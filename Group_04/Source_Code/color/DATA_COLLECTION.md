# Data Collection and Model Retraining Guide

This guide explains how to collect real user data and retrain the model to fix prediction accuracy issues.

## The Problem

The current model is trained on synthetic data, which causes:
- Inconsistent predictions
- Underestimation of Normal vision (spreads probability across Protan/Deut/Trit)
- Poor accuracy because the model doesn't learn true mappings

## The Solution

Collect real user responses and retrain the model with actual data.

## Step 1: Collect Real Responses

1. **Run the test**: Open `web/test.html` in your browser
2. **Load plates**: Click "Load Plates (manifest)"
3. **Start test**: Click "Start Test"
4. **Complete test**: Go through all plates, entering the numbers you see
5. **Export data**: Click "Export Responses" to download `responses.csv`

The exported file will have columns: `plate_id,type_idx,answer`

## Step 2: Create User Labels (Optional but Recommended)

Create a `labels.csv` file with user ground truth labels:

```csv
session_id,user_label
session_001,Normal
session_002,Normal
session_003,Protanopia
session_004,Deuteranopia
session_005,Tritanopia
```

**Note**: If you only have Normal users now, that's fine - start there!

## Step 3: Add Ground Truth Answers (Optional but Best)

Create a `ground_truth.csv` file with expected correct answers:

```csv
plate_id,expected_normal_answer
1,12
2,8
3,6
4,29
5,57
```

This enables the model to learn correctness features, dramatically boosting Normal vs non-Normal separation.

## Step 4: Retrain the Model

### Option A: Using the helper script
```bash
# Create sample files
python scripts/collect_data.py init-labels
python scripts/collect_data.py init-ground

# Edit the generated files with your data, then:
python scripts/collect_data.py train
```

### Option B: Direct training
```bash
# With just responses
python scripts/train_response_model.py web/plates_manifest.json web/weights.json responses.csv

# With responses and labels
python scripts/train_response_model.py web/plates_manifest.json web/weights.json responses.csv labels.csv

# With responses, labels, and ground truth
python scripts/train_response_model.py web/plates_manifest.json web/weights.json responses.csv labels.csv ground_truth.csv
```

## Step 5: Test the New Model

1. Refresh `web/test.html` in your browser
2. The new `web/weights.json` will be automatically loaded
3. Run the test again - you should see Normal ~90%+ when all answers are correct

## Why This Fixes the Problem

**Before**: The synthetic training doesn't know which answers are "correct" - it only sees fabricated patterns. Without real labels or plate ground truth, Normal isn't explicitly favored.

**After**: With real data and ground truth, the model learns:
- Per-plate correctness features
- Answer patterns that distinguish Normal from colorblind users
- Strong Normal vs non-Normal separation

## File Structure

```
iCare/
├── responses.csv          # Exported from test.html
├── labels.csv            # User ground truth (optional)
├── ground_truth.csv      # Expected answers (optional)
├── web/weights.json      # Retrained model weights
└── scripts/
    ├── train_response_model.py  # Enhanced training script
    └── collect_data.py          # Helper script
```

## Tips for Better Results

1. **Start with Normal users**: Even if you only have Normal vision users, this helps establish the baseline
2. **Use ground truth**: If you know the correct answers for plates, include them
3. **Collect diverse data**: Try to get responses from users with different color vision types
4. **Validate results**: Test the retrained model with known users to verify accuracy

## Troubleshooting

- **No responses.csv**: Make sure to complete the test and click "Export Responses"
- **Training fails**: Check that CSV files have the correct column names
- **Still inaccurate**: Ensure you have enough diverse training data (aim for 20+ responses per user type)





