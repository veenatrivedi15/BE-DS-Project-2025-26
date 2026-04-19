"""Train a calibrated session-level logistic regression model with engineered features.

Usage:
  python -m color.scripts.train_session_calibrated color/artifacts/features.csv --label-col label

This script expects a CSV with at least columns:
  session_id (optional), label, n_responses, type_1_acc, type_2_acc, type_3_acc (optional), answer_hist_*, ...

It will:
  1. Load & clean data (drop unlabeled, enforce min responses)
  2. Re-normalize histogram columns answer_hist_*
  3. Engineer summary stats (entropy, max, second, gap, unique count)
  4. Train base LogisticRegression (class_weight balanced)
  5. Calibrate probabilities (isotonic if enough samples else sigmoid/Platt)
  6. Save calibrated model + metadata bundle

Outputs:
  color/artifacts/session_calibrated_model.pkl
  color/artifacts/session_calibrated_model.json (metadata)
"""
from __future__ import annotations
import argparse, json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, brier_score_loss, f1_score

CLASSES = ["Normal","Protanopia","Deuteranopia","Tritanopia"]
MIN_RESP = 8
ART_DIR = Path("color")/"artifacts"
ART_DIR.mkdir(parents=True, exist_ok=True)


def load_and_engineer(path: Path, label_col: str):
    df = pd.read_csv(path)
    if label_col not in df.columns:
        raise SystemExit(f"Missing label column {label_col}")
    df[label_col] = df[label_col].astype(str).str.strip()
    df = df[df[label_col].isin(CLASSES)].copy()
    if "n_responses" in df.columns:
        df = df[df["n_responses"] >= MIN_RESP]
    # Identify histogram cols
    hist_cols = [c for c in df.columns if c.startswith("answer_hist_")]
    # Normalize histogram
    if hist_cols:
        hist = df[hist_cols].fillna(0.0).clip(lower=0)
        sums = hist.sum(axis=1).replace(0,1)
        hist = hist.div(sums, axis=0)
        df[hist_cols] = hist
        # Summary features
        hist_values = hist.values
        sorted_desc = np.sort(hist_values, axis=1)[:, ::-1]
        df['hist_entropy'] = -(hist.replace(0, np.nan)*np.log(hist.replace(0,np.nan))).sum(axis=1).fillna(0)
        df['hist_max'] = sorted_desc[:,0]
        df['hist_second'] = np.where(sorted_desc.shape[1]>1, sorted_desc[:,1], 0)
        df['hist_gap'] = df['hist_max'] - df['hist_second']
        df['unique_answers'] = (hist > 0).sum(axis=1)
    # Keep base columns if present
    base_cols = [c for c in ["n_responses","type_1_acc","type_2_acc","type_3_acc"] if c in df.columns]
    feature_cols = base_cols + hist_cols + [c for c in ['hist_entropy','hist_max','hist_second','hist_gap','unique_answers'] if c in df.columns]
    X = df[feature_cols].fillna(0.0)
    y = pd.Categorical(df[label_col], categories=CLASSES).codes
    return X, y, feature_cols, df


def train_calibrated(X, y):
    # Stratified split
    Xtr, Xval, ytr, yval = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    if len(set(ytr)) < 2:
        raise SystemExit("Not enough classes to train (need at least 2)")
    base = LogisticRegression(max_iter=1500, multi_class='multinomial', solver='lbfgs', class_weight='balanced', random_state=42)
    base.fit(Xtr, ytr)
    # Choose calibration method
    method = 'isotonic' if len(Xtr) > 200 else 'sigmoid'
    calib = CalibratedClassifierCV(base, method=method, cv='prefit')
    calib.fit(Xval, yval)
    proba = calib.predict_proba(Xval)
    # Brier macro
    brier_macro = float(np.mean([
        brier_score_loss((yval==i).astype(int), proba[:,i]) for i in range(proba.shape[1])
    ]))
    f1_macro = float(f1_score(yval, calib.predict(Xval), average='macro'))
    report = classification_report(yval, calib.predict(Xval), target_names=CLASSES, output_dict=True)
    return calib, method, brier_macro, f1_macro, report


def save_bundle(model, feature_cols, method, brier_macro, f1_macro, report, feature_path: Path):
    bundle = {
        'model': model,
        'feature_columns': feature_cols,
        'classes': CLASSES,
        'calibration_method': method,
        'brier_macro': brier_macro,
        'f1_macro': f1_macro
    }
    pkl_path = ART_DIR/"session_calibrated_model.pkl"
    with pkl_path.open('wb') as f:
        pickle.dump(bundle, f)
    meta = {
        'feature_columns': feature_cols,
        'classes': CLASSES,
        'calibration_method': method,
        'brier_macro': brier_macro,
        'f1_macro': f1_macro,
        'classification_report': report,
        'source_features_csv': str(feature_path)
    }
    (ART_DIR/"session_calibrated_model.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f"Saved calibrated model to {pkl_path}")


def parse_args():
    ap = argparse.ArgumentParser("Train calibrated session model")
    ap.add_argument('features_csv', type=Path)
    ap.add_argument('--label-col', default='label')
    ap.add_argument('--min-responses', type=int, default=MIN_RESP)
    return ap.parse_args()


def main():
    args = parse_args()
    global MIN_RESP
    MIN_RESP = args.min_responses
    X, y, feat_cols, df = load_and_engineer(args.features_csv, args.label_col)
    if len(df) < 10:
        print(f"Warning: very small dataset ({len(df)} rows). Probabilities may be unstable.")
    model, method, brier_macro, f1_macro, report = train_calibrated(X, y)
    save_bundle(model, feat_cols, method, brier_macro, f1_macro, report, args.features_csv)

if __name__ == '__main__':
    main()
