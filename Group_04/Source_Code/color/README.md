## iCare - Color Blindness Simulator

A desktop GUI tool to simulate how images appear to people with different types of color vision deficiencies (Protanopia, Deuteranopia, Tritanopia). Includes severity control, side-by-side preview, and save/export.

### Features
- Load any image (`PNG/JPG/BMP/TIFF/WEBP`)
- Simulate: Protanopia, Deuteranopia, Tritanopia
- Severity slider (0.0 original → 1.0 full simulation)
- Side-by-side preview
- Save simulated image

### Install

Using Python 3.9+:

```bash
pip install -r requirements.txt
```

### Run

```bash
python icare_colorblind_gui.py
```

### Notes on Accuracy

This app uses sRGB linearization and 3×3 matrices inspired by published research (Machado et al.) for fast, approximate simulations. For research-grade accuracy, consider full LMS cone-space models and spectral conversions.

---

## Web App (HTML/CSS/JS)

Open `web/index.html` in a modern browser (Chrome/Edge/Firefox/Safari). No build step required.

### Web Features
- Client-side processing with Canvas
- Same simulation types and severity control
- Download simulated image as PNG

Note: Do not run `web/app.js` with Node; it expects the browser DOM (e.g., `document`).

---

## AI-driven Color Blindness Detection (Ishihara)

This project includes a non-rule-based pipeline that trains a small classifier on (plate, response) pairs and runs inference fully in the browser. Unlike rule tables that hardcode expected answers per plate, this learns patterns across plates and supports probabilistic outputs and severity proxy.

### Steps
1) Build manifest from your dataset and optionally copy a web subset:
```bash
python scripts/build_manifest.py "C:/Users/Rahul/Downloads/ishihara" artifacts --copy-web web --per-type 6
```
This writes `artifacts/manifest.json` and `web/plates_manifest.json` and copies images to `web/plates/`.

2) Train a simple multinomial logistic regression on synthesized responses (replace later with real user data):
```bash
python scripts/train_response_model.py web/plates_manifest.json web/weights.json
```

3) Open the test UI:
```
web/test.html
```
Load plates, start test, enter responses, and click Predict. The model outputs class probabilities and a severity proxy.

### Why this differs from rule-based detectors
- Learns from data: produces probabilities rather than binary pass/fail.
- Robust to noise/typos: multiple responses aggregate into a distribution over classes.
- Extensible: can incorporate additional features (reaction time, confidence) without re-authoring rules.
- Deployable on-device: weights are small JSON for private, offline inference.




