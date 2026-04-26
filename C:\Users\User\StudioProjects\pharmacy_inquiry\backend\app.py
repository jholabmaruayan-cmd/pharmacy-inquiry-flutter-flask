from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from antibiotic_catalog import (
    find_antibiotic,
    find_curated_general_faq,
    find_curated_medicine_info,
    find_curated_medicine_tips,
    search_antibiotics,
)
from chat_engine import (
    MedicineInfo,
    UserProfile,
    casual_greeting_reply,
    default_memory_state,
    generate_connected_response,
    out_of_scope_reply,
)
from db import connect, fetch_all, fetch_one, init_db
from safety import DOCTOR_DISCLAIMER, allergy_conflicts, normalize_text
from seed import ensure_seeded


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_int(value: object, *, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def clamp_float(value: object, *, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def make_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.config["JWT_SECRET"] = os.environ.get("JWT_SECRET", "dev-change-me")
    app.config["JWT_ISSUER"] = "pharmacy_inquiry_api"
    app.config["JWT_EXP_MINUTES"] = int(os.environ.get("JWT_EXP_MINUTES", "240"))

    init_db()
    ensure_seeded()

    def issue_token(user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iss": app.config["JWT_ISSUER"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=app.config["JWT_EXP_MINUTES"])).timestamp()),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")

    def require_auth() -> str:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise PermissionError("Missing bearer token")
        token = auth.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(
                token,
                app.config["JWT_SECRET"],
                algorithms=["HS256"],
                issuer=app.config["JWT_ISSUER"],
                options={"require": ["sub", "exp", "iat", "iss"]},
            )
        except Exception as e:  # noqa: BLE001
            raise PermissionError("Invalid token") from e
        return str(payload["sub"])

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/antibiotics")
    def antibiotics_search():
        query = (request.args.get("q") or "").strip()
        rows = search_antibiotics(query)
        return jsonify(
            {
                "items": [r.to_dict() for r in rows],
                "count": len(rows),
                "disclaimer": DOCTOR_DISCLAIMER,
            }
        )

    @app.get("/antibiotics/<name>")
    def antibiotic_detail(name: str):
        row = find_antibiotic(name)
        if row is None:
            return jsonify({"error": "Antibiotic not found"}), 404
        return jsonify(
            {
                "item": row.to_dict(),
                "summary": row.to_medicine_description(),
                "disclaimer": DOCTOR_DISCLAIMER,
            }
        )

    @app.post("/register")
    def register():
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        age = data.get("age")
        gender = (data.get("gender") or "").strip()
        contact = (data.get("contact") or "").strip()
        allergies = (data.get("allergies") or "").strip()
        illness = (data.get("illness") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = (data.get("password") or "").strip()

        if not (name and gender and contact and email and password):
            return jsonify({"error": "Missing required fields"}), 400
        try:
            age_int = int(age)
            if age_int <= 0 or age_int > 130:
                raise ValueError
        except Exception:  # noqa: BLE001
            return jsonify({"error": "Invalid age"}), 400

        user_id = str(uuid4())
        pw_hash = generate_password_hash(password)

        with connect() as con:
            existing = fetch_one(con, "SELECT id FROM Users WHERE email = ?", (email,))
            if existing:
                return jsonify({"error": "Email already registered"}), 409
            con.execute(
                """
                INSERT INTO Users (id, name, age, gender, contact, allergies, illness, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, age_int, gender, contact, allergies, illness, email, pw_hash, utc_now()),
            )

        return jsonify(
            {
                "user": {
                    "id": user_id,
                    "name": name,
                    "age": age_int,
                    "gender": gender,
                    "contact": contact,
                    "email": email,
                }
            }
        )

    @app.post("/login")
    def login():
        data = request.get_json(force=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = (data.get("password") or "").strip()
        if not (email and password):
            return jsonify({"error": "Missing credentials"}), 400

        with connect() as con:
            user = fetch_one(
                con,
                "SELECT id, password_hash, allergies FROM Users WHERE email = ?",
                (email,),
            )
            if not user or not check_password_hash(user["password_hash"], password):
                return jsonify({"error": "Invalid email or password"}), 401

            session_id = str(uuid4())
            con.execute(
                "INSERT INTO Sessions (id, user_id, started_at) VALUES (?, ?, ?)",
                (session_id, user["id"], utc_now()),
            )

        token = issue_token(str(user["id"]))
        return jsonify({"token": token, "session_id": session_id})

    @app.post("/logout")
    def logout():
        try:
            user_id = require_auth()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 401
        data = request.get_json(force=True) or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"ok": True})

        with connect() as con:
            con.execute(
                "UPDATE Sessions SET ended_at = ? WHERE id = ? AND user_id = ?",
                (utc_now(), session_id, user_id),
            )
        return jsonify({"ok": True})

    @app.get("/homepage-medicines")
    def homepage_medicines():
        try:
            user_id = require_auth()
        except PermissionError:
            user_id = ""

        allergies = ""
        if user_id:
            with connect() as con:
                row = fetch_one(con, "SELECT allergies FROM Users WHERE id = ?", (user_id,))
                allergies = (row["allergies"] if row else "") or ""

        limit = int(request.args.get("limit", 8))
        offset = int(request.args.get("offset", 0))
        limit = max(5, min(10, limit))
        offset = max(0, offset)

        with connect() as con:
            meds = fetch_all(
                con,
                """
                SELECT name, class, common_use, warning, allergy_tags
                FROM Medicines
                ORDER BY name ASC
                """,
                (),
            )

        user_a = normalize_text(allergies)
        filtered = []
        for m in meds:
            tags = {t.strip() for t in (m["allergy_tags"] or "").split(",") if t.strip()}
            if allergy_conflicts(user_a, tags):
                continue
            filtered.append(
                {
                    "name": m["name"],
                    "class": m["class"],
                    "common_use": m["common_use"],
                    "warning": m["warning"],
                }
            )

        # rotation via offset pagination
        if not filtered:
            page = []
        else:
            start = offset % len(filtered)
            page = (filtered[start:] + filtered[:start])[:limit]

        return jsonify(
            {
                "items": page,
                "disclaimer": f"For educational purposes only. {DOCTOR_DISCLAIMER}",
            }
        )

    @app.post("/chat")
    def chat():
        try:
            user_id = require_auth()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 401

        data = request.get_json(force=True) or {}
        message = (data.get("input") or "").strip()
        session_id = (data.get("session_id") or "").strip()
        if not message:
            return jsonify({"error": "Missing input"}), 400
        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        with connect() as con:
            user = fetch_one(
                con,
                "SELECT allergies, illness, age, gender FROM Users WHERE id = ?",
                (user_id,),
            )
            allergies = (user["allergies"] if user else "") or ""
            illness = (user["illness"] if user else "") or ""
            age = int(user["age"]) if user and user["age"] is not None else None
            gender = (user["gender"] if user else "") or None

            recent = fetch_all(
                con,
                """
                SELECT message, response
                FROM ChatLogs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,),
            )
            meds = fetch_all(
                con,
                """
                SELECT name, class, common_use, warning, allergy_tags
                FROM Medicines
                ORDER BY name ASC
                """,
                (),
            )
            memory_row = fetch_one(
                con,
                """
                SELECT memory_json
                FROM ConversationMemory
                WHERE session_id = ? AND user_id = ?
                LIMIT 1
                """,
                (session_id, user_id),
            )
        history = "\n".join([f"U: {r['message']}\nA: {r['response']}" for r in recent[::-1]])
        if memory_row and memory_row["memory_json"]:
            try:
                memory_state = json.loads(memory_row["memory_json"])
            except json.JSONDecodeError:
                memory_state = default_memory_state()
        else:
            memory_state = default_memory_state()

        profile = UserProfile(allergies=allergies, illness=illness, age=age, gender=gender)
        med_infos = [
            MedicineInfo(
                name=m["name"],
                klass=m["class"],
                common_use=m["common_use"],
                warning=m["warning"],
                allergy_tags={t.strip() for t in (m["allergy_tags"] or "").split(",") if t.strip()},
            )
            for m in meds
        ]
        greeting_reply = casual_greeting_reply(message)
        if greeting_reply is not None:
            response_text = greeting_reply
        else:
            curated_faq_reply = find_curated_general_faq(message)
            if curated_faq_reply is not None:
                response_text = curated_faq_reply
            else:
                curated_tips_hit = find_curated_medicine_tips(message)
                if curated_tips_hit is not None:
                    med_name, med_tips = curated_tips_hit
                    response_text = "\n".join(
                        [
                            f"Medicine: {med_name}",
                            "",
                            "Tips for taking this medicine:",
                            med_tips,
                        ]
                    )
                else:
                    curated_hit = find_curated_medicine_info(message)
                    if curated_hit is not None:
                        med_name, med_info = curated_hit
                        response_text = "\n".join(
                            [
                                f"Medicine: {med_name}",
                                "",
                                med_info,
                            ]
                        )
                    else:
                        catalog_hit = find_antibiotic(message)
                        if catalog_hit is not None:
                            response_text = catalog_hit.to_medicine_description()
                        else:
                            scope_reply = out_of_scope_reply(message, med_infos)
                            if scope_reply is not None:
                                response_text = scope_reply
                            else:
                                response_text, memory_state = generate_connected_response(
                                    message,
                                    profile=profile,
                                    history=history,
                                    medicines=med_infos,
                                    memory=memory_state,
                                )

        with connect() as con:
            con.execute(
                """
                INSERT INTO ChatLogs (id, user_id, session_id, message, response, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), user_id, session_id, message, response_text, utc_now()),
            )
            con.execute(
                """
                INSERT INTO ConversationMemory (session_id, user_id, memory_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    memory_json = excluded.memory_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, user_id, json.dumps(memory_state, separators=(",", ":")), utc_now()),
            )

        return jsonify({"response": response_text})

    @app.get("/history")
    def history_endpoint():
        try:
            user_id = require_auth()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 401

        with connect() as con:
            rows = fetch_all(
                con,
                """
                SELECT id, session_id, message, response, created_at
                FROM ChatLogs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,),
            )

        return jsonify(
            {
                "items": [
                    {
                        "id": r["id"],
                        "session_id": r["session_id"],
                        "message": r["message"],
                        "response": r["response"],
                        "timestamp": r["created_at"],
                    }
                    for r in rows
                ]
            }
        )

    @app.post("/history/delete")
    def delete_history_endpoint():
        try:
            user_id = require_auth()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 401

        data = request.get_json(force=True) or {}
        delete_all = bool(data.get("all"))
        ids_raw = data.get("ids") or []
        ids = [str(v).strip() for v in ids_raw if str(v).strip()]

        with connect() as con:
            if delete_all:
                result = con.execute("DELETE FROM ChatLogs WHERE user_id = ?", (user_id,))
                return jsonify({"deleted": int(result.rowcount or 0), "all": True})

            if not ids:
                return jsonify({"error": "Missing ids or all=true"}), 400

            placeholders = ",".join(["?"] * len(ids))
            params = [user_id, *ids]
            result = con.execute(
                f"DELETE FROM ChatLogs WHERE user_id = ? AND id IN ({placeholders})",
                params,
            )
            return jsonify({"deleted": int(result.rowcount or 0), "all": False})

    @app.post("/api/interactions")
    def create_interaction():
        data = request.get_json(force=True) or {}
        action = (data.get("action") or "capsule_interaction").strip() or "capsule_interaction"
        raw_timestamp = data.get("timestamp")
        session_id = (data.get("sessionId") or "").strip()
        payload = data.get("data") or {}

        if not session_id:
            return jsonify({"error": "Missing sessionId"}), 400

        interaction_type = (payload.get("interactionType") or "click").strip().lower() or "click"
        energy_level = clamp_int(payload.get("energyLevel"), minimum=0, maximum=100, default=50)
        coordinates = payload.get("coordinates") or {}
        coord_x = coordinates.get("x")
        coord_y = coordinates.get("y")
        x = clamp_float(coord_x, minimum=-100000.0, maximum=100000.0, default=0.0)
        y = clamp_float(coord_y, minimum=-100000.0, maximum=100000.0, default=0.0)

        capsule_state = payload.get("capsuleState") or {}
        animation_phase = (
            (capsule_state.get("animationPhase") or "idle").strip().lower() or "idle"
        )
        splash_intensity = clamp_float(
            capsule_state.get("splashIntensity"), minimum=0.0, maximum=1.0, default=0.0
        )
        virus_destruction_progress = clamp_float(
            capsule_state.get("virusDestructionProgress"), minimum=0.0, maximum=1.0, default=0.0
        )
        glass_reflection_angle = clamp_float(
            capsule_state.get("glassReflectionAngle"), minimum=0.0, maximum=360.0, default=0.0
        )

        timestamp_ms = clamp_int(
            raw_timestamp,
            minimum=946684800000,
            maximum=4102444800000,
            default=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        event_id = str(uuid4())
        with connect() as con:
            session = fetch_one(con, "SELECT id, started_at FROM Sessions WHERE id = ?", (session_id,))
            if not session:
                return jsonify({"error": "Unknown sessionId"}), 404
            con.execute(
                """
                INSERT INTO InteractionEvents (
                    id, session_id, action, timestamp_ms, interaction_type,
                    energy_level, x, y, animation_phase, splash_intensity,
                    virus_destruction_progress, glass_reflection_angle, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    action,
                    timestamp_ms,
                    interaction_type,
                    energy_level,
                    x,
                    y,
                    animation_phase,
                    splash_intensity,
                    virus_destruction_progress,
                    glass_reflection_angle,
                    json.dumps(payload, separators=(",", ":")),
                    utc_now(),
                ),
            )
            totals = fetch_one(
                con,
                "SELECT COUNT(*) AS c FROM InteractionEvents WHERE session_id = ?",
                (session_id,),
            )
            counts = fetch_all(
                con,
                """
                SELECT action, COUNT(*) AS c
                FROM InteractionEvents
                WHERE session_id = ?
                GROUP BY action
                """,
                (session_id,),
            )
            last_event = fetch_one(
                con,
                """
                SELECT timestamp_ms
                FROM InteractionEvents
                WHERE session_id = ?
                ORDER BY timestamp_ms DESC
                LIMIT 1
                """,
                (session_id,),
            )

        action_counts = {str(row["action"]): int(row["c"]) for row in counts}
        return jsonify(
            {
                "success": True,
                "sessionId": session_id,
                "totalInteractions": int(totals["c"] if totals else 0),
                "sessionStats": {
                    "sessionStart": session["started_at"] if session else utc_now(),
                    "lastInteraction": int(last_event["timestamp_ms"] if last_event else timestamp_ms),
                    "actionCounts": action_counts,
                },
            }
        )

    @app.get("/api/interactions")
    def get_interactions():
        session_id = (request.args.get("sessionId") or "").strip()
        with connect() as con:
            if session_id:
                session = fetch_one(con, "SELECT id, started_at FROM Sessions WHERE id = ?", (session_id,))
                if not session:
                    return jsonify({"error": "Unknown sessionId"}), 404
                rows = fetch_all(
                    con,
                    """
                    SELECT id, session_id, action, timestamp_ms, interaction_type, energy_level, x, y,
                           animation_phase, splash_intensity, virus_destruction_progress, glass_reflection_angle
                    FROM InteractionEvents
                    WHERE session_id = ?
                    ORDER BY timestamp_ms ASC
                    """,
                    (session_id,),
                )
                counts = fetch_all(
                    con,
                    """
                    SELECT action, COUNT(*) AS c
                    FROM InteractionEvents
                    WHERE session_id = ?
                    GROUP BY action
                    """,
                    (session_id,),
                )
                stats = {
                    "sessionStart": session["started_at"],
                    "totalInteractions": len(rows),
                    "actionCounts": {str(row["action"]): int(row["c"]) for row in counts},
                }
                return jsonify(
                    {
                        "sessionId": session_id,
                        "interactions": [
                            {
                                "interactionId": row["id"],
                                "sessionId": row["session_id"],
                                "timestamp": int(row["timestamp_ms"]),
                                "action": row["action"],
                                "interactionType": row["interaction_type"],
                                "coordinates": {"x": row["x"], "y": row["y"]},
                                "capsuleState": {
                                    "energyLevel": row["energy_level"],
                                    "animationPhase": row["animation_phase"],
                                    "splashIntensity": row["splash_intensity"],
                                    "virusDestructionProgress": row["virus_destruction_progress"],
                                    "glassReflectionAngle": row["glass_reflection_angle"],
                                },
                            }
                            for row in rows
                        ],
                        "stats": stats,
                    }
                )

            total_sessions = fetch_one(
                con,
                "SELECT COUNT(*) AS c FROM Sessions",
                (),
            )
            total_interactions = fetch_one(
                con,
                "SELECT COUNT(*) AS c FROM InteractionEvents",
                (),
            )
            top_actions = fetch_all(
                con,
                """
                SELECT action, COUNT(*) AS c
                FROM InteractionEvents
                GROUP BY action
                ORDER BY c DESC
                LIMIT 20
                """,
                (),
            )

        return jsonify(
            {
                "totalSessions": int(total_sessions["c"] if total_sessions else 0),
                "totalInteractions": int(total_interactions["c"] if total_interactions else 0),
                "sessionStats": {
                    "topActions": {str(row["action"]): int(row["c"]) for row in top_actions},
                },
            }
        )

    @app.get("/api/interactions/export")
    def export_interactions():
        with connect() as con:
            rows = fetch_all(
                con,
                """
                SELECT id, session_id, action, timestamp_ms, interaction_type, energy_level, x, y,
                       animation_phase, splash_intensity, virus_destruction_progress, glass_reflection_angle
                FROM InteractionEvents
                ORDER BY timestamp_ms ASC
                """,
                (),
            )
        return jsonify(
            {
                "count": len(rows),
                "items": [
                    {
                        "interactionId": row["id"],
                        "sessionId": row["session_id"],
                        "timestamp": int(row["timestamp_ms"]),
                        "action": row["action"],
                        "interactionType": row["interaction_type"],
                        "coordinates": {"x": row["x"], "y": row["y"]},
                        "capsuleState": {
                            "energyLevel": row["energy_level"],
                            "animationPhase": row["animation_phase"],
                            "splashIntensity": row["splash_intensity"],
                            "virusDestructionProgress": row["virus_destruction_progress"],
                            "glassReflectionAngle": row["glass_reflection_angle"],
                        },
                    }
                    for row in rows
                ],
            }
        )

    @app.get("/api/docs")
    def api_docs():
        return jsonify(
            {
                "name": "MediTech Pharmaceutical Capsule System API",
                "version": "1.0.0",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/interactions",
                        "description": "Store capsule interaction telemetry",
                    },
                    {
                        "method": "GET",
                        "path": "/api/interactions?sessionId={sessionId}",
                        "description": "Retrieve interactions for one session",
                    },
                    {
                        "method": "GET",
                        "path": "/api/interactions",
                        "description": "Get global interaction statistics",
                    },
                    {
                        "method": "GET",
                        "path": "/api/interactions/export",
                        "description": "Export complete interaction history in JSON",
                    },
                ],
            }
        )

    return app


if __name__ == "__main__":
    app = make_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)

