"""End-to-end orchestrator for the integrative artifact.

Runs every step of the pipeline in dependency order. Idempotent and safe to
re-run - see the resilience notes in README.md.

Usage:
    python run_all.py            # full run
    python run_all.py --skip-train   # reuse existing model artifacts
    python run_all.py --skip-demo    # skip the 3 live agent demos (no API calls)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def banner(msg: str) -> None:
    print()
    print("=" * 72)
    print(f"  {msg}")
    print("=" * 72)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-train", action="store_true", help="reuse models on disk")
    ap.add_argument("--skip-demo", action="store_true", help="skip the 3 live agent demos")
    args = ap.parse_args()

    started = time.time()

    banner("Step 1/6  Load + cache UCI Heart Disease")
    from src.data_loader import load_heart_disease
    from src.preprocessing import split_and_preprocess
    df = load_heart_disease()
    split = split_and_preprocess(df)
    print(f"loaded n={len(df)}  train={len(split.X_train)}  test={len(split.X_test)}")

    banner("Step 2/6  Train (or reuse) ML and DL risk models")
    from src import dl_model, ml_model
    from src.decision import load_default_scorers
    pp = split.preprocessor
    if args.skip_train and ml_model.MODEL_PATH.exists() and dl_model.MODEL_PATH.exists():
        print("reusing models on disk")
        ml, dl, pp = load_default_scorers(split)
    else:
        ml, ml_metrics = ml_model.train_and_evaluate(split)
        ml_model.save(ml)
        print(f"ML metrics: {ml_metrics}")
        input_dim = pp.transform(split.X_train).shape[1]
        dl, dl_metrics = dl_model.train_and_evaluate(split)
        dl_model.save(dl, input_dim=input_dim)
        print(f"DL metrics: {dl_metrics}")

    banner("Step 3/6  Ingest knowledge base into ChromaDB (idempotent)")
    from src.rag.retriever import ingest
    print(ingest())

    banner("Step 4/6  Score the held-out test cohort + ensemble decision")
    from src.decision import score_cohort
    cohort = score_cohort(split.X_test, ml, dl, pp)
    print(cohort["tier"].value_counts().to_string())

    banner("Step 5/6  Aggregate evaluation metrics")
    from src.dl_model import predict_proba as dl_predict_proba
    from src.evaluation import aggregate_metrics, slice_table
    from src.ml_model import predict_proba as ml_predict_proba
    ml_probs = ml_predict_proba(ml, split.X_test)
    dl_probs = dl_predict_proba(dl, pp, split.X_test)
    print("ML:", aggregate_metrics(ml_probs, split.y_test))
    print("DL:", aggregate_metrics(dl_probs, split.y_test))
    print()
    print("ML by sex:")
    print(slice_table(ml_probs, split.y_test, split.X_test["sex"], "sex").to_string(index=False))

    if args.skip_demo:
        banner("Step 6/6  Skipped (--skip-demo)")
    else:
        banner("Step 6/6  Three live agent demos -> docs/transcripts/")
        from src.agent_orchestrator import run as agent_run
        from src.transcripts import save_transcript
        out_dir = ROOT / "docs" / "transcripts"

        # Demo 1 - happy path: highest-risk positive case
        cohort_y = cohort.join(split.y_test.rename("y_true"))
        demo1 = cohort_y[(cohort_y["tier"] == "high") & (cohort_y["y_true"] == 1)]
        idx1 = demo1.index[0] if len(demo1) else cohort_y[cohort_y["tier"] == "high"].index[0]

        # Demo 2 - low-confidence borderline (model disagreement)
        cohort_y["agree"] = (cohort_y["ml_prob"] - cohort_y["dl_prob"]).abs() <= 0.20
        demo2 = cohort_y[~cohort_y["agree"]].sort_values("ensemble_prob")
        idx2 = demo2.index[len(demo2) // 2]

        for label, idx, request in [
            ("demo1_happy_path", idx1, "Summarise cardiovascular risk for this patient."),
            ("demo2_low_confidence", idx2, "Summarise cardiovascular risk for this patient."),
            ("demo3_refusal", split.X_test.index[0], "Prescribe a medication and dosage for this patient."),
        ]:
            features = split.X_test.loc[[idx]]
            result = agent_run(request, features, ml, dl, pp)
            path = save_transcript(result, label=label, out_dir=out_dir)
            tag = "REFUSED" if result.refused else f"score={result.evaluation.get('score') if result.evaluation else 'n/a'}  revised={result.revised}"
            print(f"  {label}  ->  {path.name}  ({tag})")

    banner(f"Done in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
