"""Build a labeled per-response CSV from logs for training.

Reads:
  color/responses.csv  (columns: numeral,type_idx,answer,timestamp,session_id)
  color/results.csv    (columns: session_id,timestamp,total_questions,label,probs_json)

Writes:
  color/artifacts/responses_labeled.csv  (per-response rows + 'label' column)

Usage (PowerShell):
  python -m color.scripts.build_features_from_logs --min-answers 10
  python -m color.scripts.train_single_model color/artifacts/responses_labeled.csv --label-col label --aggregate
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RESP = BASE / 'responses.csv'
RESU = BASE / 'results.csv'
ART = BASE / 'artifacts'
ART.mkdir(parents=True, exist_ok=True)

ALLOWED = {
    'normal': 'Normal',
    'protanopia': 'Protanopia', 'protan': 'Protanopia',
    'deuteranopia': 'Deuteranopia', 'deutanopia': 'Deuteranopia', 'deutan': 'Deuteranopia', 'deuteran': 'Deuteranopia',
    'tritanopia': 'Tritanopia', 'tritan': 'Tritanopia'
}


def parse_args():
    ap = argparse.ArgumentParser("Build labeled responses from logs")
    ap.add_argument('--min-answers', type=int, default=10, help='Minimum responses per session to include')
    ap.add_argument('--out', type=Path, default=ART / 'responses_labeled.csv', help='Output CSV path')
    return ap.parse_args()


def main():
    args = parse_args()
    if not RESP.exists() or not RESU.exists():
        raise SystemExit(f"Missing logs. Need {RESP} and {RESU}")
    df_resp = pd.read_csv(RESP)
    # Expected columns
    for c in ['session_id','numeral','type_idx','answer']:
        if c not in df_resp.columns:
            raise SystemExit(f"responses.csv missing column: {c}")
    # Basic cleaning
    df_resp['session_id'] = df_resp['session_id'].astype(str)
    for c in ['numeral','type_idx','answer']:
        df_resp[c] = pd.to_numeric(df_resp[c], errors='coerce').fillna(-1).astype(int)

    df_resu = pd.read_csv(RESU)
    if 'session_id' not in df_resu.columns or 'label' not in df_resu.columns:
        # Backward compatibility: some logs may store probs_json only; skip such sessions
        missing = [c for c in ['session_id','label'] if c not in df_resu.columns]
        raise SystemExit(f"results.csv missing {missing}; cannot build labels")
    df_resu['session_id'] = df_resu['session_id'].astype(str)
    # Normalize labels and take the first class if slash-separated
    def norm_label(x: str) -> str:
        raw = str(x).split('/')[0].strip().lower()
        return ALLOWED.get(raw, '')
    df_resu['label'] = df_resu['label'].map(norm_label)
    df_resu = df_resu[df_resu['label'] != '']

    # Filter by min answers per session
    counts = df_resp.groupby('session_id').size()
    keep_sessions = counts[counts >= args.min_answers].index.astype(str)
    df_resp = df_resp[df_resp['session_id'].isin(keep_sessions)]

    # Join labels
    df = df_resp.merge(df_resu[['session_id','label']], on='session_id', how='inner')
    # Drop sessions with conflicting labels (keep majority)
    # Compute dominant label per session
    maj = (df.groupby(['session_id','label']).size()
             .reset_index(name='n')
             .sort_values(['session_id','n'], ascending=[True, False])
             .drop_duplicates('session_id'))
    df = df.drop(columns=['label']).merge(maj[['session_id','label']], on='session_id', how='left')

    # Save
    df[['session_id','numeral','type_idx','answer','label']].to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")


if __name__ == '__main__':
    main()
