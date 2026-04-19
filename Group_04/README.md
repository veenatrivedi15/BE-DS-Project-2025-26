# I-Care: A Convolutional model for automated eye screening

## Group Members
- Annsh Yadav (22107012)
- Diya Thakkar (22107040)
- Soham Shigvan (22107001)
- Rahul Zore (22107008)

I-Care is a Flask-based eye health screening web application with multiple AI-assisted modules:

- Eye disease image classification
- Color-vision testing and simulation
- Eye fatigue risk scoring from image + questionnaire
- AI chat recommendations with clinic lookup
- User authentication and profile management

This README reflects the current code in this repository.

## Current Feature Status

### 1. Eye Disease Detection (Integrated in main app)

- Route: `/detection` (login required)
- Model file expected at: `static/models/eye_disease_finalV2.keras`
- Class labels expected at: `static/models/class_labels_V2.json`
- Predicted classes:
    - Cataract
    - Diabetic Retinopathy
    - Glaucoma
    - Normal
- Result page: `/detection/result`

### 2. Color Blindness Test + Simulator (Integrated via blueprint)

- Blueprint prefix: `/color`
- UI routes:
    - `/color/ishihara`
    - `/color/simulator`
- API routes:
    - `/color/new-session`
    - `/color/append-responses`
    - `/color/append-result`
    - `/color/predict-session`
    - `/color/next-plate`
    - `/color/simulate`
- Session prediction targets:
    - Normal
    - Protanopia
    - Deuteranopia
    - Tritanopia

### 3. Eye Fatigue Analysis (Integrated in main app)

- Route: `/fatigue` (login required)
- Prediction API: `/fatigue/predict` (login required)
- Uses:
    - Local redness model at `static/models/eye_redness_model.keras`
    - Roboflow inference API for fatigue/dryness signals
    - Questionnaire-based risk adjustment

### 4. Recommendations Chat + Nearby Clinics (Integrated in main app)

- Route: `/recommendations` (login required)
- Chat API: `/chat`
    - Uses Groq (`llama-3.3-70b-versatile`)
    - Optional translation with `deep-translator`
- Clinic lookup API: `/search_clinics`
    - Uses SerpApi when configured
    - Falls back to OpenStreetMap Overpass

### 5. Authentication and Profile (Integrated in main app)

- Signup: `/signup`
- Login: `/login`
- Logout: `/logout`
- Profile update: `/profile`
- Password change: `/profile/change-password`
- Storage: SQLite database (`icare.db` by default)

## Tech Stack Actually Used

- Backend: Flask
- Templating: Jinja2
- Frontend: HTML, CSS, JavaScript, Tailwind (CDN), Bootstrap Icons
- ML/DL: TensorFlow/Keras, scikit-learn, NumPy, Pandas
- Image processing: Pillow
- External AI/Services: Groq API, Roboflow Inference SDK, SerpApi, Overpass
- Translation: deep-translator
- Database: SQLite

## Repository Layout (Important Parts)

```
I-Care/
├── app.py                     # Main Flask app used for web platform
├── color_feature.py           # Color blueprint mounted at /color
├── requirements.txt
├── templates/                 # Main app templates
├── static/                    # Main app static assets + model files
│   └── models/
│       ├── eye_disease_finalV2.keras
│       ├── class_labels_V2.json
│       └── eye_redness_model.keras
├── color/                     # Color data/artifacts/training scripts
├── fatigue/                   # Standalone fatigue prototype app
├── recommend/                 # Standalone recommendation prototype app
└── exercise/                  # Standalone exercise tracking app
```

## Setup

### 1. Python

Recommended: Python 3.12 (current local environment is 3.12.10).

### 2. Create and activate virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` (optional but recommended)

Example:

```env
GROQ_API_KEY=your_groq_api_key
SERPAPI_API_KEY=your_serpapi_key
SQLITE_DB_PATH=icare.db
PORT=5000
```

Notes:

- `GROQ_API_KEY` is needed for chatbot responses.
- `SERPAPI_API_KEY` is optional. If missing, clinic search uses Overpass fallback.
- If `SQLITE_DB_PATH` is not set, the app uses `icare.db` in project root.

### 5. Ensure model files exist

Required for AI endpoints:

- `static/models/eye_disease_finalV2.keras`
- `static/models/class_labels_V2.json`
- `static/models/eye_redness_model.keras`

### 6. Run the main app

```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Data Files Generated at Runtime

- SQLite DB:
    - `icare.db` (or `SQLITE_DB_PATH` value)
- Uploaded files:
    - `static/uploads/`
    - `static/uploads/profile/`
- Color module logs:
    - `color/responses.csv`
    - `color/results.csv`
    - generated images in `static/color/plates/generated/` and `static/color/simulated/`

## About Standalone Sub-Apps

The following directories contain separate/legacy prototype apps and scripts, not routes directly mounted in `app.py`:

- `exercise/`
- `fatigue/`
- `recommend/`

The main integrated web app entry point is `app.py`.

## Medical Disclaimer

I-Care provides AI-assisted screening support and wellness guidance. It is not a medical diagnosis tool and does not replace professional eye examination by a licensed specialist.
