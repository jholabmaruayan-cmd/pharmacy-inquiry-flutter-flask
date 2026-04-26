from __future__ import annotations

from dataclasses import dataclass

from db import connect, fetch_all, fetch_one
from safety import normalize_text

CURATED_MEDICINE_INFO: dict[str, str] = {
    "amoxicillin": "Amoxicillin is a broad-spectrum penicillin antibiotic used for many common bacterial infections. It works by inhibiting bacterial cell wall synthesis, causing bacteria to rupture and die. It is commonly used for respiratory infections, ear infections, and urinary tract infections. It is well absorbed orally, making it convenient for outpatient treatment. It is often combined with clavulanate to overcome resistant bacteria.",
    "ampicillin": "Ampicillin is a penicillin antibiotic with a broader spectrum than early penicillins. It works by blocking bacterial cell wall formation. It is used for respiratory, gastrointestinal, urinary tract, and some meningitis infections. It can be given orally or by injection depending on severity. Resistance is common in bacteria producing beta-lactamase enzymes.",
    "dicloxacillin": "Dicloxacillin is a penicillinase-resistant penicillin used for staphylococcal infections. It works by preventing bacterial cell wall synthesis. It is mainly used for skin and soft tissue infections. It is effective against methicillin-sensitive Staphylococcus aureus (MSSA). It is not effective against MRSA strains.",
    "flucloxacillin": "Flucloxacillin is an antibiotic used primarily for staphylococcal infections. It works by inhibiting bacterial cell wall formation. It is commonly used for skin, bone, and soft tissue infections. It is resistant to beta-lactamase enzymes produced by some bacteria. It is ineffective against MRSA.",
    "nafcillin": "Nafcillin is a penicillin antibiotic used for serious staphylococcal infections. It works by stopping bacterial cell wall synthesis. It is mainly used in hospitals for bloodstream, bone, and deep tissue infections. It is effective against MSSA but not MRSA. It is usually given intravenously.",
    "oxacillin": "Oxacillin is a penicillinase-resistant antibiotic used for staphylococcal infections. It works by preventing bacteria from forming proper cell walls. It is used for skin, lung, and bone infections caused by MSSA. It is commonly administered in hospital settings. It does not work against MRSA.",
    "penicillin g": "Penicillin G is an injectable antibiotic used for severe bacterial infections. It works by inhibiting bacterial cell wall synthesis. It is commonly used for syphilis, meningitis, and streptococcal infections. It is not stable in stomach acid, so it is given by injection. It remains highly effective against many Gram-positive bacteria.",
    "penicillin v": "Penicillin V is an oral penicillin used for mild bacterial infections. It works by stopping bacterial cell wall formation. It is commonly used for strep throat and mild respiratory infections. It is more stable in stomach acid than penicillin G. It is generally well tolerated and widely used.",
    "piperacillin": "Piperacillin is a broad-spectrum penicillin used for severe hospital infections. It works by inhibiting bacterial cell wall synthesis. It is effective against many Gram-negative bacteria including Pseudomonas aeruginosa. It is usually given intravenously in serious cases. It is often combined with tazobactam for better effectiveness.",
    "ticarcillin": "Ticarcillin is a broad-spectrum penicillin used for serious infections. It works by disrupting bacterial cell wall formation. It is effective against several Gram-negative organisms. It is mainly used in hospital settings for severe infections. It is often combined with clavulanic acid to overcome resistance.",
    "cefaclor": "Cefaclor is a second-generation cephalosporin antibiotic. It works by inhibiting bacterial cell wall synthesis. It is commonly used for respiratory tract infections, ear infections, and skin infections. It has better Gram-negative coverage than first-generation cephalosporins. Side effects may include rash, diarrhea, and allergic reactions.",
    "cefuroxime": "Cefuroxime is a second-generation cephalosporin used for a wide range of infections. It works by blocking bacterial cell wall formation. It is commonly used for sinusitis, pneumonia, urinary tract infections, and skin infections. It has good activity against both Gram-positive and Gram-negative bacteria. It can be given orally or by injection depending on severity.",
    "cefoxitin": "Cefoxitin is a second-generation cephalosporin with strong anaerobic coverage. It works by inhibiting bacterial cell wall synthesis. It is commonly used for abdominal, pelvic, and surgical infections. It is effective against some Gram-negative bacteria and anaerobes. It is usually administered by injection in hospital settings.",
    "cefotetan": "Cefotetan is a second-generation cephalosporin antibiotic used for serious infections. It works by stopping bacterial cell wall formation. It is commonly used for abdominal and gynecological infections. It has good anaerobic and Gram-negative coverage. It is given intravenously or intramuscularly in clinical settings.",
    "cefixime": "Cefixime is an oral third-generation cephalosporin antibiotic. It works by inhibiting bacterial cell wall synthesis. It is commonly used for respiratory, urinary tract, and ear infections. It has strong Gram-negative coverage. It is often used for outpatient treatment of mild to moderate infections.",
    "ceftriaxone": "Ceftriaxone is a powerful injectable third-generation cephalosporin. It works by blocking bacterial cell wall formation. It is used for serious infections such as meningitis, sepsis, and gonorrhea. It has long duration of action allowing once-daily dosing. It is widely used in hospitals for severe infections.",
    "ceftazidime": "Ceftazidime is a third-generation cephalosporin with strong anti-Pseudomonas activity. It works by inhibiting bacterial cell wall synthesis. It is commonly used for hospital-acquired infections and severe Gram-negative infections. It has weaker Gram-positive coverage compared to earlier generations. It is administered intravenously or intramuscularly.",
    "cefotaxime": "Cefotaxime is a third-generation cephalosporin used for serious systemic infections. It works by disrupting bacterial cell wall formation. It is commonly used for meningitis, respiratory infections, and sepsis. It has broad Gram-negative and moderate Gram-positive coverage. It is usually given by injection.",
    "cefpodoxime": "Cefpodoxime is an oral third-generation cephalosporin antibiotic. It works by inhibiting bacterial cell wall synthesis. It is used for respiratory tract, urinary tract, and skin infections. It has improved Gram-negative coverage compared to earlier generations. It is commonly used in outpatient therapy.",
    "cefepime": "Cefepime is a fourth-generation cephalosporin antibiotic used for serious hospital infections. It works by inhibiting bacterial cell wall synthesis. It has broad-spectrum activity against both Gram-positive and Gram-negative bacteria. It is commonly used for pneumonia, sepsis, and complicated urinary tract infections. It is administered intravenously and is effective against resistant organisms like Pseudomonas.",
    "ceftaroline": "Ceftaroline is a fifth-generation cephalosporin antibiotic with strong activity against MRSA. It works by binding to bacterial penicillin-binding proteins and inhibiting cell wall formation. It is used for skin infections and community-acquired pneumonia. It has good Gram-positive coverage and moderate Gram-negative coverage. It is administered intravenously in clinical settings.",
    "ceftobiprole": "Ceftobiprole is a fifth-generation cephalosporin antibiotic used for resistant bacterial infections. It works by inhibiting bacterial cell wall synthesis. It is effective against MRSA and some Gram-negative bacteria. It is mainly used for hospital-acquired pneumonia and complicated skin infections. It is administered intravenously and is reserved for serious cases.",
    "ertapenem": "Ertapenem is a carbapenem antibiotic used for moderate to severe infections. It works by inhibiting bacterial cell wall synthesis. It has broad activity against Gram-positive and Gram-negative bacteria but not strong against Pseudomonas. It is commonly used for abdominal, urinary, and skin infections. It is given by injection in hospital or outpatient settings.",
    "imipenem": "Imipenem is a powerful carbapenem antibiotic used for life-threatening infections. It works by blocking bacterial cell wall formation. It has very broad-spectrum activity against many resistant bacteria. It is usually combined with cilastatin to prevent kidney breakdown. It is administered intravenously in hospital settings.",
    "meropenem": "Meropenem is a broad-spectrum carbapenem antibiotic. It works by inhibiting bacterial cell wall synthesis. It is used for severe infections such as meningitis, sepsis, and hospital-acquired infections. It is effective against many resistant Gram-negative bacteria. It is given intravenously and is widely used in intensive care units.",
    "doripenem": "Doripenem is a carbapenem antibiotic used for severe resistant infections. It works by blocking bacterial cell wall formation. It has strong activity against Gram-negative bacteria including Pseudomonas. It is used mainly in complicated abdominal and urinary infections. It is administered intravenously in hospitals.",
}

CURATED_MEDICINE_TIPS: dict[str, str] = {
    "amoxicillin": "Take exactly as prescribed and finish the full course even if symptoms improve. You can take it with or without food, but food may reduce stomach upset. Do not skip doses to avoid antibiotic resistance. Avoid using it for viral infections like colds or flu. Drink plenty of water while taking it.",
    "ampicillin": "Take on an empty stomach for better absorption unless your doctor says otherwise. Follow the dosing schedule strictly and do not miss doses. Complete the full course even if you feel better early. Watch for allergic reactions like rash or itching. Avoid self-medication.",
    "dicloxacillin": "Take on an empty stomach for best results. Do not take with food because it reduces absorption. Finish the full prescribed course. Take doses evenly spaced throughout the day. Report any allergic reaction immediately.",
    "flucloxacillin": "Take on an empty stomach for maximum effectiveness. Do not skip or double doses. Complete the full treatment course. Avoid alcohol if it causes stomach discomfort. Seek medical help if yellowing of skin occurs.",
    "nafcillin": "Use only under hospital supervision. Do not self-administer. Follow IV schedule strictly. Report any vein pain or irritation. Complete full treatment as directed by healthcare staff.",
    "oxacillin": "Usually given in hospital settings only. Follow injection or IV schedule exactly. Do not miss doses. Watch for allergic reactions during treatment. Always complete prescribed therapy.",
    "penicillin g": "Must be given by healthcare professionals only. Do not attempt oral use. Follow injection schedule strictly. Report any severe allergic reaction immediately. Complete full treatment even if symptoms improve.",
    "penicillin v": "Take on an empty stomach for better absorption. Stick to regular dosing times. Complete the full course. Do not stop early even if you feel better. Avoid sharing medication with others.",
    "piperacillin": "Use only in hospital settings under supervision. Follow IV infusion schedule strictly. Do not miss doses. Monitor for side effects during treatment. Complete full course as directed.",
    "ticarcillin": "Administer only through hospital IV. Follow dosing schedule carefully. Do not skip doses. Report side effects immediately. Use only under medical supervision.",
    "cefaclor": "Take exactly as prescribed with or without food. Complete the full course even if symptoms improve. Do not skip doses. Watch for allergic reactions like rash. Avoid unnecessary antibiotic use.",
    "cefuroxime": "Take with food if it causes stomach upset. Follow dosing schedule strictly. Do not stop early. Complete full treatment course. Avoid sharing with others.",
    "cefoxitin": "Use only in hospital settings. Follow injection schedule strictly. Do not miss doses. Report any unusual symptoms immediately. Complete full prescribed treatment.",
    "cefotetan": "Given by injection in hospital or clinic. Follow dosing exactly. Do not skip doses. Report side effects like bleeding or allergy. Complete full treatment course.",
    "cefixime": "Take exactly as prescribed, usually once or twice daily. Can be taken with or without food. Finish the full course. Do not skip doses. Avoid using for viral infections.",
    "ceftriaxone": "Given only by injection in healthcare settings. Follow dosing schedule strictly. Do not miss doses. Report any side effects immediately. Complete full treatment.",
    "ceftazidime": "Use only under hospital supervision. Follow IV/IM schedule exactly. Do not skip doses. Report allergic reactions. Complete full therapy.",
    "cefotaxime": "Given by injection in hospital settings. Follow dosing instructions carefully. Do not miss doses. Report side effects promptly. Complete full course.",
    "cefpodoxime": "Take with food for better absorption. Follow dosing schedule strictly. Do not skip doses. Complete full treatment course. Avoid unnecessary use. Take at evenly spaced times.",
    "cefepime": "Use only in hospital under supervision. Follow IV dosing strictly. Do not miss scheduled doses. Monitor for side effects. Complete full treatment course.",
    "ceftaroline": "Given only by IV in clinical settings. Follow doctor instructions carefully. Do not skip doses. Report allergic reactions immediately. Complete full therapy.",
    "ceftobiprole": "Administered only in hospitals. Follow IV schedule strictly. Do not miss doses. Monitor for side effects. Complete full treatment.",
    "ertapenem": "Given by injection in hospital or clinic. Follow dosing schedule strictly. Do not miss doses. Report side effects immediately. Complete full treatment.",
    "imipenem": "Administered only under hospital supervision. Follow IV schedule carefully. Do not skip doses. Report seizures or severe reactions. Complete full course.",
    "meropenem": "Given by IV in hospital settings. Follow dosing schedule strictly. Do not miss doses. Monitor for side effects. Complete full therapy.",
    "doripenem": "Use only in hospitals under supervision. Follow IV dosing schedule. Do not skip doses. Report side effects immediately. Complete full treatment.",
    "azithromycin": "Take exactly as prescribed and finish the full course even if you feel better. It can be taken with or without food. Do not skip doses or double up if you miss one. Avoid antacids close to dosing time unless advised. Do not use for viral infections.",
    "clarithromycin": "Take with or without food but food may reduce stomach upset. Follow dosing schedule strictly. Complete the full course. Do not skip doses to avoid resistance. Avoid combining with certain medications unless prescribed.",
    "erythromycin": "Take on an empty stomach for better absorption. Avoid taking with food unless it causes stomach upset. Follow dosing schedule carefully. Complete the full treatment course. Avoid grapefruit juice.",
    "roxithromycin": "Take as prescribed, usually before meals. Do not skip doses. Complete the full course even if symptoms improve. Follow timing strictly for best effect. Avoid self-medication.",
    "ciprofloxacin": "Take with plenty of water to avoid kidney irritation. Avoid dairy products close to dosing time. Do not skip doses or stop early. Avoid heavy exercise due to tendon risk. Complete full course.",
    "levofloxacin": "Take once daily at the same time each day. Drink plenty of water. Avoid sun exposure or use sunscreen. Do not stop early even if you feel better. Follow full prescribed duration.",
    "moxifloxacin": "Take at the same time daily. Do not take with dairy or antacids. Avoid skipping doses. Avoid strenuous physical activity. Complete full treatment.",
    "norfloxacin": "Take on an empty stomach for better absorption. Drink plenty of fluids. Do not miss doses. Complete the full course. Avoid antacids close to dosing time.",
    "ofloxacin": "Take exactly as prescribed. Avoid sun exposure or use protection. Do not skip doses. Drink plenty of water. Complete full treatment course.",
    "doxycycline": "Take with a full glass of water while sitting upright. Avoid lying down immediately after taking it. Do not take with dairy or antacids. Avoid sun exposure. Complete full course.",
    "tetracycline": "Take on an empty stomach for best absorption. Avoid dairy products. Drink plenty of water. Do not lie down immediately after taking. Complete full treatment.",
    "minocycline": "Take with or without food but avoid dairy. Do not skip doses. Stay upright after taking. Avoid sun exposure. Complete full course.",
    "oxytetracycline": "Take on an empty stomach. Avoid dairy and antacids. Drink plenty of water. Do not skip doses. Finish full course.",
    "gentamicin": "Used only under hospital supervision. Follow injection schedule strictly. Do not self-administer. Report hearing or kidney issues immediately. Complete full treatment.",
    "amikacin": "Given in hospital settings only. Follow dosing strictly. Do not miss doses. Monitor kidney and hearing function. Complete full course.",
    "tobramycin": "Use only under medical supervision. Follow IV or inhalation schedule. Do not skip doses. Report side effects immediately. Complete full therapy.",
    "streptomycin": "Administered by healthcare professionals only. Follow injection schedule. Do not miss doses. Monitor hearing carefully. Complete full course.",
    "neomycin": "Use only as prescribed (often topical or oral bowel use). Do not overuse. Follow exact instructions. Avoid prolonged use. Report side effects.",
    "vancomycin": "Given only by IV or monitored oral use. Follow dosing schedule strictly. Do not skip doses. Monitor kidney function. Complete full treatment.",
    "teicoplanin": "Administered in hospital settings. Follow dosing schedule carefully. Do not miss doses. Report side effects. Complete full course.",
    "telavancin": "Use only under medical supervision. Follow IV dosing strictly. Do not skip doses. Monitor kidney and pregnancy risks. Complete full treatment.",
    "dalbavancin": "Given as long-acting IV injection. Follow hospital instructions. Do not miss scheduled dose. Report side effects. Complete full therapy.",
    "oritavancin": "Administered as single-dose IV therapy. Follow hospital guidance. Do not self-medicate. Monitor for reactions. Follow-up as advised.",
}

CURATED_GENERAL_FAQ: list[tuple[tuple[str, ...], str]] = [
    (
        ("what is an antibiotic", "ano ang antibiotic", "define antibiotic"),
        "Antibiotics are medicines used to treat infections caused by bacteria. They do not work against viruses like colds or flu.",
    ),
    (
        (
            "do i need antibiotics",
            "kailangan ko ba ng antibiotic",
            "need antibiotic for my illness",
        ),
        "It depends on your condition. Antibiotics are only effective for bacterial infections. For viral infections, rest and supportive care are usually recommended. Please consult a healthcare professional for proper diagnosis.",
    ),
    (
        (
            "sore throat and fever",
            "masakit lalamunan at lagnat",
            "should i take antibiotics for sore throat",
        ),
        "Not all sore throats require antibiotics. Some are caused by viruses. If symptoms are severe or last more than a few days, consult a doctor for proper testing.",
    ),
    (
        (
            "how often should i take my antibiotic",
            "gaano kadalas inumin ang antibiotic",
            "antibiotic dosage",
        ),
        "Follow the exact dosage prescribed by your doctor or indicated on the label. Do not skip doses or stop early, even if you feel better.",
    ),
    (
        ("miss a dose", "nakalimutan ko dose", "missed antibiotic dose"),
        "Take the missed dose as soon as you remember. If it is almost time for your next dose, skip the missed one. Do not double the dose.",
    ),
    (
        (
            "side effects of antibiotics",
            "antibiotic side effect",
            "effects of antibiotic",
        ),
        "Common side effects include nausea, diarrhea, and stomach upset. Some people may experience allergic reactions. Seek medical help if symptoms are severe.",
    ),
    (
        ("can i take antibiotics if i have allergies", "antibiotic allergy"),
        "You should inform your doctor about any allergies before taking antibiotics. Some antibiotics can cause allergic reactions in sensitive individuals.",
    ),
    (
        ("what is antibiotic resistance", "antibiotic resistance"),
        "Antibiotic resistance happens when bacteria adapt and become harder to treat with medicines. Misuse and overuse of antibiotics can cause this problem.",
    ),
    (
        (
            "stop taking antibiotics when i feel better",
            "pwede itigil antibiotic pag okay na",
            "can i stop antibiotics early",
        ),
        "No. You should complete the full course as prescribed to ensure all bacteria are eliminated and to prevent resistance.",
    ),
    (
        ("share my antibiotics", "can i share antibiotics"),
        "No. Antibiotics are prescribed specifically for your condition. Sharing them can be unsafe and ineffective.",
    ),
    (
        ("take antibiotics with food", "antibiotic with food"),
        "Some antibiotics can be taken with food, while others should be taken on an empty stomach. Follow the instructions provided with your medication.",
    ),
    (
        ("drink alcohol while taking antibiotics", "antibiotic and alcohol"),
        "It is generally best to avoid alcohol while taking antibiotics, as it may reduce effectiveness or increase side effects.",
    ),
    (
        ("antibiotics safe during pregnancy", "pregnant and antibiotics"),
        "Some antibiotics are safe, while others are not. Always consult your doctor before taking any medication during pregnancy.",
    ),
    (
        ("can children take antibiotics", "antibiotic for child", "antibiotic for kids"),
        "Yes, but only under medical supervision. Dosage and type depend on the child’s age and weight.",
    ),
    (
        (
            "check symptoms",
            "symptom checker",
            "check my symptoms",
            "symptoms checker",
        ),
        "Please select your symptoms:\n- Fever\n- Sore Throat\n- Cough\n- Wound Infection\n- Urinary Pain\n\nYou can type one or more symptoms, and I will guide you.",
    ),
    (
        (
            "fever and sore throat",
            "i have fever and sore throat",
            "lagnat at sore throat",
        ),
        "You selected: Fever and Sore Throat.\n\nThese symptoms may be caused by a viral or bacterial infection.\n\nDo you have any of the following?\n- Difficulty swallowing\n- Swollen lymph nodes\n- Symptoms lasting more than 3 days",
    ),
    (
        (
            "difficulty swallowing",
            "swollen lymph nodes",
            "symptoms lasting more than 3 days",
            "yes i have those symptoms",
        ),
        "You may need medical evaluation. Antibiotics might be required if it is a bacterial infection.\n\nPlease consult a doctor for proper diagnosis.",
    ),
    (
        (
            "learn about antibiotics",
            "about antibiotics",
            "teach me about antibiotics",
        ),
        "Antibiotics are medicines used to treat bacterial infections.\nThey do NOT work against viruses like colds or flu.\n\nYou can ask:\n- Types of Antibiotics\n- When to Use\n- Examples",
    ),
    (
        ("types of antibiotics", "antibiotic types", "classes of antibiotics"),
        "Common antibiotic classes include:\n- Penicillins\n- Cephalosporins\n- Macrolides\n- Fluoroquinolones\n- Tetracyclines\n\nEach class is used based on the infection type and patient safety profile.",
    ),
    (
        ("when to use antibiotics", "when to use", "when should i use antibiotics"),
        "Use antibiotics only when a bacterial infection is suspected or confirmed by a licensed clinician.\n\nAntibiotics should not be used for viral illnesses such as common cold or flu.",
    ),
    (
        ("examples of antibiotics", "antibiotic examples", "examples"),
        "Here are common antibiotics:\n- Amoxicillin: for respiratory and ear infections\n- Azithromycin: for throat and lung infections\n- Ciprofloxacin: for urinary infections",
    ),
    (
        (
            "dosage and safety",
            "dosage safety",
            "safety of antibiotics",
            "how to take safely",
        ),
        "What would you like to know?\n- Missed Dose\n- How to Take Antibiotics\n- Can I Stop Early?",
    ),
    (
        ("how to take antibiotics", "how to take", "take antibiotics safely"),
        "Follow the exact dosage prescribed by your doctor or the medication label.\nTake doses on schedule and complete the full course.\nDo not skip doses and do not self-adjust treatment.",
    ),
    (
        ("can i stop early", "stop early", "stop antibiotics early"),
        "No. You must complete the full course to fully eliminate bacteria and help prevent antibiotic resistance.",
    ),
    (
        (
            "side effects",
            "antibiotic side effects",
            "what side effects",
        ),
        "Common side effects include:\n- Nausea\n- Diarrhea\n- Stomach pain\n\nSeek medical help immediately if you experience:\n- Severe allergic reaction\n- Difficulty breathing\n- Swelling",
    ),
    (
        (
            "talk to expert",
            "expert",
            "doctor consultation",
            "consult expert",
        ),
        "I can provide educational information, but diagnosis and treatment decisions must come from a licensed healthcare professional.",
    ),
    (
        (
            "welcome",
            "start",
            "hello antibiotic assistant",
        ),
        "Hello! I’m your Antibiotic Assistant.\nI can help you understand antibiotics, their uses, and safety.\n\nYou can choose:\n- Check Symptoms\n- Learn About Antibiotics\n- Dosage and Safety\n- Side Effects\n- Talk to Expert (Info Only)",
    ),
    (
        (
            "why cant antibiotics treat colds",
            "why can't antibiotics treat colds",
            "antibiotics for colds",
        ),
        "Colds are caused by viruses, and antibiotics only work against bacteria. Taking antibiotics for viral infections will not help and may increase antibiotic resistance.",
    ),
    (
        (
            "how long do antibiotics take to work",
            "how fast do antibiotics work",
            "when will antibiotics start working",
        ),
        "Most people start feeling better within 1 to 3 days. You should still complete the full course exactly as prescribed.",
    ),
    (
        (
            "what happens if antibiotics dont work",
            "what happens if antibiotics don't work",
            "antibiotic not working",
        ),
        "The infection may be resistant, or the cause may not be bacterial. A doctor may change your medicine or request additional tests.",
    ),
    (
        (
            "what is azithromycin used for",
            "azithromycin use",
            "azithromycin for what infection",
        ),
        "Azithromycin is used for bacterial infections such as some respiratory, skin, and sexually transmitted infections. It should be used only when prescribed.",
    ),
    (
        (
            "is ciprofloxacin strong",
            "ciprofloxacin strong antibiotic",
            "how strong is ciprofloxacin",
        ),
        "Ciprofloxacin is a broad-spectrum antibiotic often used for serious infections. It should only be taken with a doctor’s prescription.",
    ),
    (
        (
            "can i buy antibiotics without prescription",
            "buy antibiotics without prescription",
            "do antibiotics require prescription",
        ),
        "In many places, antibiotics require a prescription to ensure safe and proper use. Always consult a healthcare professional before taking them.",
    ),
    (
        (
            "can i take antibiotics at night",
            "take antibiotics before sleep",
            "antibiotics bedtime",
        ),
        "Yes, you can take antibiotics at night as long as you follow the prescribed schedule. Consistent timing is important for effectiveness.",
    ),
    (
        (
            "what should i avoid while taking antibiotics",
            "what to avoid with antibiotics",
            "avoid while on antibiotics",
        ),
        "Avoid skipping doses, self-medicating, and combining medicines without medical advice. Alcohol should also be avoided for certain antibiotics.",
    ),
    (
        (
            "can antibiotics treat tooth infection",
            "antibiotics for tooth infection",
            "antibiotic for dental infection",
        ),
        "Antibiotics may be used for bacterial tooth infections, but dental treatment is often also required. Please consult a dentist or doctor.",
    ),
    (
        (
            "do antibiotics help with cough",
            "antibiotics for cough",
            "can antibiotic cure cough",
        ),
        "Only bacterial cough-related infections may need antibiotics. Most coughs are viral and do not require antibiotics.",
    ),
    (
        (
            "can antibiotics cure uti",
            "antibiotics for uti",
            "urinary tract infection antibiotic",
        ),
        "Yes, antibiotics are commonly used to treat urinary tract infections. A doctor should prescribe the correct type for your case.",
    ),
    (
        (
            "what happens if i take too many antibiotics",
            "too much antibiotics",
            "antibiotic overdose",
        ),
        "Taking too much can cause side effects and increase resistance risk. Seek medical help immediately if overdose is suspected.",
    ),
    (
        (
            "can antibiotics damage my body",
            "are antibiotics harmful to body",
            "antibiotics harm body",
        ),
        "When used correctly, antibiotics are generally safe. Misuse can cause side effects, resistance, and harm to beneficial bacteria.",
    ),
    (
        (
            "can elderly people take antibiotics",
            "antibiotics for elderly",
            "old people antibiotics",
        ),
        "Yes, elderly patients can take antibiotics, but doses may need adjustment based on kidney function and health conditions.",
    ),
    (
        (
            "can i take antibiotics with vitamins",
            "antibiotics and vitamins",
            "vitamins while taking antibiotics",
        ),
        "Some vitamins can interact with antibiotics. It is often safer to take them at different times and confirm with a doctor or pharmacist.",
    ),
    (
        (
            "can i exercise while taking antibiotics",
            "exercise on antibiotics",
            "workout while on antibiotics",
        ),
        "Light activity is usually fine if you feel well. Rest is recommended when you are unwell, and strenuous exercise should be avoided with certain antibiotics.",
    ),
    (
        (
            "what if i feel worse after taking antibiotics",
            "feel worse on antibiotics",
            "antibiotic made me worse",
        ),
        "If symptoms worsen, seek medical attention promptly. If you have severe symptoms such as breathing difficulty, get urgent care immediately.",
    ),
    (
        (
            "i still have fever after 3 days of antibiotics",
            "fever after 3 days antibiotics",
            "still fever on antibiotics",
        ),
        "Some infections take time to improve, but persistent fever after 2 to 3 days needs medical review. Please consult your doctor.",
    ),
    (
        (
            "symptoms gone after 2 days should i continue antibiotics",
            "feel better should i continue antibiotics",
            "continue antibiotics after feeling better",
        ),
        "Yes. You should complete the full course to eliminate bacteria fully and reduce the chance of resistance.",
    ),
    (
        (
            "can i take antibiotics with paracetamol",
            "paracetamol and antibiotics",
            "antibiotics plus paracetamol",
        ),
        "In most cases, they can be taken together. Follow your prescription and ask a healthcare professional if you are unsure.",
    ),
    (
        (
            "can i take antibiotics with ibuprofen",
            "ibuprofen and antibiotics",
            "antibiotics plus ibuprofen",
        ),
        "Usually yes, but this depends on your condition and medication type. Ask a doctor or pharmacist to confirm safety.",
    ),
    (
        (
            "can i mix two antibiotics together",
            "combine two antibiotics",
            "take two antibiotics at once",
        ),
        "Do not combine antibiotics unless specifically prescribed by a doctor. Incorrect combinations can be harmful.",
    ),
    (
        (
            "what time should i take my antibiotic",
            "best time to take antibiotics",
            "antibiotic timing",
        ),
        "Take antibiotics at evenly spaced intervals, such as every 8 or 12 hours, based on your prescription. Consistent timing helps maintain effectiveness.",
    ),
    (
        (
            "what if i vomit after taking antibiotics",
            "vomit after antibiotic dose",
            "threw up after antibiotics",
        ),
        "If vomiting happens shortly after a dose, you may need guidance on whether to repeat it. Contact your doctor or pharmacist promptly.",
    ),
    (
        (
            "can i drink milk with antibiotics",
            "milk and antibiotics",
            "take antibiotics with milk",
        ),
        "Some antibiotics should not be taken with milk because absorption can be reduced. Check your medication instructions.",
    ),
    (
        (
            "what foods should i eat while taking antibiotics",
            "diet while taking antibiotics",
            "foods with antibiotics",
        ),
        "Eat balanced meals and stay hydrated. Probiotic foods like yogurt may help support gut health for some people.",
    ),
    (
        (
            "how do i know if im allergic to an antibiotic",
            "how do i know if i'm allergic to an antibiotic",
            "antibiotic allergy signs",
        ),
        "Possible allergy signs include rash, itching, swelling, or breathing difficulty. Seek emergency care immediately for severe reactions.",
    ),
    (
        (
            "i got a rash after taking amoxicillin what should i do",
            "rash after amoxicillin",
            "amoxicillin allergy rash",
        ),
        "Stop taking the medicine and seek medical attention immediately. This may indicate an allergic reaction.",
    ),
    (
        (
            "can diabetics take antibiotics",
            "antibiotics for diabetes",
            "diabetic taking antibiotics",
        ),
        "Yes, but monitoring is important because some antibiotics can affect blood sugar levels. Consult your doctor for safe use.",
    ),
    (
        (
            "can i take antibiotics if i have kidney problems",
            "antibiotics kidney disease",
            "kidney problem antibiotics",
        ),
        "Some antibiotics need dose adjustment in kidney disease. Always consult a doctor before taking them.",
    ),
    (
        (
            "can antibiotics affect my heart",
            "antibiotics heart rhythm",
            "heart side effects antibiotics",
        ),
        "Certain antibiotics can affect heart rhythm in some people. This is uncommon but needs attention in high-risk patients.",
    ),
    (
        (
            "why is antibiotic resistance dangerous",
            "danger of antibiotic resistance",
            "antibiotic resistance risk",
        ),
        "Antibiotic resistance makes infections harder to treat and can lead to longer illness and more complications. Responsible antibiotic use helps prevent this.",
    ),
    (
        (
            "can using antibiotics too often weaken them",
            "antibiotics too often",
            "overuse antibiotics effectiveness",
        ),
        "Yes. Overuse can make bacteria resistant, which reduces antibiotic effectiveness over time.",
    ),
    (
        (
            "how should i store antibiotics",
            "store antibiotics",
            "antibiotic storage",
        ),
        "Store antibiotics in a cool, dry place away from direct sunlight. Some types may require refrigeration, so check the label.",
    ),
    (
        (
            "can i travel while taking antibiotics",
            "travel with antibiotics",
            "taking antibiotics while traveling",
        ),
        "Yes, but follow your dosing schedule and carry enough medicine for the trip. Keep medicines stored properly during travel.",
    ),
    (
        (
            "can antibiotics treat ear infections",
            "antibiotics for ear infection",
            "ear infection antibiotic",
        ),
        "Bacterial ear infections may require antibiotics, but some improve without them. A doctor can confirm whether antibiotics are needed.",
    ),
    (
        (
            "do i need antibiotics for sinus infection",
            "antibiotics for sinus infection",
            "sinus infection antibiotic needed",
        ),
        "Most sinus infections are viral and improve without antibiotics. If symptoms last more than 7 to 10 days, consult a doctor.",
    ),
    (
        (
            "can antibiotics work instantly",
            "do antibiotics work instantly",
            "instant effect antibiotics",
        ),
        "No, antibiotics do not work instantly. Symptoms usually improve over a few days as bacteria are reduced.",
    ),
    (
        (
            "can i drive after taking antibiotics",
            "drive while on antibiotics",
            "antibiotics and driving",
        ),
        "Most antibiotics do not affect driving. If you feel dizzy, weak, or unwell, avoid driving and seek advice.",
    ),
    (
        (
            "when should i stop taking antibiotics immediately",
            "stop antibiotics immediately",
            "urgent stop antibiotic",
        ),
        "Stop and seek urgent medical help if you develop severe rash, facial or throat swelling, or difficulty breathing.",
    ),
    (
        (
            "are antibiotics safe for babies",
            "antibiotics for infants",
            "baby antibiotics safety",
        ),
        "Some antibiotics are safe for infants, but they must be prescribed by a doctor with the correct dose.",
    ),
    (
        (
            "can i crush my antibiotic tablet",
            "crush antibiotic tablet",
            "split or crush antibiotics",
        ),
        "Some antibiotic tablets can be crushed, but others should not. Check product instructions or ask a pharmacist first.",
    ),
    (
        (
            "why do i need to drink plenty of water with antibiotics",
            "drink water with antibiotics",
            "water and antibiotics",
        ),
        "Water helps support medicine absorption and overall recovery. It also helps reduce dehydration risk during illness.",
    ),
    (
        (
            "my friend said antibiotics cure everything",
            "do antibiotics cure everything",
            "antibiotics cure all",
        ),
        "No. Antibiotics only treat bacterial infections, not all illnesses.",
    ),
    (
        (
            "can i just try antibiotics and see if i get better",
            "try antibiotics first",
            "self medicate antibiotics",
        ),
        "Self-medicating with antibiotics is not recommended. Incorrect use can cause side effects, treatment failure, and resistance.",
    ),
    (
        (
            "how many days have you been sick",
            "do follow up questions",
            "ask me follow up questions",
        ),
        "To guide you safely, please share:\n- How many days you have been sick\n- Any medicine allergies\n- Current medications\n- Your age group",
    ),
    (
        (
            "i have cough and fever",
            "cough and fever",
            "i have fever and cough",
        ),
        "How long have you had these symptoms?\n- Less than 3 days\n- More than 3 days",
    ),
    (
        (
            "more than 3 days",
            "its been more than 3 days",
            "more than three days",
        ),
        "Do you have difficulty breathing or chest pain?\n- Yes\n- No",
    ),
    (
        (
            "yes difficulty breathing",
            "yes chest pain",
            "yes i have difficulty breathing",
        ),
        "This may need urgent medical attention. Please consult a healthcare provider immediately.",
    ),
]
CURATED_GENERAL_DISCLAIMER = (
    "This chatbot provides general information only. "
    "It does NOT replace professional medical advice. "
    "Always consult a licensed healthcare provider."
)


@dataclass(frozen=True)
class AntibioticCatalogItem:
    name: str
    klass: str
    common_use: str
    warning: str
    allergy_tags: set[str]

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "class": self.klass,
            "common_use": self.common_use,
            "warning": self.warning,
        }

    def to_medicine_description(self) -> str:
        return "\n".join(
            [
                f"Medicine: {self.name}",
                f"Class: {self.klass}",
                f"Common use: {self.common_use}",
                f"Warning: {self.warning}",
            ]
        )


def _row_to_item(row: object) -> AntibioticCatalogItem:
    r = dict(row)
    return AntibioticCatalogItem(
        name=str(r["name"]),
        klass=str(r["class"]),
        common_use=str(r["common_use"]),
        warning=str(r["warning"]),
        allergy_tags={
            t.strip().lower() for t in str(r.get("allergy_tags", "")).split(",") if t.strip()
        },
    )


def search_antibiotics(query: str) -> list[AntibioticCatalogItem]:
    q = normalize_text(query)
    with connect() as con:
        if not q:
            rows = fetch_all(
                con,
                """
                SELECT name, class, common_use, warning, allergy_tags
                FROM Medicines
                ORDER BY name ASC
                LIMIT 50
                """,
                (),
            )
        else:
            like = f"%{q}%"
            rows = fetch_all(
                con,
                """
                SELECT name, class, common_use, warning, allergy_tags
                FROM Medicines
                WHERE lower(name) LIKE ? OR lower(class) LIKE ? OR lower(common_use) LIKE ?
                ORDER BY name ASC
                LIMIT 50
                """,
                (like, like, like),
            )
    return [_row_to_item(row) for row in rows]


def find_antibiotic(name: str) -> AntibioticCatalogItem | None:
    q = normalize_text(name)
    if not q:
        return None

    with connect() as con:
        row = fetch_one(
            con,
            """
            SELECT name, class, common_use, warning, allergy_tags
            FROM Medicines
            WHERE lower(name) = ?
            LIMIT 1
            """,
            (q,),
        )
        if row is not None:
            return _row_to_item(row)

        row = fetch_one(
            con,
            """
            SELECT name, class, common_use, warning, allergy_tags
            FROM Medicines
            WHERE lower(name) LIKE ?
            ORDER BY name ASC
            LIMIT 1
            """,
            (f"%{q}%",),
        )
    return _row_to_item(row) if row is not None else None


def find_curated_medicine_info(user_text: str) -> tuple[str, str] | None:
    t = normalize_text(user_text)
    if not t:
        return None

    for med_name, info in CURATED_MEDICINE_INFO.items():
        if med_name in t:
            return med_name.title(), info
    return None


def _is_tips_intent(text: str) -> bool:
    tip_phrases = (
        "tips",
        "tip for taking",
        "tip in taking",
        "how to use",
        "how do i use",
        "how to take",
        "how do i take",
        "taking",
        "use the",
    )
    return any(p in text for p in tip_phrases)


def find_curated_medicine_tips(user_text: str) -> tuple[str, str] | None:
    t = normalize_text(user_text)
    if not t or not _is_tips_intent(t):
        return None

    for med_name, tips in CURATED_MEDICINE_TIPS.items():
        if med_name in t:
            return med_name.title(), tips
    return None


def find_curated_general_faq(user_text: str) -> str | None:
    t = normalize_text(user_text)
    if not t:
        return None

    for patterns, answer in CURATED_GENERAL_FAQ:
        if any(pattern in t for pattern in patterns):
            return f"{answer}\n\n{CURATED_GENERAL_DISCLAIMER}"
    return None
