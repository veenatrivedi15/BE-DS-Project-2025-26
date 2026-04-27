from __future__ import annotations

import json
import math
import random
import colorsys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, TYPE_CHECKING, Optional, Dict, Any
if TYPE_CHECKING:  # pragma: no cover
    from PIL import Image  # type: ignore

from flask import Blueprint, render_template, request, jsonify, session
import uuid
import io

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy should exist, fallback not implemented
    np = None  # Will raise at runtime if used

color_bp = Blueprint(
    'color_feature', __name__,
    url_prefix='/color'
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'color'
RESPONSES_CSV = DATA_DIR / 'responses.csv'
RESULTS_CSV = DATA_DIR / 'results.csv'
GENERATED_DIR = Path('static') / 'color' / 'plates' / 'generated'
SIMULATED_DIR = Path('static') / 'color' / 'simulated'
MODEL_ARTIFACT = BASE_DIR / 'color' / 'artifacts' / 'session_model.pkl'
FEATURES_CSV = BASE_DIR / 'color' / 'artifacts' / 'features.csv'
LOGREG_MODEL = BASE_DIR / 'color' / 'artifacts' / 'logreg_model.pkl'

# In-memory singleton style caches (lazy loaded)
_SESSION_MODEL: Optional[Any] = None
_FEATURE_COLUMNS: Optional[List[str]] = None  # Ordered feature names used during training
_LABEL_MAP: Optional[Dict[int, str]] = None  # index -> label string
_LOGREG_OBJ: Optional[Dict[str, Any]] = None  # contains model, feature_order, classes


def _ensure_headers():
    RESPONSES_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not RESPONSES_CSV.exists() or RESPONSES_CSV.stat().st_size == 0:
        RESPONSES_CSV.write_text('numeral,type_idx,answer,timestamp,session_id\n', encoding='utf-8')
    if not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0:
        RESULTS_CSV.write_text('session_id,timestamp,total_questions,label,probs_json\n', encoding='utf-8')


def _new_color_session_id() -> str:
    sid = uuid.uuid4().hex
    session['color_session_id'] = sid
    return sid


def _get_color_session_id() -> str:
    sid = session.get('color_session_id')
    if not sid:
        sid = _new_color_session_id()
    return sid


@color_bp.route('/simulator')
def simulator():
    return render_template('feature_color_simulator.html')


@color_bp.route('/ishihara')
def ishihara():
    # New session for each visit to the test page to simplify per-attempt logging
    _new_color_session_id()
    return render_template('feature_colorblind.html')


@color_bp.post('/append-responses')
def append_responses():
    _ensure_headers()
    data = request.get_json(silent=True) or {}
    rows: List[str] = data.get('rows') or []
    if not isinstance(rows, list):
        return jsonify({'error': 'rows must be list'}), 400
    session_id = str(data.get('session_id') or _get_color_session_id())
    ts = datetime.now(timezone.utc).isoformat()
    appended = 0
    with RESPONSES_CSV.open('a', encoding='utf-8') as f:
        for r in rows:
            parts = [p.strip() for p in str(r).split(',')]
            numeral = parts[0] if len(parts) > 0 else ''
            type_idx = parts[1] if len(parts) > 1 else ''
            answer = parts[2] if len(parts) > 2 else ''
            f.write(f"{numeral},{type_idx},{answer},{ts},{session_id}\n")
            appended += 1
    return jsonify({'status': 'ok', 'count': appended})


@color_bp.post('/append-result')
def append_result():
    _ensure_headers()
    data = request.get_json(silent=True) or {}
    session_id = str(data.get('session_id') or _get_color_session_id())
    label = str(data.get('label') or '')
    probs = data.get('probs') or []
    total = int(data.get('total') or 0)
    ts = datetime.now(timezone.utc).isoformat()
    with RESULTS_CSV.open('a', encoding='utf-8') as f:
        f.write(f"{session_id},{ts},{total},{label},{json.dumps(probs)}\n")
    return jsonify({'status': 'ok'})


@color_bp.post('/new-session')
def new_color_session():
    """Start/reset a new color test session. Returns the fresh session_id."""
    sid = _new_color_session_id()
    return jsonify({'session_id': sid})


def _load_session_model():  # pragma: no cover - IO heavy
    """Lazy load the session-level model and supporting metadata.

    Returns:
        model: object with predict_proba / predict
        feature_cols: ordered list of feature column names expected (excluding id/label columns)
        label_map: mapping from class index -> label string (fallback synthesized if missing)
    Raises:
        FileNotFoundError if model not present.
    """
    global _SESSION_MODEL, _FEATURE_COLUMNS, _LABEL_MAP
    if _SESSION_MODEL is not None and _FEATURE_COLUMNS is not None:
        return _SESSION_MODEL, _FEATURE_COLUMNS, _LABEL_MAP or {}
    import pickle, csv
    if not MODEL_ARTIFACT.exists():
        raise FileNotFoundError(f"Missing model artifact: {MODEL_ARTIFACT}")
    with MODEL_ARTIFACT.open('rb') as f:
        _SESSION_MODEL = pickle.load(f)
    # Extract feature column order from features.csv header (excluding session_id & label like fields)
    if FEATURES_CSV.exists():
        with FEATURES_CSV.open('r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, [])
            # Known non-feature columns present in training file
            skip = {'session_id', 'label'}
            _FEATURE_COLUMNS = [c for c in header if c not in skip]
    else:
        # Minimal fallback; expected core engineered features if CSV missing
        _FEATURE_COLUMNS = [
            'n_responses', 'type_1_acc', 'type_2_acc', 'type_3_acc',
            'mae', 'consistency'
        ] + [f'answer_hist_{i}' for i in range(100)]
    # Attempt to detect label map stored alongside model (common pattern)
    # Some training scripts store (model, label_map) tuple; handle gracefully
    if isinstance(_SESSION_MODEL, (tuple, list)) and len(_SESSION_MODEL) >= 2:
        maybe_model, maybe_map = _SESSION_MODEL[0], _SESSION_MODEL[1]
        if hasattr(maybe_model, 'predict_proba'):
            _SESSION_MODEL = maybe_model
            if isinstance(maybe_map, dict):
                _LABEL_MAP = {int(k): str(v) for k, v in maybe_map.items()}
    # Fallback synthesize label map from model classes_ when available
    if _LABEL_MAP is None:
        try:
            classes = getattr(_SESSION_MODEL, 'classes_', None)
            if classes is not None:
                _LABEL_MAP = {i: str(lbl) for i, lbl in enumerate(classes)}
        except Exception:  # pragma: no cover
            _LABEL_MAP = {}
    return _SESSION_MODEL, _FEATURE_COLUMNS, _LABEL_MAP or {}


def _compute_session_features(payload: dict, feature_cols: List[str]) -> List[float]:
    """Build the feature vector in training column order from raw responses payload.

    Expected payload format (sent by frontend when user finishes test):
        {
          'responses': [ { 'numeral': '12', 'expected': '12', 'answer': '12', 'type_idx': 0, 'is_correct': true }, ... ],
          'session_id': '...' (optional)
        }

    Engineering replicates training assumptions:
      - n_responses: len(responses)
      - type_X_acc: accuracy restricted to responses where type_idx == X (if denominator>0 else 0)
      - answer_hist_i: relative frequency of answer numeral i (0-99) among responses
      - type_3_acc included if present in feature set
      - mae: mean absolute error between expected numeral (int) and answer (int) when both numeric
      - consistency: max relative frequency of the most common provided answer
    """
    responses = payload.get('responses') or []
    if not isinstance(responses, list):
        responses = []
    n = len(responses)
    # Accuracies per type index
    by_type_total = {1: 0, 2: 0, 3: 0}
    by_type_correct = {1: 0, 2: 0, 3: 0}
    answer_counts = [0]*100
    abs_err_sum = 0
    abs_err_n = 0
    value_counts = {}
    for r in responses:
        try:
            t_idx = int(r.get('type_idx', 0))
        except Exception:
            t_idx = 0
        is_correct = bool(r.get('is_correct'))
        if t_idx in by_type_total:
            by_type_total[t_idx] += 1
            if is_correct:
                by_type_correct[t_idx] += 1
        answer_raw = str(r.get('answer', '')).strip()
        if answer_raw.isdigit():
            ai = int(answer_raw)
            if 0 <= ai < 100:
                answer_counts[ai] += 1
            exp_raw = str(r.get('expected', '')).strip()
            if exp_raw.isdigit():
                abs_err_sum += abs(int(exp_raw) - ai)
                abs_err_n += 1
        value_counts[answer_raw] = value_counts.get(answer_raw, 0) + 1
    def acc(t):
        tot = by_type_total[t]
        return (by_type_correct[t] / tot) if tot else 0.0
    type_1_acc = acc(1)
    type_2_acc = acc(2)
    type_3_acc = acc(3)
    # answer histogram normalized
    answer_hist = [ (c / n) if n else 0.0 for c in answer_counts ]
    mae = (abs_err_sum / abs_err_n) if abs_err_n else 0.0
    consistency = (max(value_counts.values())/n) if n else 0.0
    # Build full map
    feature_map: Dict[str, float] = {
        'n_responses': float(n),
        'type_1_acc': type_1_acc,
        'type_2_acc': type_2_acc,
        'type_3_acc': type_3_acc,
        'mae': mae,
        'consistency': consistency,
    }
    for i in range(100):
        feature_map[f'answer_hist_{i}'] = answer_hist[i]
    # Now project onto ordered feature_cols (unknown columns default 0)
    vector = []
    for col in feature_cols:
        if col in ('session_id', 'label'):  # skip meta if accidentally present
            continue
        vector.append(float(feature_map.get(col, 0.0)))
    return vector


def _prob_to_severity(prob: float) -> str:
    """Map positive class probability (non-Normal) to severity bucket.

    Heuristic thresholds chosen for demonstration; can be refined with calibration stats.
    """
    if prob < 0.25:
        return 'None'
    if prob < 0.45:
        return 'Mild'
    if prob < 0.70:
        return 'Moderate'
    return 'Severe'

# Decision thresholds for choosing a deficiency even if Normal has the highest raw prob.
# If any deficiency class probability exceeds DEFICIENCY_ABS_THRESHOLD OR
# (Normal_prob - best_def_prob) < NORMAL_MARGIN and best_def_prob >= DEFICIENCY_MIN_THRESHOLD,
# we will pick that deficiency.
DEFICIENCY_ABS_THRESHOLD = 0.55  # confident absolute probability
DEFICIENCY_MIN_THRESHOLD = 0.30  # minimum probability to consider overriding Normal
NORMAL_MARGIN = 0.08             # if Normal only ahead by less than this margin, allow override

# Global default to enable heuristic overrides (probability thresholds + accuracy-based override)
# Set to True to prefer robust, rule-augmented decisions by default.
ALLOW_OVERRIDES_DEFAULT = True

def _decide_final_label(probs: list[dict], *, pure: bool = False) -> str:
    """Decide final label from sanitized probability list with override rules.

    probs: list of {'label': <Name>, 'prob': float} expected to sum ~1.
    Returns canonical label.
    """
    if not probs:
        return 'Normal'
    # Pure argmax: no threshold or margin logic
    if pure:
        top = max(probs, key=lambda d: d['prob'])
        return top['label']
    # Get normal prob
    normal_prob = next((p['prob'] for p in probs if p['label'].lower() == 'normal'), None)
    # Collect deficiency candidates
    deficiencies = [p for p in probs if p['label'] != 'Normal']
    if not deficiencies:
        # Only Normal present
        return 'Normal'
    # Sort deficiencies by probability
    deficiencies.sort(key=lambda d: d['prob'], reverse=True)
    best_def = deficiencies[0]
    best_def_prob = best_def['prob']
    # Direct absolute threshold
    if best_def_prob >= DEFICIENCY_ABS_THRESHOLD:
        return best_def['label']
    if normal_prob is None:
        return best_def['label'] if best_def_prob >= DEFICIENCY_MIN_THRESHOLD else 'Normal'
    # Margin-based override
    if (normal_prob - best_def_prob) < NORMAL_MARGIN and best_def_prob >= DEFICIENCY_MIN_THRESHOLD:
        return best_def['label']
    # Default: choose max probability (standard argmax)
    top = max(probs, key=lambda d: d['prob'])
    return top['label']

def _pad_probs(probs: list[dict]) -> list[dict]:
    """Ensure all four canonical classes appear in the probability table.

    Any class missing is added with prob 0.0. Order is fixed for UX consistency.
    """
    wanted = ["Normal", "Protanopia", "Deuteranopia", "Tritanopia"]
    have = {p['label'] for p in probs}
    padded = list(probs)
    for lbl in wanted:
        if lbl not in have:
            padded.append({'label': lbl, 'prob': 0.0})
    # Keep stable canonical order, or fallback to existing order for user familiarity
    order_map = {lbl:i for i,lbl in enumerate(wanted)}
    padded.sort(key=lambda d: order_map.get(d['label'], 999))
    return padded

# ------------------ Heuristic Override Based on Per-Type Accuracy ------------------
MIN_TYPE_PLATES = 2
LOW_ACC_THRESHOLD = 0.25
OTHER_MIN_THRESHOLD = 0.50

def _compute_type_accuracies(responses: list[dict]):
    """Return per-type accuracy stats for types 1,2,3.

    Returns:
        acc: dict {1: acc1, 2: acc2, 3: acc3}
        counts: dict {1: total1, 2: total2, 3: total3}
        correct: dict {1: correct1, ...}
    """
    counts = {1:0,2:0,3:0}
    correct = {1:0,2:0,3:0}
    for r in responses:
        try:
            t = int(r.get('type_idx',0))
        except Exception:
            t = 0
        if t in counts:
            counts[t] += 1
            # Accept both is_correct or explicit equivalence check
            if bool(r.get('is_correct')) or str(r.get('answer','')).strip() == str(r.get('numeral','')).strip():
                correct[t] += 1
    acc = {k: (correct[k]/counts[k] if counts[k] else 0.0) for k in counts}
    return acc, counts, correct

def _apply_accuracy_heuristic(current_label: str, severity: str, probs: list[dict], responses: list[dict]):
    """Optionally override Normal label if one deficiency type shows distinctly depressed accuracy.

    Returns (new_label, new_severity, meta_dict)
    meta_dict holds per_type_accuracy, type_counts, override flags.
    """
    acc, counts, _ = _compute_type_accuracies(responses)
    # Decide candidates
    candidates = []
    for t in (1,2,3):
        if counts[t] >= MIN_TYPE_PLATES and acc[t] <= LOW_ACC_THRESHOLD:
            # At least one other type with decent accuracy to show selectivity
            others = [acc[o] for o in (1,2,3) if o != t and counts[o] > 0]
            if others and max(others) >= OTHER_MIN_THRESHOLD:
                candidates.append(t)
    override_applied = False
    reason = ''
    new_label = current_label
    new_severity = severity
    if current_label == 'Normal' and len(candidates) == 1:
        t = candidates[0]
        mapping = {1:'Protanopia',2:'Deuteranopia',3:'Tritanopia'}
        new_label = mapping[t]
        # If severity was None but we are overriding, derive a pseudo deficiency probability from accuracy gap
        if severity in ('None',''):
            pseudo_prob = max(0.30, 1.0 - acc[t])  # ensure at least Mild trigger at 0.30
            new_severity = _prob_to_severity(pseudo_prob)
        override_applied = True
        reason = f"overridden_by_accuracy_type{t}_acc={acc[t]:.2f}"
    meta = {
        'per_type_accuracy': {
            'protanopia': acc[1],
            'deuteranopia': acc[2],
            'tritanopia': acc[3]
        },
        'type_plate_counts': {
            'protanopia': counts[1],
            'deuteranopia': counts[2],
            'tritanopia': counts[3]
        },
        'accuracy_override': override_applied,
        'accuracy_override_reason': reason
    }
    return new_label, new_severity, meta

import pickle as _pkl_single
from pathlib import Path as _PathSingle
import pandas as _pd_single

_SINGLE_MODEL_PATH = _PathSingle('color') / 'artifacts' / 'single_logreg_model.pkl'
_single_bundle = None

def _load_single_model():
    global _single_bundle
    if _single_bundle is None and _SINGLE_MODEL_PATH.exists():
        with _SINGLE_MODEL_PATH.open('rb') as f:
            _single_bundle = _pkl_single.load(f)
    return _single_bundle

def _build_single_session_features(responses: list[dict]):
    # Build per-response feature rows then aggregate to session-level features matching training aggregator
    if not responses:
        import numpy as _np
        return _np.zeros((1,0)), []
    rows = []
    for r in responses:
        try:
            numeral = int(str(r.get('numeral','')).strip() or -1)
        except Exception:
            numeral = -1
        try:
            answer = int(str(r.get('answer','')).strip() or -1)
        except Exception:
            answer = -1
        try:
            t_idx = int(str(r.get('type_idx','')).strip() or 0)
        except Exception:
            t_idx = 0
        row = {
            'numeral': max(0, numeral),
            'answer': max(0, answer),
            'type_idx': max(0, t_idx),
            'is_correct_proxy': 1 if answer == numeral and answer >= 0 else 0,
            'abs_err': abs(answer - numeral) if (answer >=0 and numeral>=0) else 0,
            'err_ge10': 1 if (abs(answer - numeral) >= 10 and answer>=0 and numeral>=0) else 0,
            'mod10_num': (numeral % 10) if numeral>=0 else 0,
            'mod10_ans': (answer % 10) if answer>=0 else 0,
            'type_1': 1 if t_idx == 1 else 0,
            'type_2': 1 if t_idx == 2 else 0,
            'type_3': 1 if t_idx == 3 else 0,
        }
        rows.append(row)
    df = _pd_single.DataFrame(rows)
    # Means for all columns
    means = df.mean(numeric_only=True)
    agg = { f"mean_{c}": float(means[c]) for c in means.index }
    # Selected sums
    for c in ["is_correct_proxy","abs_err","err_ge10"]:
        agg[f"sum_{c}"] = float(df[c].sum())
    # Count
    n = len(df)
    agg["n_responses"] = float(n)
    # Per-type counts and accuracies
    for t in (1,2,3):
        mask = (df[f"type_{t}"] == 1)
        ct = int(mask.sum())
        agg[f"count_type{t}"] = ct
        agg[f"acc_type{t}"] = float(df.loc[mask, "is_correct_proxy"].mean()) if ct>0 else 0.0
    # Overall stats
    agg["overall_acc"] = float(df["is_correct_proxy"].mean())
    agg["err_mean"] = float(df["abs_err"].mean())
    agg["err_big_rate"] = float(df["err_ge10"].mean())
    # Answer distribution stats
    vc = df["answer"].value_counts(normalize=True, dropna=False).sort_values(ascending=False).values
    top = float(vc[0]) if vc.size>0 else 0.0
    second = float(vc[1]) if vc.size>1 else 0.0
    # Entropy helper
    def _entropy(vals):
        import numpy as _np
        vals = _np.asarray(vals, dtype=float)
        vals = vals[vals>0]
        if vals.size==0:
            return 0.0
        return float(-_np.sum(vals * _np.log2(vals)))
    agg["ans_hist_entropy"] = _entropy(vc)
    agg["ans_hist_max"] = top
    agg["ans_hist_second"] = second
    agg["ans_hist_gap"] = top - second
    agg["ans_hist_unique"] = int(df["answer"].nunique(dropna=False))
    out = _pd_single.DataFrame([agg])
    return out, rows


@color_bp.post('/predict-session')
def predict_session():
    payload = request.get_json(silent=True) or {}
    responses = payload.get('responses') or []
    if not isinstance(responses, list):
        return jsonify({'error': 'responses must be a list'}), 400
    # Decide override behavior (heuristics) with sensible defaults:
    # - If client specifies allow_overrides, honor it
    # - Else if client specifies pure, invert it
    # - Else use ALLOW_OVERRIDES_DEFAULT (True)
    if 'allow_overrides' in payload:
        allow_overrides = bool(payload.get('allow_overrides'))
    elif 'pure' in payload:
        allow_overrides = not bool(payload.get('pure'))
    else:
        allow_overrides = ALLOW_OVERRIDES_DEFAULT
    pure_mode = not allow_overrides
    # Try single logistic model first
    bundle = _load_single_model()
    if bundle:
        try:
            feat_df, raw_rows = _build_single_session_features(responses)
            order = bundle.get('feature_order', [])
            # align columns
            feat_df = feat_df.reindex(columns=order, fill_value=0)
            model = bundle['model']
            import numpy as _np
            X = feat_df.astype('float32')
            temperature = float(bundle.get('temperature', 1.0) or 1.0)
            if hasattr(model, 'predict_proba'):
                # Use decision_function if available to apply temperature scaling, else fallback to predict_proba
                if temperature != 1.0 and hasattr(model, 'decision_function'):
                    import numpy as _np
                    logits = model.decision_function(X)
                    z = logits / max(1e-6, temperature)
                    z = z - z.max(axis=1, keepdims=True)
                    exp_z = _np.exp(z)
                    p = (exp_z / exp_z.sum(axis=1, keepdims=True))[0]
                else:
                    p = model.predict_proba(X)[0]
                classes = bundle.get('classes') or list(getattr(model, 'classes_', []))
                probs = [ {'label': str(classes[i]), 'prob': float(p[i])} for i in range(len(p)) ]
                # Sanitize labels: drop NaN / blank, map to allowed set
                allowed = {
                    'normal': 'Normal',
                    'protanopia': 'Protanopia', 'protan': 'Protanopia',
                    'deuteranopia': 'Deuteranopia', 'deutanopia': 'Deuteranopia', 'deutan': 'Deuteranopia', 'deuteran': 'Deuteranopia',
                    'tritanopia': 'Tritanopia', 'tritan': 'Tritanopia'
                }
                sanitized = []
                for pr in probs:
                    raw_lbl = pr['label']
                    key = str(raw_lbl).strip().lower()
                    if key in ('', 'nan', 'none', 'null'):
                        continue
                    mapped = allowed.get(key)
                    if not mapped:
                        # If unknown and not normal, skip; we keep only allowed classes
                        continue
                    sanitized.append({'label': mapped, 'prob': pr['prob']})
                # Re-normalize probabilities of kept classes if any were removed
                if sanitized:
                    # Renormalize then apply light Laplace smoothing (alpha=1e-3)
                    total_p = sum(pr['prob'] for pr in sanitized) or 1.0
                    alpha = 1e-3
                    k = len(sanitized)
                    smooth_total = total_p + alpha * k
                    for pr in sanitized:
                        pr['prob'] = float((pr['prob'] + alpha) / smooth_total)
                    probs = sanitized
                # Determine best label among sanitized list
                if probs:
                    probs = _pad_probs(probs)
                    best_lbl = _decide_final_label(probs, pure=pure_mode)
                else:
                    probs = _pad_probs([])
                    best_lbl = 'Normal'
            else:
                pred = model.predict(X)[0]
                probs = []
                key = str(pred).strip().lower()
                if key in ('nan','', 'none','null'):
                    best_lbl = 'Normal'
                else:
                    best_lbl = {
                        'normal':'Normal',
                        'protan':'Protanopia','protanopia':'Protanopia',
                        'deutan':'Deuteranopia','deutanopia':'Deuteranopia','deuteranopia':'Deuteranopia','deuteran':'Deuteranopia',
                        'tritan':'Tritanopia','tritanopia':'Tritanopia'
                    }.get(key, 'Normal')
            probs = _pad_probs(probs)
            normal_prob = next((pr['prob'] for pr in probs if pr['label'].lower()=='normal'), None)
            non_normal_prob = 1.0 - normal_prob if normal_prob is not None else 1.0
            severity = _prob_to_severity(non_normal_prob)
            # Apply heuristic override only if allowed
            if allow_overrides:
                new_label, new_severity, meta = _apply_accuracy_heuristic(best_lbl, severity, probs, responses)
            else:
                new_label, new_severity = best_lbl, severity
                meta = {
                    'per_type_accuracy': _compute_type_accuracies(responses)[0],
                    'type_plate_counts': _compute_type_accuracies(responses)[1],
                    'accuracy_override': False,
                    'accuracy_override_reason': ''
                }
            return jsonify({
                'status': 'ok',
                'engine': 'single_logreg',
                'label': new_label,
                'probs': probs,
                'severity': new_severity,
                'n_responses': len(responses),
                'feature_vector_len': len(order),
                'calibration': {
                    'method': 'temperature_scaling',
                    'temperature': temperature,
                    'smoothing_alpha': 1e-3
                },
                'pure': pure_mode,
                **meta
            })
        except Exception as e:  # fallback to legacy pipeline
            pass
    # Legacy paths (logreg session model or session aggregate)
    try:
        requested_model = str(payload.get('model', 'auto')).lower()
        if requested_model in ('lr','logreg','logistic') and LOGREG_MODEL.exists():
            global _LOGREG_OBJ
            if _LOGREG_OBJ is None:
                import pickle as _pkl
                with LOGREG_MODEL.open('rb') as f:
                    _LOGREG_OBJ = _pkl.load(f)
            lr_model = _LOGREG_OBJ.get('model')
            feat_order = _LOGREG_OBJ.get('feature_order', [])
            vec_full = _compute_session_features(payload, feat_order)
            X = _pd_single.DataFrame([vec_full], columns=feat_order).astype('float32')
            probs = []
            if hasattr(lr_model, 'predict_proba'):
                p = lr_model.predict_proba(X)[0]
                classes = list(getattr(lr_model, 'classes_', [])) or _LOGREG_OBJ.get('classes', [])
                probs = [ {'label': str(classes[i]), 'prob': float(p[i])} for i in range(len(p)) ]
                allowed = {
                    'normal': 'Normal',
                    'protanopia': 'Protanopia', 'protan': 'Protanopia',
                    'deuteranopia': 'Deuteranopia', 'deutanopia': 'Deuteranopia', 'deutan': 'Deuteranopia', 'deuteran': 'Deuteranopia',
                    'tritanopia': 'Tritanopia', 'tritan': 'Tritanopia'
                }
                sanitized = []
                for pr in probs:
                    key = pr['label'].strip().lower()
                    if key in ('','nan','none','null'):
                        continue
                    mapped = allowed.get(key)
                    if not mapped:
                        continue
                    sanitized.append({'label': mapped, 'prob': pr['prob']})
                if sanitized:
                    total_p = sum(pr['prob'] for pr in sanitized) or 1.0
                    for pr in sanitized:
                        pr['prob'] = float(pr['prob']/total_p)
                    probs = sanitized
                if probs:
                    probs = _pad_probs(probs)
                    best_lbl = _decide_final_label(probs, pure=pure_mode)
                else:
                    probs = _pad_probs([])
                    best_lbl = 'Normal'
            else:
                pred = lr_model.predict(X)[0]
                probs = []
                key = str(pred).strip().lower()
                best_lbl = {
                    'normal':'Normal',
                    'protan':'Protanopia','protanopia':'Protanopia',
                    'deutan':'Deuteranopia','deutanopia':'Deuteranopia','deuteranopia':'Deuteranopia','deuteran':'Deuteranopia',
                    'tritan':'Tritanopia','tritanopia':'Tritanopia'
                }.get(key, 'Normal') if key not in ('nan','', 'none','null') else 'Normal'
            probs = _pad_probs(probs)
            normal_candidates = [pr['prob'] for pr in probs if pr['label'].lower()=='normal']
            non_normal_prob = 1.0
            if normal_candidates:
                non_normal_prob = 1.0 - normal_candidates[0]
            severity = _prob_to_severity(non_normal_prob)
            if allow_overrides:
                new_label, new_severity, meta = _apply_accuracy_heuristic(best_lbl, severity, probs, responses)
            else:
                new_label, new_severity = best_lbl, severity
                meta = {
                    'per_type_accuracy': _compute_type_accuracies(responses)[0],
                    'type_plate_counts': _compute_type_accuracies(responses)[1],
                    'accuracy_override': False,
                    'accuracy_override_reason': ''
                }
            return jsonify({
                'status': 'ok',
                'engine': 'logreg',
                'label': new_label,
                'probs': probs,
                'severity': new_severity,
                'feature_vector_len': len(vec_full),
                'n_responses': len(responses),
                'pure': pure_mode,
                **meta
            })
        model, feature_cols, label_map = _load_session_model()
        vec = _compute_session_features(payload, feature_cols)
        X = _pd_single.DataFrame([vec], columns=feature_cols).astype('float32')
        probs = []
        if hasattr(model, 'predict_proba'):
            p = model.predict_proba(X)[0]
            if label_map and len(label_map) == len(p):
                probs = [ {'label': label_map[i], 'prob': float(p[i])} for i in range(len(p)) ]
            else:
                probs = [ {'label': str(i), 'prob': float(p[i])} for i in range(len(p)) ]
            best_idx = int(p.argmax())
        else:
            pred = model.predict(X)[0]
            probs = []
            try:
                classes = getattr(model, 'classes_', [])
                best_idx = int(list(classes).index(pred)) if pred in classes else 0
            except Exception:
                best_idx = 0
        # Sanitize and then re-decide label
        raw_label = label_map.get(best_idx, 'Unknown') if label_map else 'Unknown'
        key = str(raw_label).strip().lower()
        label = {
            'normal': 'Normal',
            'protan': 'Protanopia', 'protanopia': 'Protanopia',
            'deutan': 'Deuteranopia','deutanopia':'Deuteranopia','deuteranopia':'Deuteranopia','deuteran':'Deuteranopia',
            'tritan': 'Tritanopia','tritanopia':'Tritanopia'
        }.get(key, 'Normal' if key in ('nan','', 'none','null') else 'Normal')
        # If predict_proba path gave us probs, re-normalize & re-decide
        if probs:
            allowed_map = { 'normal':'Normal','protanopia':'Protanopia','protan':'Protanopia', 'deuteranopia':'Deuteranopia','deutanopia':'Deuteranopia','deutan':'Deuteranopia','deuteran':'Deuteranopia','tritanopia':'Tritanopia','tritan':'Tritanopia' }
            sanitized = []
            for pr in probs:
                k = pr['label'].strip().lower()
                if k in ('','nan','none','null'):
                    continue
                mapped = allowed_map.get(k)
                if not mapped:
                    continue
                sanitized.append({'label': mapped, 'prob': pr['prob']})
            if sanitized:
                tot = sum(p['prob'] for p in sanitized) or 1.0
                for p in sanitized:
                    p['prob'] = float(p['prob']/tot)
                probs = sanitized
                label = _decide_final_label(probs, pure=pure_mode)
        non_normal_prob = 1.0
        probs = _pad_probs(probs)
        if probs:
            normal_candidates = [pr['prob'] for pr in probs if pr['label'].lower()=='normal']
            if normal_candidates:
                non_normal_prob = 1.0 - normal_candidates[0]
        severity = _prob_to_severity(non_normal_prob)
        if allow_overrides:
            new_label, new_severity, meta = _apply_accuracy_heuristic(label, severity, probs, responses)
        else:
            new_label, new_severity = label, severity
            meta = {
                'per_type_accuracy': _compute_type_accuracies(responses)[0],
                'type_plate_counts': _compute_type_accuracies(responses)[1],
                'accuracy_override': False,
                'accuracy_override_reason': ''
            }
        return jsonify({
            'status': 'ok',
            'engine': 'session_model',
            'label': new_label,
            'probs': probs,
            'severity': new_severity,
            'feature_vector_len': len(vec),
            'n_responses': len(responses),
            'pure': pure_mode,
            **meta
        })
    except FileNotFoundError:
        # Fallback heuristic if model artifacts not present
        # Compute simple accuracies and pick worst performing type
        feature_cols = [ 'n_responses','type_1_acc','type_2_acc','type_3_acc' ]
        vec = _compute_session_features(payload, feature_cols)
        # indices: n_responses=0, type1=1,type2=2,type3=3
        type_accs = vec[1:4]
        worst_idx = 1 + int(min(range(len(type_accs)), key=lambda i: type_accs[i]))
        mapping = {1: 'Protanopia?', 2: 'Deutanopia?', 3: 'Tritanopia?'}
        label = mapping.get(worst_idx, 'Normal')
        non_normal_prob = 1.0 - max(type_accs)
        severity = _prob_to_severity(non_normal_prob)
        probs = [
            {'label': 'Normal', 'prob': float(max(type_accs))},
            {'label': 'Deficiency', 'prob': float(non_normal_prob)}
        ]
        new_label, new_severity, meta = _apply_accuracy_heuristic(label, severity, probs, responses)
        return jsonify({
            'status': 'degraded',
            'label': new_label,
            'probs': probs,
            'severity': new_severity,
            'feature_vector_len': len(vec),
            'n_responses': len(responses),
            **meta
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Dynamic plate generation (simple placeholder version)
@color_bp.post('/next-plate')
def next_plate():
    try:
        payload = request.get_json(silent=True) or {}
        plate_id = int(payload.get('plate_id', 0))
        type_idx = int(payload.get('type_idx', 0))  # 0 normal, 1 protan, 2 deutan, 3 tritan (example)
        numeral = str(payload.get('numeral', '12'))
        seed = int(payload.get('seed', plate_id * 101 + type_idx * 31 + len(numeral) * 7))
        style = payload.get('style', 'simple')  # 'simple' | 'ishihara'

        if style == 'ishihara':
            img, meta = _generate_ishihara_plate(numeral=numeral, type_idx=type_idx, seed=seed)
            GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"adv_{plate_id}_{type_idx}_{numeral}_{seed}.png"
            out_path = GENERATED_DIR / filename
            img.save(out_path, format='PNG')
            return jsonify({
                'plate_id': plate_id,
                'type_idx': type_idx,
                'numeral': numeral,
                'seed': seed,
                'path': f"/static/color/plates/generated/{filename}",
                'meta': meta | {'method': 'advanced'}
            })

        import random
        from PIL import Image, ImageDraw, ImageFont
       
        random.seed(seed)
        w = h = 512
        img = Image.new('RGB', (w, h), (28, 28, 30))
        dr = ImageDraw.Draw(img)
        # Basic dot cloud background
        for _ in range(1400):
            r = random.randint(4, 10)
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            # palette shifts based on type_idx
            if type_idx == 1:      # protan
                base = (random.randint(120, 180), random.randint(30, 80), random.randint(30, 80))
            elif type_idx == 2:    # deutan
                base = (random.randint(40, 90), random.randint(120, 180), random.randint(40, 90))
            elif type_idx == 3:    # tritan
                base = (random.randint(40, 90), random.randint(40, 90), random.randint(120, 200))
            else:                  # normal
                base = (random.randint(80, 200), random.randint(80, 200), random.randint(80, 200))
            dr.ellipse((x - r, y - r, x + r, y + r), fill=base)

        # Draw numeral in contrasting dots
        try:
            ft = ImageFont.truetype('arial.ttf', 180)
        except Exception:
            ft = ImageFont.load_default()
        tw, th = dr.textbbox((0, 0), numeral, font=ft)[2:]
        tx, ty = (w - tw) // 2, (h - th) // 2
        for _ in range(800):
            r = random.randint(4, 9)
            # pick a random point inside text bounding box; only draw if inside glyph mask
            px = random.randint(tx, tx + tw - 1)
            py = random.randint(ty, ty + th - 1)
            # naive mask test using text rendering onto temp single pixel offset (fast enough here)
            # Render once to an alpha mask lazily (cache not implemented to keep simple)
            # For simplicity we approximate by drawing text outline background then dots on it.
            base_col = (220, 70, 70) if type_idx != 1 else (250, 200, 80)
            dr.ellipse((px - r, py - r, px + r, py + r), fill=base_col)

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"gen_{plate_id}_{type_idx}_{numeral}_{seed}.png"
        out_path = GENERATED_DIR / filename
        img.save(out_path, format='PNG')

        return jsonify({
            'plate_id': plate_id,
            'type_idx': type_idx,
            'numeral': numeral,
            'seed': seed,
            'path': f"/static/color/plates/generated/{filename}",
            'meta': {'method': 'simple', 'dots': 2200}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -----------------------------
# Color Vision Deficiency (CVD) Simulation (server-side)
# -----------------------------
# While the client already performs simulation via JS, this endpoint allows
# server-side generation so images can be stored, shared, or processed further.
# Uses simple linear RGB matrices (approximate) inspired by common references
# (e.g. Machado et al.). These are NOT perceptually perfect but are lightweight.

_CVD_MATRICES = {
    'protan': [
        [0.567, 0.433, 0.000],
        [0.558, 0.442, 0.000],
        [0.000, 0.242, 0.758],
    ],
    'deutan': [
        [0.625, 0.375, 0.000],
        [0.700, 0.300, 0.000],
        [0.000, 0.300, 0.700],
    ],
    'tritan': [
        [0.950, 0.050, 0.000],
        [0.000, 0.433, 0.567],
        [0.000, 0.475, 0.525],
    ],
}


def _generate_ishihara_plate(numeral: str, type_idx: int, seed: int, size: int = 512) -> Tuple['Image.Image', dict]:
    """Generate a more Ishihara-like plate.

    Approach:
      1. Derive two hue clusters (foreground/background) with controlled separation.
      2. Create a text mask for the numeral using a large font.
      3. Scatter varying-radius dots using stratified random placement.
      4. Assign foreground palette to dots whose centers fall on numeral mask; background otherwise.
      5. Slightly perturb luminance/saturation within cluster for natural variation.
    """
    from PIL import Image, ImageDraw, ImageFont
    rng = random.Random(seed)
    # Palette hue base chosen per deficiency type to accentuate confusion lines
    base_hues = {0: 30/360, 1: 10/360, 2: 90/360, 3: 220/360}
    h1 = base_hues.get(type_idx, 0.08)
    hue_sep = 0.18  # separation in hue space
    h2 = (h1 + hue_sep + rng.uniform(-0.02, 0.02)) % 1.0
    if rng.random() < 0.5:
        h1, h2 = h2, h1
    def mk_palette(h: float) -> List[Tuple[int,int,int]]:
        pals = []
        for _ in range(32):
            s = rng.uniform(0.55, 0.85)
            v = rng.uniform(0.55, 0.85)
            r,g,b = colorsys.hsv_to_rgb((h + rng.uniform(-0.015,0.015))%1.0, s, v)
            pals.append((int(r*255), int(g*255), int(b*255)))
        return pals
    fg_palette = mk_palette(h1)
    bg_palette = mk_palette(h2)
    img = Image.new('RGB', (size, size), (255,255,255))
    msk = Image.new('L', (size, size), 0)
    dr_m = ImageDraw.Draw(msk)
    try:
        ft = ImageFont.truetype('arial.ttf', int(size*0.55))
    except Exception:
        ft = ImageFont.load_default()
    tw, th = dr_m.textbbox((0,0), numeral, font=ft)[2:]
    tx, ty = (size - tw)//2, (size - th)//2
    dr_m.text((tx, ty), numeral, fill=255, font=ft)
    mask_px = msk.load()
    dr = ImageDraw.Draw(img)
    # Dot placement parameters
    dot_count = int(size*size / 130)  # density heuristic
    min_r, max_r = int(size*0.007), int(size*0.02)
    # Simple rejection sampling with attempt cap
    for _ in range(dot_count):
        r = rng.randint(min_r, max_r)
        x = rng.randint(r, size - r - 1)
        y = rng.randint(r, size - r - 1)
        is_fg = mask_px[x, y] > 128
        palette = fg_palette if is_fg else bg_palette
        col = palette[rng.randrange(len(palette))]
        # Slight radial vignette lighten to mimic plate edges
        dx = (x - size/2) / (size/2)
        dy = (y - size/2) / (size/2)
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0.9:
            col = tuple(int(c + (255-c)*0.35) for c in col)
        dr.ellipse((x-r, y-r, x+r, y+r), fill=col)
    meta = {
        'hues': [h1, h2],
        'dot_count': dot_count,
        'radii': [min_r, max_r],
        'numeral': numeral,
        'seed': seed,
    }
    return img, meta


def _simulate_cvd(img, mode: str):
    """Apply an approximate color vision deficiency matrix to a PIL.Image.

    Args:
        img: PIL.Image in RGB mode.
        mode: one of 'protan','deutan','tritan'.
    Returns:
        New PIL.Image with simulated colors.
    Raises:
        ValueError: if mode unsupported or numpy missing.
    """
    if np is None:
        raise ValueError("numpy not available for server-side simulation")
    mode = mode.lower()
    if mode not in _CVD_MATRICES:
        raise ValueError(f"Unsupported mode '{mode}'")
    if img.mode != 'RGB':
        img = img.convert('RGB')
    arr = np.asarray(img).astype('float32') / 255.0  # (H,W,3)
    m = np.array(_CVD_MATRICES[mode], dtype='float32')  # (3,3)
    # Matrix multiply each pixel: (H,W,3) dot (3,3)
    sim = arr @ m.T
    sim = np.clip(sim, 0.0, 1.0)
    out = (sim * 255.0 + 0.5).astype('uint8')
    from PIL import Image  # local import to avoid top-level if Pillow missing earlier
    return Image.fromarray(out, mode='RGB')


@color_bp.post('/simulate')
def simulate_image():
    """Accept an uploaded image and return server-generated CVD simulation variants.

    Request:
        multipart/form-data with field 'image'. Optional query/form 'modes' comma list.
        Optional 'max_side' to constrain largest dimension (int, default 800).
    Response JSON:
        {
          'id': <uuid>,
          'original': '/static/color/simulated/<id>_orig.png',
          'variants': { 'protan': '..._protan.png', ... },
          'width': W, 'height': H, 'modes': [...]
        }
    Error codes: 400 invalid input, 500 internal.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'missing file field: image'}), 400
    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'empty filename'}), 400
    from PIL import Image
    data = file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        return jsonify({'error': f'cannot open image: {e}'}), 400
    max_side = int(request.form.get('max_side', 800) or 800)
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    modes_param = request.form.get('modes', 'protan,deutan,tritan')
    modes = [m.strip().lower() for m in modes_param.split(',') if m.strip()]
    modes = [m for m in modes if m in _CVD_MATRICES]
    if not modes:
        return jsonify({'error': 'no valid modes supplied'}), 400
    SIMULATED_DIR.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex
    # Save original (normalized to PNG)
    orig_name = f"{uid}_orig.png"
    orig_path = SIMULATED_DIR / orig_name
    img.save(orig_path, format='PNG')
    variants = {}
    for m in modes:
        try:
            sim_img = _simulate_cvd(img, m)
            out_name = f"{uid}_{m}.png"
            sim_img.save(SIMULATED_DIR / out_name, format='PNG')
            variants[m] = f"/static/color/simulated/{out_name}"
        except Exception as e:  # capture per-mode errors
            variants[m] = {'error': str(e)}
    return jsonify({
        'id': uid,
        'original': f"/static/color/simulated/{orig_name}",
        'variants': variants,
        'width': img.width,
        'height': img.height,
        'modes': modes
    })

