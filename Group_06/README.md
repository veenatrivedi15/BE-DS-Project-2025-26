# 🩺 Diagnox — AI-Powered Medical Diagnostics Platform

## 👥 Group Members

| Name          |
|---------------|
| Darshan Korde |
| Snehal Pawar  |
| Yash Nalawade |
| Gauri Salvi   |

---

## 📌 Project Description

Diagnox is a multimodal AI diagnostic platform that analyzes **chest X-rays** combined with **patient EHR data** and optional **genomic sequences** to predict lung conditions — including **Lung Cancer, Tuberculosis, Pneumonia, and Normal** — with clinical-grade explainability using Grad-CAM, SHAP, and LIME.

**Key Features:**
- 📷 **CNN Image Analysis** — DenseNet-based chest X-ray classifier
- 🧬 **Genomic Precision Medicine** — targeted therapy recommendations from genomic input
- 📝 **ClinicalBERT NLP** — symptom severity scoring from free-text clinical notes
- 🔥 **Grad-CAM XAI** — visual heatmaps showing exactly where the AI focused
- 📊 **SHAP & LIME** — feature-level explainability for each prediction
- 💬 **AI Chatbot** — flan-t5-small model with smart rule-based fallback
- 📄 **Clinical Reports** — full patient-facing reports with lifestyle & monitoring guidance

---

## 🚀 How to Run

### Prerequisites
- Python 3.9+
- (Optional) NVIDIA GPU with CUDA for faster inference

### Step 1 — Navigate to the Project & Activate Virtual Environment

```bash
cd Source_Code
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
```

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Run the Flask Server

```bash
python app.py
```

> ⏳ On first launch, the CNN and ClinicalBERT models load (~30–60 seconds). The chatbot loads silently in the background.

### Step 4 — Open in Browser

```
http://localhost:5000
```

---

## 📁 Project Structure

```
Source_Code/
├── app.py                  # Main Flask application & API routes
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Frontend UI (Diagnox platform)
├── models/
│   ├── cnn_model.py        # DenseNet CNN for X-ray classification
│   ├── nlp_model.py        # ClinicalBERT for symptom NLP
│   ├── ehr_model.py        # EHR tabular data model
│   ├── genomic_model.py    # Genomic sequence processing
│   └── multimodal_model.py # Multimodal fusion architecture
├── utils/
│   └── xai_utils.py        # Grad-CAM explainability
├── train_cnn.py            # CNN training script
├── visualize_loss.py       # Loss curve visualization
└── ProjectMajor.ipynb      # Research notebook
```

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `Flask` | Web framework |
| `torch` / `torchvision` | Deep learning (CNN inference) |
| `transformers` | ClinicalBERT + flan-t5-small |
| `opencv-python` | Image preprocessing |
| `grad-cam` | Grad-CAM XAI heatmaps |
| `scikit-learn` | Evaluation metrics |

---

## ⚕️ Disclaimer

Diagnox is a **research prototype** intended for academic demonstration. It is **not** a certified medical device and should not be used for clinical diagnosis without review by a qualified healthcare professional.
