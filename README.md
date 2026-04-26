# Pharmacy Inquiry (Flutter + Flask)

AI-driven chatbot app for **antibiotic inquiry + prescription safety**.

## MediTech Background Design

This project uses a medical capsule-inspired animated background across app screens:
- Glass capsule style
- Dynamic splash and droplets
- Subtle pathogen motif and energy pulse effect
- Medical blue palette application in the global theme

## Run backend (Flask)

```powershell
cd backend
python -m pip install -r requirements.txt
python app.py
```

Backend runs on `http://localhost:5000`.

### Interaction analytics API

- `POST /api/interactions`
- `GET /api/interactions?sessionId=<id>`
- `GET /api/interactions`
- `GET /api/interactions/export`
- `GET /api/docs`

## Run app (Flutter)

```powershell
flutter pub get
flutter run
```

### Windows note (important)

If you see “**Building with plugins requires symlink support**”, enable **Developer Mode** in Windows:

```powershell
start ms-settings:developers
```

Then retry `flutter pub get`.

## API base URL

In `lib/config.dart`:
- Android emulator uses `http://10.0.2.2:5000`
- Desktop/Web uses `http://localhost:5000`

