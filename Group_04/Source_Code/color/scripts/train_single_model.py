"""Train a single deterministic multinomial Logistic Regression model for color vision classification.

Usage:
  python -m color.scripts.train_single_model color/responses_labeled.csv --label-col user_label --aggregate

Expected columns in responses CSV:
  session_id, numeral, type_idx, answer, <label-col>
Labels must be one of: Normal, Protanopia, Deuteranopia, Tritanopia

Artifacts written:
  color/artifacts/single_logreg_model.pkl
  color/artifacts/single_logreg_model.json (metadata)
  color/artifacts/single_logreg_model_meta.json (dataset snapshot)
"""
from __future__ import annotations
import argparse, json, pickle, os, random
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

# Deterministic seeds & threading controls
SEED = 42
os.environ["PYTHONHASHSEED"] = str(SEED)
# Limit threads for determinism (optional)
for var in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"]:
    os.environ.setdefault(var, "1")
random.seed(SEED)
np.random.seed(SEED)

ART_DIR = Path("color") / "artifacts"
ART_DIR.mkdir(parents=True, exist_ok=True)
CLASSES = ["Normal","Protanopia","Deuteranopia","Tritanopia"]


def load_df(path: Path, label_col: str, require_session: bool = True) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Responses file not found: {path}")
    df = pd.read_csv(path)
    needed = {"numeral","type_idx","answer",label_col}
    if require_session:
        needed.add("session_id")
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {missing}")
    # Basic cleaning
    for c in ["numeral","type_idx","answer"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(-1).astype(int)
    df[label_col] = df[label_col].astype(str).str.strip()
    before = len(df)
    df = df[df[label_col].isin(CLASSES)]
    if len(df) < before:
        print(f"Filtered {before-len(df)} rows with unknown labels")
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    feat = pd.DataFrame(index=df.index)
    feat["numeral"] = df["numeral"].clip(lower=0)
    feat["answer"] = df["answer"].clip(lower=0)
    feat["type_idx"] = df["type_idx"].clip(lower=0)
    feat["is_correct_proxy"] = (df["answer"] == df["numeral"]).astype(int)  # proxy until true ground truth
    feat["abs_err"] = (df["answer"] - df["numeral"]).abs()
    feat["err_ge10"] = (feat["abs_err"] >= 10).astype(int)
    feat["mod10_num"] = df["numeral"] % 10
    feat["mod10_ans"] = df["answer"] % 10
    for t in (1,2,3):
        feat[f"type_{t}"] = (df["type_idx"] == t).astype(int)
    return feat.fillna(0)


def aggregate_session_level(feat: pd.DataFrame, labels: np.ndarray, sessions: pd.Series):
    rows = []
    y_sess: List[int] = []
    # Helper for entropy
    def _entropy(p):
        p = np.asarray(p, dtype=float)
        p = p[p > 0]
        if p.size == 0:
            return 0.0
        return float(-(p * np.log2(p)).sum())

    for sid, sub in feat.groupby(sessions):
        row = {"n_responses": len(sub)}
        # Means for all columns
        for c in feat.columns:
            row[f"mean_{c}"] = float(sub[c].mean())
        # Sums (selected)
        for c in ["is_correct_proxy","abs_err","err_ge10"]:
            row[f"sum_{c}"] = float(sub[c].sum())
        # Per-type counts and accuracies
        for t in (1, 2, 3):
            mask = (sub["type_"+str(t)] == 1)
            ct = int(mask.sum())
            row[f"count_type{t}"] = ct
            if ct > 0:
                row[f"acc_type{t}"] = float(sub.loc[mask, "is_correct_proxy"].mean())
            else:
                row[f"acc_type{t}"] = 0.0
        # Overall stats
        row["overall_acc"] = float(sub["is_correct_proxy"].mean())
        row["err_mean"] = float(sub["abs_err"].mean())
        row["err_big_rate"] = float(sub["err_ge10"].mean())
        # Answer distribution stats
        vc = sub["answer"].value_counts(normalize=True, dropna=False).sort_values(ascending=False).values
        top = float(vc[0]) if vc.size > 0 else 0.0
        second = float(vc[1]) if vc.size > 1 else 0.0
        row["ans_hist_entropy"] = _entropy(vc)
        row["ans_hist_max"] = top
        row["ans_hist_second"] = second
        row["ans_hist_gap"] = top - second
        row["ans_hist_unique"] = int(sub["answer"].nunique(dropna=False))
        rows.append(row)
        # Majority label for the session
        y_sess.append(int(np.bincount(labels[sub.index]).argmax()))
    agg = pd.DataFrame(rows).fillna(0)
    return agg, np.array(y_sess), list(agg.columns)


def _fit_temperature(logits: np.ndarray, y_true: np.ndarray) -> float:
    """Optimize temperature T for temperature scaling on a held-out set.

    We minimize NLL w.r.t T>0. Simple 1D optimization via grid + refinement.
    logits: shape (n_samples, n_classes) before softmax.
    Returns optimal temperature (float).
    """
    # Initial coarse grid
    temps = np.linspace(0.5, 5.0, 30)
    def nll(T):
        z = logits / T
        z = z - z.max(axis=1, keepdims=True)
        exp_z = np.exp(z)
        probs = exp_z / exp_z.sum(axis=1, keepdims=True)
        # avoid log(0)
        eps = 1e-12
        ll = -np.log(probs[np.arange(len(y_true)), y_true] + eps)
        return ll.mean()
    losses = [nll(t) for t in temps]
    best_idx = int(np.argmin(losses))
    best_T = float(temps[best_idx])
    # Local refinement using small perturbations
    for _ in range(10):
        candidates = np.clip([best_T*0.85, best_T*0.93, best_T, best_T*1.07, best_T*1.15], 0.05, 10.0)
        cand_losses = [nll(c) for c in candidates]
        best_T = float(candidates[int(np.argmin(cand_losses))])
    return max(0.05, min(best_T, 10.0))


def train_single(X, y, calibrate: bool = True):
    pipe = Pipeline([
        ("scaler", StandardScaler(with_mean=False)),
        ("clf", LogisticRegression(
            multi_class="multinomial",
            solver="lbfgs",
            max_iter=1500,
            class_weight="balanced",
            random_state=SEED
        ))
    ])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="f1_weighted", n_jobs=-1)
    print(f"CV weighted F1: mean={scores.mean():.4f} std={scores.std():.4f}")
    # Split for calibration (stratified)
    if calibrate:
        X_train, X_cal, y_train, y_cal = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
        pipe.fit(X_train, y_train)
        # logits: use decision_function for multinomial gives shape (n_samples, n_classes)
        if hasattr(pipe.named_steps['clf'], 'decision_function'):
            logits = pipe.decision_function(X_cal)
            T = _fit_temperature(logits, y_cal)
            print(f"Calibrated temperature T={T:.3f}")
        else:
            T = 1.0
    else:
        pipe.fit(X, y)
        T = 1.0
    return pipe, scores, T


def save_artifacts(model, feature_order, scores, rows_used, y, temperature: float):
    bundle = {
        "model": model,
        "feature_order": feature_order,
        "classes": CLASSES,
        "cv_f1_mean": float(scores.mean()),
        "cv_f1_std": float(scores.std()),
        "seed": SEED,
        "temperature": float(temperature),
        "calibration": {
            "method": "temperature_scaling",
            "temperature": float(temperature)
        }
    }
    pkl_path = ART_DIR / "single_logreg_model.pkl"
    with pkl_path.open("wb") as f:
        pickle.dump(bundle, f)
    meta = {
        "rows": rows_used,
        "class_counts": {c:int(n) for c,n in zip(CLASSES, np.bincount(y, minlength=len(CLASSES)))},
        "cv_f1_mean": float(scores.mean()),
        "cv_f1_std": float(scores.std()),
        "feature_count": len(feature_order),
        "seed": SEED,
        "temperature": float(temperature)
    }
    (ART_DIR/"single_logreg_model.json").write_text(json.dumps({k:v for k,v in bundle.items() if k!="model"}, indent=2), encoding="utf-8")
    (ART_DIR/"single_logreg_model_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved artifacts: {pkl_path}")


def parse_args():
    ap = argparse.ArgumentParser("Train single logistic regression model")
    ap.add_argument("responses", type=Path, help="Path to labeled responses CSV")
    ap.add_argument("--label-col", default="user_label", help="Name of label column")
    ap.add_argument("--aggregate", action="store_true", help="Aggregate to session-level features")
    return ap.parse_args()


def main():
    args = parse_args()
    df = load_df(args.responses, args.label_col)
    y = pd.Categorical(df[args.label_col], categories=CLASSES).codes
    feat = build_features(df)
    if args.aggregate:
        print("Aggregating to session level...")
        feat, y, feature_order = aggregate_session_level(feat, y, df["session_id"])
    else:
        feature_order = list(feat.columns)
    model, scores, T = train_single(feat, y, calibrate=True)
    save_artifacts(model, feature_order, scores, feat.shape[0], y, T)
    print("Done.")

if __name__ == "__main__":
    main()
