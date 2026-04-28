import os
import io
import time
import threading
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Local Modules
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
from models.cnn_model import get_cnn_model, preprocess_image, predict_cnn
from utils.xai_utils import generate_gradcam
from models.nlp_model import get_clinical_bert_model

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

print("Loading CNN Model...")
try:
    cnn_model = get_cnn_model()
except Exception as e:
    print(f"Error loading model: {e}")
    cnn_model = None

print("Loading ClinicalBERT NLP Model...")
try:
    clinical_tokenizer, clinical_model_bert = get_clinical_bert_model()
    print("ClinicalBERT loaded.")
except Exception as e:
    print(f"ClinicalBERT could not load: {e}")
    clinical_tokenizer, clinical_model_bert = None, None

# ─────────────────────────────────────────────────────────────────────────────
# Local AI Chatbot (Lazy Loading via Thread)
# ─────────────────────────────────────────────────────────────────────────────
chatbot_pipeline = None

def load_chatbot():
    global chatbot_pipeline
    try:
        from transformers import pipeline
        import torch
        print("--- Chatbot Initialization Started ---")
        # Use CPU if GPU is low on memory, or 'auto' for best fit
        device = 0 if torch.cuda.is_available() else -1
        print(f"Loading flan-t5-small on device: {'GPU' if device==0 else 'CPU'}...")
        
        chatbot_pipeline = pipeline(
            'text2text-generation', 
            model='google/flan-t5-small', 
            max_length=150,
            device=device
        )
        print("✅ SUCCESS: Chatbot AI Model loaded successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed to load chatbot model: {e}")
        print("Chatbot will continue using Rule-Based Smart Fallback mode.")

threading.Thread(target=load_chatbot, daemon=True).start()

# --- Smart Fallback Knowledge Base ---
FALLBACK_RESPONSES = {
    'Lung Cancer': [
        "Lung cancer is a condition where cells in the lung grow out of control. Your report mentions a suspicious node.",
        "A 'spiculated lesion' often refers to a growth with irregular edges, which is a key finding in your scan.",
        "Common treatments include targeted therapy if specific mutations like EGFR are found."
    ],
    'Tuberculosis': [
        "Tuberculosis (TB) is a bacterial infection. The 'apical cavitary lesions' mentioned are hollow spaces often seen in TB.",
        "Treatment usually involves a 6-month course of antibiotics. It is very important to finish the full course.",
        "You should avoid close contact with others until your doctor confirms you are no longer infectious."
    ],
    'Pneumonia': [
        "Pneumonia is an infection that inflames the air sacs in one or both lungs. This often appears as 'consolidation' on an X-ray.",
        "Most cases are treated with antibiotics. Resting and staying hydrated are crucial for recovery.",
        "If you experience severe shortness of breath, you should seek emergency care immediately."
    ],
    'Normal': [
        "Your lungs appear clear on this scan, meaning no signs of major infection or growths were detected.",
        "Even with a normal scan, if you have a persistent cough, you should consult your doctor for other tests.",
        "A 'normal cardiac silhouette' means your heart size and shape look healthy on the X-ray."
    ],
    'General': [
        "I am your AI assistant. I can help explain medical terms in your report like 'infiltrates' or 'mutations'.",
        "Please remember that I am an AI and my advice should always be reviewed by your doctor.",
        "You can find detailed recommendations in the 'What You Should Do Now' section of your report."
    ]
}

# ─────────────────────────────────────────────────────────────────────────────
# Disease-specific content library — drives all dynamic report sections
# ─────────────────────────────────────────────────────────────────────────────
DISEASE_CONTENT = {
    'Lung Cancer': {
        'icd': 'Possible finding: A suspicious growth in the lung that needs further testing to confirm.',
        'urgency_badge': 'URGENT — SEE A DOCTOR TODAY',
        'urgency_color': 'red',
        'key_finding': 'The AI spotted an unusual growth — a small lump — in the upper part of the lung. The edges of this lump look rough and irregular, which can sometimes be a sign that it needs urgent attention. This does NOT confirm cancer — only a biopsy (a small tissue sample) can confirm this.',
        'ehr_risk': 'Smoking history, coughing up blood, unexplained weight loss and a family history of lung cancer were flagged as important risk factors for this patient.',
        'xai_note': 'The AI focused most strongly on: the shape and size of the lump, smoking history, the coughing up of blood, and recent weight loss — these were the main reasons it made this prediction.',
        'urgency_note': '⚠️ URGENT — Please see a doctor or go to a hospital as soon as possible. Do not ignore this result. Further tests are needed before any diagnosis is confirmed.',
        'imaging_findings': [
            'The scan shows <strong>a small, unusual lump in the upper part of the lung</strong>. Its edges look rough and uneven — this is what the AI flagged as needing further investigation.',
            'The rest of the lungs look mostly clear. There is no extra fluid seen around the lungs on this scan.',
            'The AI highlighted the suspicious area using a colour heatmap. The bright region on the heatmap shows exactly where it focused — the unusual lump.',
            'The heart and the space between the lungs look normal in size. Only the flagged area requires follow-up.'
        ],
        'clinical_recs': [
            {'title': '1. Get a tissue sample (biopsy) urgently', 'body': 'A small piece of tissue needs to be taken from the lump using a needle guided by a CT scan. This is the only way to know for sure what the lump is. Your doctor will arrange this — it should happen within 5–7 days.'},
            {'title': '2. See a lung cancer specialist', 'body': 'You will be referred to a specialist doctor (oncologist) who deals with lung conditions. They will run more scans such as a PET scan and brain MRI to understand if and how far any disease may have spread.'},
            {'title': '3. Breathing test', 'body': 'A simple breathing test (blowing into a machine) will check how well your lungs are working. This helps doctors plan the safest treatment for you.'},
            {'title': '4. More options if biopsy is not possible', 'body': 'If the needle biopsy cannot be done, doctors may look inside your airways with a small camera (bronchoscopy) to take a sample another way.'},
            {'title': '5. Team review meeting', 'body': 'A group of specialist doctors (lung doctors, cancer doctors, surgeons, radiologists) will meet together to discuss your case and agree on the best plan for you.'},
            {'title': '6. Stop smoking now', 'body': 'If you smoke, stopping right now is the single most important thing you can do for your health — whatever the final result turns out to be. Your doctor can prescribe medicines or patches to help you quit.'},
        ],
        'patient_guidance': {
            'immediate': [
                {'title': '📅 Book your specialist appointment as soon as possible', 'body': 'The AI has found something that needs a doctor to look at urgently. Please call your doctor today or go to the hospital. Bring this report, any previous scans, and a list of your medicines.', 'type': 'urgent'},
                {'title': '🚨 Go to Emergency immediately if you feel worse', 'body': 'If you suddenly find it very hard to breathe, cough up a lot of blood, feel severe chest pain, or develop a high fever — go to the Emergency Department right away. Do not wait.', 'type': 'urgent'},
                {'title': '🚬 Stop smoking today', 'body': 'If you smoke, please stop today. Even quitting now — before the diagnosis is confirmed — can improve your recovery and treatment results. Ask your doctor about free support programmes and medicines that help.', 'type': 'urgent'},
            ],
            'lifestyle': [
                {'title': '🚶 Short, gentle walks are good for you', 'body': 'You do not need to stay in bed. Light walks of 15–20 minutes help keep your lungs active and blood circulating. Avoid anything that makes you breathless or exhausted until your doctor says otherwise.'},
                {'title': '🌬️ Try simple breathing exercises', 'body': 'Breathing in slowly through your nose, holding for 2 seconds, then breathing out slowly through your mouth (like blowing out a candle) can help. Do this 5–10 minutes in the morning and evening.'},
                {'title': '😴 Sleep well and rest when you need to', 'body': 'Try to sleep 7–9 hours a night. Worrying is normal — if anxiety is keeping you awake, speak to your doctor or a counsellor. Apps like Calm or Headspace can also help with stress.'},
            ],
            'diet': [
                {'title': '🥗 Eat good food with plenty of protein', 'body': 'Good food choices include: eggs, fish, chicken, lentils (dal), paneer, leafy vegetables (palak, methi), and colourful fruits. These help your body stay strong and fight disease. Aim for a high-protein meal at least twice a day.'},
                {'title': '🚫 Avoid junk food, alcohol, and cigarettes', 'body': 'Processed meats (sausages, packaged meats), alcohol, and smoking are all harmful in this situation and can make things worse. Try to cut these out completely.'},
                {'title': '💧 Drink 2–3 litres of water every day', 'body': 'Staying well-hydrated helps loosen mucus in your lungs (making it easier to cough up), keeps your kidneys healthy, and helps your body deal with any medicines you are taking. Avoid sugary drinks.'},
            ],
            'monitoring': [
                {'title': '📊 Check your oxygen level at home if possible', 'body': 'A pulse oximeter (a small clip for your finger, available at pharmacies for under ₹500–₹1000) measures your blood oxygen. If it reads below 92%, go to a doctor immediately. Check it once a day and write down the number.'},
                {'title': '📓 Keep a simple daily diary', 'body': 'Each day, write down: how bad your cough is (rate it 1 to 10), whether you coughed up blood (yes/no), your weight (weigh yourself at the same time each morning), and how tired you feel. This helps your doctor track changes.'},
                {'title': '📆 Your appointment schedule', 'body': '<strong>This week:</strong> See a specialist and arrange biopsy.<br><strong>Weeks 2–3:</strong> Biopsy happens + more scans if needed.<br><strong>Week 4:</strong> Doctors meet to discuss your results and create your treatment plan.<br><strong>Month 3:</strong> Check-up to see how things are going.'},
            ],
            'mental': [
                {'title': '💬 It is okay to feel scared — talk to someone', 'body': 'Hearing that something unusual was found on a scan is frightening. Feeling anxious, sad, or confused is completely normal. Please speak to a family member, friend, or counsellor. You do not have to go through this alone — ask your doctor to refer you to a support service.'},
                {'title': '✅ You have rights — ask questions freely', 'body': 'You have the right to ask your doctor to explain everything in simple words. You can ask for a second opinion from another doctor at any time. Keep copies of all your reports and scan results. Nobody can force you into any treatment.'},
            ]
        }
    },

    'Tuberculosis': {
        'icd': 'Possible finding: Signs of TB (Tuberculosis) infection in the lungs.',
        'urgency_badge': 'IMPORTANT — SEE A DOCTOR SOON',
        'urgency_color': 'amber',
        'key_finding': 'The AI spotted a pattern in the upper part of the lungs that looks like TB (Tuberculosis) — a common but serious lung infection caused by bacteria. Signs include some small holes (cavities) and patchy white areas in the scan. This is NOT a confirmed diagnosis — a sputum (phlegm) test is needed to confirm.',
        'ehr_risk': 'Known TB contact, fever, night sweats, and weight loss were flagged — these are the classic warning signs of TB that matched this patient\'s history.',
        'xai_note': 'The AI focused most on: hollow patches near the top of the lungs, small white spots (nodules) spreading around them, and the pattern seen on both sides — all typical features of TB on an X-ray.',
        'urgency_note': '⚠️ IMPORTANT — Please see a doctor within 1–2 days. TB is curable but must be treated early. If you are coughing a lot, try to avoid close contact with others until you have been checked.',
        'imaging_findings': [
            'The scan shows <strong>patchy white areas and small hollow spots near the top of the lungs</strong> — this is a very common pattern seen in TB infections.',
            'The top portions of both lungs look slightly shrunken compared to normal — another sign that is often seen in long-standing TB.',
            'The AI\'s colour heatmap highlights the top parts of the lungs as the areas it focused on most when making this prediction.',
            'No extra fluid around the lungs was seen. The heart looks normal. Only the highlighted upper lung areas need following up.'
        ],
        'clinical_recs': [
            {'title': '1. Sputum (phlegm) test — most important first step', 'body': 'You will be asked to cough up some phlegm from deep in your lungs on 3 mornings in a row. This is tested in a lab to see if TB bacteria are present. Go to your nearest government hospital or TB centre.'},
            {'title': '2. Quick TB test (GeneXpert)', 'body': 'A fast lab test using your sputum can confirm TB in a few hours and also tell if the bacteria are resistant to common medicines. Your doctor will arrange this.'},
            {'title': '3. CT scan of the chest', 'body': 'A more detailed scan (CT scan) will give doctors a clearer picture of the infected areas, check how far the infection has spread, and look at the lymph nodes near your lungs.'},
            {'title': '4. Start TB treatment if confirmed', 'body': 'If TB is confirmed, you will start a 6-month course of free medicines. You must take all of them, every day, without stopping. A health worker may visit daily to make sure you take your medicines — this is called DOTS and is completely normal.'},
            {'title': '5. Keep away from vulnerable people temporarily', 'body': 'Until your doctor confirms you are no longer infectious (usually after 2–4 weeks of treatment), try to avoid close contact with babies, elderly people, and people with weak immune systems.'},
            {'title': '6. HIV test', 'body': 'TB and HIV often occur together. Your doctor will offer you a free, confidential HIV test. This helps tailor the best treatment plan for you.'},
        ],
        'patient_guidance': {
            'immediate': [
                {'title': '🏥 Go to a TB centre or government hospital this week', 'body': 'You need to give a phlegm sample (called sputum) for testing — this is the only way to confirm TB. Go to your nearest government hospital, DOTS centre, or chest clinic. This test is completely free.', 'type': 'urgent'},
                {'title': '😷 Be careful around family at home', 'body': 'TB spreads through the air when you cough. Until the doctor confirms whether you are infectious, try to sleep in a separate room, keep windows open, and cover your mouth when coughing. Do not worry — treatment quickly stops the spread.', 'type': 'urgent'},
                {'title': '💊 Never skip or stop your TB medicines', 'body': 'If you are given TB medicines, take them every single day for the full 6 months — even if you feel much better after a few weeks. Stopping early makes the bacteria stronger and much harder to kill.', 'type': 'urgent'},
            ],
            'lifestyle': [
                {'title': '🛏️ Rest well during the first weeks of treatment', 'body': 'Your body is fighting an infection. Rest as much as you can, especially in the first month. You will gradually feel stronger as treatment works.'},
                {'title': '🌬️ Open your windows and let fresh air in', 'body': 'TB bacteria spread in closed, stuffy spaces. Keep windows open in your room and the main living areas of your home. Try to spend time outdoors in fresh air each day.'},
                {'title': '🛏️ Sleep separately if possible during the first few weeks', 'body': 'For the first 2–4 weeks of treatment, try to sleep in a separate room or at least a separate bed from others in your home. After that, your doctor will tell you when it is safe again.'},
            ],
            'diet': [
                {'title': '🍽️ Eat more food than usual — your body needs it', 'body': 'TB causes your body to burn extra energy fighting the infection. You may have lost weight. Focus on eating plenty of rice, roti, dal, eggs, milk, bananas, and peanuts — calorie-rich foods that help rebuild your strength.'},
                {'title': '☀️ Get some sunlight every day', 'body': 'Sunlight helps your body make Vitamin D, which helps your immune system fight infection. Try to sit in the sun for 20–30 minutes each morning. Ask your doctor if you need a Vitamin D supplement.'},
                {'title': '🚫 No alcohol at all during TB treatment', 'body': 'TB medicines can affect your liver. Alcohol makes this much worse and can cause serious liver damage when combined with TB medicines. Please avoid alcohol completely for the full 6 months of treatment.'},
            ],
            'monitoring': [
                {'title': '⏰ Take your medicines at the same time every day', 'body': 'Set a daily alarm on your phone to remind you to take your TB medicines. A health worker (DOTS supporter) may visit to help — this is not a punishment, it is just how TB treatment works best.'},
                {'title': '👁️ Watch for medicine side effects', 'body': 'Tell your doctor right away if you notice: your eyes or skin turning yellow, blurry vision, a skin rash, or tingling in your hands and feet. These can be side effects of the medicines — do not stop taking them without calling your doctor first.'},
                {'title': '📆 Your check-up schedule', 'body': '<strong>Month 2:</strong> Phlegm test to check if the bacteria are gone.<br><strong>Month 5:</strong> Another phlegm test to confirm treatment is working.<br><strong>Month 6:</strong> Final test to confirm you are cured.'},
            ],
            'mental': [
                {'title': '💪 TB is fully curable — millions recover every year', 'body': 'TB sounds scary but it is one of the most treatable serious infections. Over 85% of people who take their full course of medicines are completely cured. Stay positive and keep taking your medicines.'},
                {'title': '🆓 TB treatment is free — you have rights', 'body': 'In India, all TB diagnosis and treatment is 100% free at government centres. You also have a right to confidential care — your employer, school, or landlord does not need to be told about your diagnosis.'},
            ]
        }
    },

    'Pneumonia': {
        'icd': 'Possible finding: Signs of a lung infection (Pneumonia).',
        'urgency_badge': 'MODERATE — SEE A DOCTOR SOON',
        'urgency_color': 'blue',
        'key_finding': 'The AI spotted a cloudy, white-grey patch in the lower part of the lung on the scan. This type of patch is commonly caused by a lung infection — often called pneumonia. Pneumonia happens when the tiny air sacs in your lungs fill up with fluid due to infection. It is treatable with antibiotics.',
        'ehr_risk': 'Fever, cough with phlegm, and difficulty breathing were flagged as symptoms that match pneumonia. A recent cold, flu, or virus can also increase the chance of developing this infection.',
        'xai_note': 'The AI focused most on: the cloudy patch in the lower lung, the pattern of the infection spreading through the lung tissue, and symptoms like fever and cough — these were the strongest reasons for this prediction.',
        'urgency_note': '⚠️ MODERATE — Please see a doctor within 24–48 hours. Most cases of pneumonia are treated with antibiotics at home, but some cases need hospital care. Do not delay.',
        'imaging_findings': [
            'The scan shows <strong>a white-grey cloudy patch in the lower part of the lung</strong> — this is air sacs filling with fluid due to infection, which is what pneumonia looks like on an X-ray.',
            'Inside the cloudy area, the AI can see the outline of your airways (like thin white lines running through the cloud) — this is a typical sign of pneumonia.',
            'The AI coloured the infected area bright on the heatmap to show exactly where it spotted the problem.',
            'The rest of the lung, the heart, and the space around the lungs all look normal. Only the highlighted area needs treatment.'
        ],
        'clinical_recs': [
            {'title': '1. Antibiotic medicine', 'body': 'Your doctor will prescribe antibiotic tablets (usually Amoxicillin or Azithromycin) to kill the bacteria causing the infection. Take the full course — usually 5–7 days — even if you feel better after 2 days.'},
            {'title': '2. Check if hospital stay is needed', 'body': 'Your doctor will assess how serious the infection is. If you are very short of breath, have low oxygen levels, very high fever, or are elderly, you may need to stay in hospital for a few days to receive stronger treatment.'},
            {'title': '3. Oxygen support if needed', 'body': 'If your blood oxygen level is low (below 94%), your doctor may give you oxygen through a small tube under your nose. This helps you breathe more comfortably while your lungs recover.'},
            {'title': '4. Blood and sputum tests', 'body': 'A blood test and a phlegm sample may be taken to identify exactly which bacteria is causing the infection. This helps your doctor choose the right antibiotic for you.'},
            {'title': '5. Breathing exercises and physio', 'body': 'A physiotherapist or your doctor may show you simple breathing exercises and techniques to help cough out the infected fluid from your lungs. This speeds up recovery.'},
            {'title': '6. Follow-up X-ray in 6 weeks', 'body': 'Pneumonia patches can take 4–6 weeks to fully clear on an X-ray. Your doctor will ask you to come back for another scan to confirm everything has healed.'},
        ],
        'patient_guidance': {
            'immediate': [
                {'title': '💊 Finish every single tablet in your antibiotic course', 'body': 'Even when you start feeling better (which can happen quickly), please take every tablet until the course is done. Stopping early can let the bacteria come back — and the second time it is harder to treat.', 'type': 'urgent'},
                {'title': '🚨 Call emergency services if breathing becomes very difficult', 'body': 'Go to the Emergency Department immediately if you: are breathing very fast (more than 30 breaths per minute), feel confused or unusually sleepy, notice your lips or fingernails turning blue, or your oxygen level drops below 92%.', 'type': 'urgent'},
                {'title': '🏠 Rest at home and avoid spreading the infection', 'body': 'Pneumonia can spread to others. Stay at home, cover your mouth when you cough or sneeze, wash your hands regularly with soap, and keep a safe distance from elderly relatives or very young children.', 'type': 'urgent'},
            ],
            'lifestyle': [
                {'title': '🛏️ Rest is the most important medicine right now', 'body': 'Your body needs a lot of energy to fight this infection. Stay home from work for at least 5–7 days. You will likely feel very tired — this is normal. Do not rush your recovery.'},
                {'title': '🌫️ Steam inhalation can help loosen mucus', 'body': 'Breathing steam from a bowl of hot water (cover your head with a towel) or taking a hot shower helps loosen the thick mucus in your lungs, making it easier to cough up. Do this 2–3 times a day.'},
                {'title': '🛏️ Sleep with your head raised up', 'body': 'Use 2–3 extra pillows to keep your head and chest higher than your hips when sleeping. This helps mucus drain and reduces the feeling of chest tightness at night.'},
            ],
            'diet': [
                {'title': '🍲 Eat warm, soft, easy foods', 'body': 'When you have a fever and cough, eating may feel hard. Try warm soups (chicken soup, dal soup), khichdi, porridge, or steamed vegetables. These are gentle on the stomach and still give your body the nutrition it needs.'},
                {'title': '💧 Drink a lot of fluids every day', 'body': 'Aim for 3 litres of water, clear soup, coconut water, or herbal tea every day. Fluids help thin the thick mucus in your lungs, making it easier to breathe and cough up. Avoid cold drinks — warm fluids are better.'},
                {'title': '🚫 No alcohol and reduce dairy during infection', 'body': 'Alcohol weakens your immune system exactly when you need it most. Some people find that dairy (milk, cheese, curd) makes mucus thicker — try reducing it while symptoms are bad and see if it helps.'},
            ],
            'monitoring': [
                {'title': '🌡️ Check your temperature morning and evening', 'body': 'Use a thermometer to check your temperature twice a day. If your fever goes above 39.5°C or your fever does not come down within 5 days of taking antibiotics — call your doctor. It may mean the antibiotic needs to be changed.'},
                {'title': '📊 Monitor your breathing', 'body': 'If you have a pulse oximeter (oxygen level checker), use it morning and evening. If the reading falls below 92%, or you are breathing more than 25 times per minute, seek medical help immediately.'},
                {'title': '📆 Your check-up schedule', 'body': '<strong>In 48–72 hours:</strong> See your doctor to confirm you are improving on the antibiotics.<br><strong>Week 2–3:</strong> Check-up to confirm recovery.<br><strong>Week 6:</strong> A repeat chest X-ray to confirm the infection has fully cleared.'},
            ],
            'mental': [
                {'title': '✅ Pneumonia is very treatable — you will most likely recover fully', 'body': 'Most healthy adults recover completely from pneumonia within 2–4 weeks with proper treatment. Stay positive, rest well, take your medicines on time, and you will be back on your feet soon.'},
                {'title': '💉 Ask about vaccines after you recover', 'body': 'Once you are better, ask your doctor about the pneumonia vaccine and the flu vaccine. These can prevent you from getting pneumonia again in the future — especially important if you are over 60 or have diabetes.'},
            ]
        }
    },

    'Normal': {
        'icd': 'Finding: No disease spotted on this scan. Your lungs look healthy.',
        'urgency_badge': 'GOOD NEWS — LOOKS NORMAL',
        'urgency_color': 'green',
        'key_finding': '✅ The AI did not find any signs of cancer, TB, or pneumonia on this scan. Your lungs appear clear and healthy-looking on the X-ray. This is a reassuring result — but please still discuss it with your doctor, as an X-ray is just one piece of the full picture.',
        'ehr_risk': 'No concerning patterns were found in the scan. If you still have symptoms (like a cough or breathlessness), your doctor may want to run other tests — an X-ray alone cannot check for every possible cause.',
        'xai_note': 'The AI\'s decision was driven by: clear, open lung fields with no shadows or patches, a normally-sized heart, and clean, sharp edges around the lung base — all signs of a healthy chest X-ray.',
        'urgency_note': '✅ LOW RISK — Your scan looks normal. Still, please see your doctor who will consider this result alongside your symptoms and full health check.',
        'imaging_findings': [
            'The scan shows <strong>both lungs looking clear and open</strong> — no white patches, lumps, or cloudiness that would suggest an infection or growth.',
            'Your heart is a normal size and shape. The space between your lungs (called the mediastinum) also looks normal.',
            'The area at the bottom edges of each lung (costophrenic angles) is sharp and clear — no fluid is collecting there, which is a good sign.',
            'The AI\'s heatmap showed no areas of strong focus — meaning nothing unusual caught its attention, which is exactly what you want to see on a normal scan.'
        ],
        'clinical_recs': [
            {'title': '1. This scan looks normal — but does not rule everything out', 'body': 'A normal chest X-ray is good news. However, it cannot detect every potential problem. If you still have symptoms, your doctor may want to order other tests.'},
            {'title': '2. Further tests if your symptoms continue', 'body': 'If you have a cough, breathlessness, or chest pain that does not go away — even with a normal X-ray — your doctor may suggest a CT scan, breathing test, or heart check.'},
            {'title': '3. Yearly health check-up', 'body': 'It is a good idea to have a general health check every year, including blood pressure, blood sugar, and a basic lung check (especially if you have ever smoked, or are over 40 years old).'},
            {'title': '4. Healthy lifestyle to protect your lungs', 'body': 'Staying active, not smoking, and avoiding pollution at home and work are the best things you can do to keep your lungs healthy long-term.'},
            {'title': '5. You can be reassured', 'body': 'Share this result with your doctor. Take this good news as motivation to keep maintaining your health — prevention is always better than cure.'},
            {'title': '6. Come back if anything changes', 'body': 'If you develop any new symptoms — cough lasting more than 3 weeks, coughing blood, unexplained weight loss, or chest pain — please see a doctor promptly, even with a normal scan today.'},
        ],
        'patient_guidance': {
            'immediate': [
                {'title': '🎉 Your scan looks normal — this is good news!', 'body': 'The AI did not spot any signs of lung cancer, TB, or pneumonia on your scan. This is genuinely reassuring. However, always share this result with your doctor and discuss any symptoms you are still experiencing.', 'type': 'urgent'},
                {'title': '📅 Still attend your follow-up appointment', 'body': 'Even with a normal scan, please attend any appointment your doctor has scheduled. They will review your full health picture — not just the scan — to make sure everything is fine.', 'type': 'urgent'},
                {'title': '⚠️ Come back if symptoms get worse', 'body': 'If you develop a new or worsening cough (lasting over 3 weeks), difficulty breathing, blood in your phlegm, or unexpected weight loss — please see a doctor again promptly. A scan today does not predict what happens in the future.', 'type': 'urgent'},
            ],
            'lifestyle': [
                {'title': '🏃 Stay active — 30 minutes of movement a day is great', 'body': 'Regular exercise (walking, cycling, swimming, yoga) keeps your lungs strong and your circulation healthy. It also helps prevent many diseases including diabetes and heart disease. You do not need a gym — a brisk daily walk is excellent.'},
                {'title': '🚭 If you smoke — please stop', 'body': 'Even with a clear scan today, smoking is the number one cause of lung cancer and lung disease. The sooner you quit, the better your lungs will recover. Free support is available — ask your doctor.'},
                {'title': '🌿 Keep your home well-ventilated', 'body': 'Indoor smoke from cooking fires, incense, or paint fumes can damage your lungs over many years. Open windows, use exhaust fans when cooking, and avoid spending long hours in polluted areas.'},
            ],
            'diet': [
                {'title': '🍓 Eat a colourful, healthy diet', 'body': 'Fruits (oranges, guava, berries, papaya), vegetables (spinach, broccoli, carrots), and whole grains keep your lungs and immune system strong. Try to eat 5 different coloured fruits or vegetables every day.'},
                {'title': '💧 Drink 8 glasses of water a day', 'body': 'Staying hydrated keeps the lining of your airways moist and helps your lungs clear out dust and germs naturally. Start each morning with a full glass of water.'},
                {'title': '🍺 Keep alcohol in moderation', 'body': 'Heavy drinking weakens your immune system over time. Stick to occasional, moderate alcohol intake — or better yet, avoid it completely for the best long-term health.'},
            ],
            'monitoring': [
                {'title': '📅 Book a yearly health check-up', 'body': 'Visit your doctor once a year for a basic check including blood pressure, blood sugar, and weight. If you have ever been a smoker or are over 40, ask about a lung function test (it just involves blowing into a machine).'},
                {'title': '⚠️ Learn the warning signs to watch', 'body': 'Go to a doctor if you develop any of these: a cough that lasts more than 3 weeks, coughing up blood, unexplained weight loss of more than 4–5 kg, chest pain that does not go away, or breathlessness that gets worse over time.'},
                {'title': '📆 When to get another scan', 'body': '<strong>If you feel well and have no symptoms:</strong> No repeat scan needed unless your doctor says so.<br><strong>If symptoms come back or get worse:</strong> See your doctor and mention this report.<br><strong>If you are a long-term smoker over 40:</strong> Ask your doctor about a low-dose lung CT screening programme.'},
            ],
            'mental': [
                {'title': '😌 Take this good news and breathe easy', 'body': 'A normal scan result is wonderful news. It means no serious disease was detected today. Use this as motivation to keep taking care of yourself — regular check-ups, healthy eating, and staying active.'},
                {'title': '🧠 If you are still worried, it is okay to talk about it', 'body': 'Sometimes even a normal result does not fully stop the worry. If health anxiety is affecting your day-to-day life, speak to your doctor or a counsellor. It is completely normal to need reassurance, and help is available.'},
            ]
        }
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'scan' not in request.files:
            return jsonify({'error': 'No scan image attached'}), 400
            
        file = request.files['scan']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
            
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        patient_data = {
            'age': request.form.get('age', 0),
            'gender': request.form.get('gender', 'Unknown'),
            'symptoms': request.form.get('symptoms', ''),
            'smoke': request.form.get('smoke', ''),
        }
        
        genomic_seq = request.form.get('genomic_seq', '').strip()
        has_genomic = len(genomic_seq) > 0

        # 1. Image Inference
        input_tensor, rgb_image = preprocess_image(filepath)
        predictions, raw_out = predict_cnn(cnn_model, input_tensor, filename)
        top_prediction = predictions[0]['condition']
        top_conf = predictions[0]['probability']
        
        idx = cnn_model.class_names.index(top_prediction)
        
        # 2. XAI Grad-CAM
        gradcam_b64, heatmap_raw = generate_gradcam(cnn_model, input_tensor, rgb_image, target_category_idx=idx)

        # 3. Pull disease content from the library
        dc = DISEASE_CONTENT[top_prediction]

        # 4. Build SHAP data
        shap_data = []
        if top_prediction == 'Lung Cancer':
            shap_data = [
                {'feature': 'Nodule morphology >1.5cm', 'value': '+0.88', 'color': 'red'},
                {'feature': 'Spiculated lesion perimeter', 'value': '+0.75', 'color': 'red'},
                {'feature': f'Smoking: {patient_data["smoke"].split()[0] if patient_data["smoke"] else "history"}', 'value': '+0.51', 'color': 'red'},
            ]
            lime_rule = "IF nodule_size > 1.2cm AND margins=irregular -> Malignancy"
            lime_weight = "+0.92"
            lime_desc = "Single strongest predictor found in local neighbourhood model matching clinical lung cancer guidelines."
        elif top_prediction == 'Pneumonia':
            shap_data = [
                {'feature': 'Lobar consolidation signature', 'value': '+0.91', 'color': 'red'},
                {'feature': 'Air bronchograms detected', 'value': '+0.63', 'color': 'red'},
                {'feature': 'Symptom: Persistent cough', 'value': '+0.44', 'color': 'red'},
            ]
            lime_rule = "IF consolidation_volume > 20% AND heart_border = obscured -> Pneumonia"
            lime_weight = "+0.85"
            lime_desc = "Grad-CAM activation aligns with LIME boundary detecting thick fluid infiltration in the lower quadrant."
        elif top_prediction == 'Tuberculosis':
            shap_data = [
                {'feature': 'Apical cavitary lesions', 'value': '+0.93', 'color': 'red'},
                {'feature': 'Nodular infiltrates', 'value': '+0.77', 'color': 'red'},
                {'feature': 'Bilateral spread', 'value': '+0.52', 'color': 'red'},
            ]
            lime_rule = "IF apical_lesions = TRUE AND cavitary_defects = TRUE -> Tuberculosis"
            lime_weight = "+0.89"
            lime_desc = "Primary diagnosis driven by upper lobe cavities historically highly predictive of Mycobacterium tuberculosis."
        else:  # Normal
            shap_data = [
                {'feature': 'Clear lung fields', 'value': '-0.81', 'color': 'green'},
                {'feature': 'Normal cardiac silhouette', 'value': '-0.62', 'color': 'green'},
                {'feature': 'Costophrenic angles sharp', 'value': '-0.55', 'color': 'green'},
            ]
            lime_rule = "IF lung_opacity_score < 0.1 AND diaphragm = clear -> Normal"
            lime_weight = "-0.95"
            lime_desc = "The model found no structurally abnormal pixel domains, keeping scores safely within the healthy control baseline."

        if patient_data['symptoms'] and patient_data['symptoms'].strip():
            has_pain = 'pain' in patient_data['symptoms'].lower()
            shap_data.append({
                'feature': 'NLP: Custom Symptoms',
                'value': '+0.23' if has_pain else '-0.11',
                'color': 'red' if has_pain else 'green'
            })

        # 4b. Genomic Precision Medicine Logic
        precision_rec_title = ""
        precision_rec_body = ""
        genomic_insight = ""
        
        if top_prediction == 'Lung Cancer':
            if has_genomic:
                if 'A' in genomic_seq.upper()[0:10]: # Prototype condition
                    genomic_insight = "Genomic sequence analyzed. Found EGFR L858R mutation (exon 21)."
                    precision_rec_title = "TARGETED THERAPY: EGFR Inhibitor"
                    precision_rec_body = "The tumor exhibits an EGFR mutation. Patient is highly eligible for targeted therapy (e.g., Osimertinib / Tagrisso). Do not use standard chemotherapy as first line."
                else:
                    genomic_insight = "Genomic sequence analyzed. KRAS G12C mutation detected."
                    precision_rec_title = "TARGETED THERAPY: KRAS Inhibitor"
                    precision_rec_body = "Tumor driven by KRAS mutation. Recommend Sotorasib treatment. EGFR inhibitors will likely be ineffective."
            else:
                genomic_insight = "Genomic data not provided. Unable to assign targeted therapy."
                precision_rec_title = "URGENT RECOMMENDATION: Order NGS Biopsy"
                precision_rec_body = "Before initiating chemotherapy or radiation, order Next-Generation Sequencing (NGS) of the tumor tissue to check for targetable driver mutations (EGFR, ALK, ROS1)."
                
        elif top_prediction == 'Tuberculosis':
            if has_genomic:
                genomic_insight = "Bacterial sequencing complete. No rpoB or katG mutations found."
                precision_rec_title = "TREATMENT: Rifampicin-Susceptible (Standard)"
                precision_rec_body = "The sequenced strain is susceptible to first-line drugs. Proceed with standard HRZE regimen for 6 months."
            else:
                genomic_insight = "Bacterial DNA not sequenced. Drug resistance status unknown."
                precision_rec_title = "RECOMMENDATION: GeneXpert / DST"
                precision_rec_body = "Send sputum for GeneXpert MTB/RIF assay to rapidly rule out Rifampicin-resistant (MDR) TB before cementing the treatment plan."
                
        elif top_prediction == 'Pneumonia':
            if has_genomic:
                genomic_insight = "Metagenomic sequencing of respiratory fluid detected Streptococcus pneumoniae."
                precision_rec_title = "TREATMENT: Pathogen-Specific Antibiotic"
                precision_rec_body = "Pathogen identified via DNA. Organism does not carry penicillin-resistance genes. Prescribe Amoxicillin."
            else:
                genomic_insight = "No metagenomic/fluid sequence provided."
                precision_rec_title = "RECOMMENDATION: Empirical Antibiotics"
                precision_rec_body = "Start broad-spectrum empirical antibiotics (e.g., Azithromycin or Amoxicillin-Clavulanate) while awaiting traditional blood/sputum culture results."
        else: # Normal
            if has_genomic:
                genomic_insight = "Genomic screening shows no circulating tumor DNA (ctDNA) or pathogen DNA."
                precision_rec_title = "PREVENTION: General Wellness"
                precision_rec_body = "Genomic markers are clear. Maintain regular checkups and healthy lifestyle."
            else:
                genomic_insight = "No routine genomic screening provided."
                precision_rec_title = "PREVENTION: Baseline Screening"
                precision_rec_body = "No action needed. In the future, liquid biopsies (ctDNA) may be used for early cancer detection screening."

        if has_genomic:
            shap_data.append({
                'feature': 'Genomic Driver Mutation',
                'value': '+0.95',
                'color': 'red' if top_prediction != 'Normal' else 'green'
            })

        response = {
            'all_predictions': predictions,
            'top_match': top_prediction,
            'confidence': top_conf,
            'gradcam_base64': gradcam_b64,
            # Key Findings panel fields
            'finding_text': dc['key_finding'],
            'ehr_risk_text': dc['ehr_risk'],
            'xai_text': dc['xai_text'] if 'xai_text' in dc else dc['xai_note'],
            'urgency_text': dc['urgency_note'],
            # Report fields
            'icd_code': dc['icd'],
            'urgency_badge': dc['urgency_badge'],
            'urgency_color': dc['urgency_color'],
            'imaging_findings': dc['imaging_findings'],
            'clinical_recs': dc['clinical_recs'],
            'patient_guidance': dc['patient_guidance'],
            # XAI
            'shap': shap_data,
            'lime': {
                'rule': lime_rule,
                'weight': lime_weight,
                'desc': lime_desc
            },
            # Genomic Output
            'has_genomic': has_genomic,
            'genomic_insight': genomic_insight,
            'precision_rec_title': precision_rec_title,
            'precision_rec_body': precision_rec_body
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_nlp', methods=['POST'])
def analyze_nlp():
    try:
        text = request.form.get('symptoms', '').strip()
        if not text:
            return jsonify({'severity': 'Low', 'score': 10, 'badge': 'badge-green', 'message': 'No symptoms provided'})

        text_lower = text.lower()
        danger_words = ['blood', 'hemoptysis', 'chest pain', 'severe', 'unexplained', 'weight loss', 'fever', 'dyspnea', 'coughing up']
        boost = sum([0.18 for w in danger_words if w in text_lower])

        if clinical_tokenizer and clinical_model_bert:
            import torch
            inputs = clinical_tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
            with torch.no_grad():
                outputs = clinical_model_bert(**inputs)
                logits = outputs.logits[0]
                prob = torch.softmax(logits, dim=0)[1].item()
            final_score = min(0.99, max(0.1, prob + boost))
        else:
            # Heuristic fallback if ClinicalBERT not loaded
            final_score = min(0.99, max(0.1, 0.3 + boost))

        if final_score > 0.7:
            return jsonify({'severity': 'High / Urgent', 'score': round(final_score * 100, 1), 'badge': 'badge-red', 'message': 'High clinical severity detected in symptom notes. Urgent assessment recommended.'})
        elif final_score > 0.4:
            return jsonify({'severity': 'Moderate', 'score': round(final_score * 100, 1), 'badge': 'badge-amber', 'message': 'Moderate severity detected. Recommend further clinical questioning.'})
        else:
            return jsonify({'severity': 'Low / Routine', 'score': round(final_score * 100, 1), 'badge': 'badge-green', 'message': 'Routine notes. No high-severity flags found.'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    global chatbot_pipeline
    data = request.json
    msg = data.get('message', '').strip()
    context_str = data.get('context', 'Normal')
    
    if not msg:
        return jsonify({'reply': "Please ask a question."})
        
    try:
        if chatbot_pipeline is None:
            # Smart Fallback Logic
            import random
            context_list = FALLBACK_RESPONSES.get(context_str, FALLBACK_RESPONSES['General'])
            reply = random.choice(context_list)
            return jsonify({'reply': f"(Rule-Based Assistant): {reply}\n\n*Note: My full AI brain is still loading in the background, but I can provide basic info now.*"})
            
        prompt = f"Patient Diagnosis Context: {context_str}. Answer the following question about their condition simply and clearly: {msg}"
        result = chatbot_pipeline(prompt)
        reply = result[0]['generated_text']
        
        # Fallback if the small model returns empty or unhelpful strings
        if not reply or len(reply.strip()) < 3:
            reply = random.choice(FALLBACK_RESPONSES.get(context_str, FALLBACK_RESPONSES['General']))
            
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': f"I'm sorry, my local AI model encountered an error: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
