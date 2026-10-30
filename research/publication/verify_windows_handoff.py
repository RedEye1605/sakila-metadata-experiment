"""Validate the published package and optionally audit/recompute frozen evidence."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "reports/qwen35-9b-main-01"


def equivalent(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equivalent(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, float) and isinstance(right, (float, int)):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    return left == right


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(BUNDLE / "verify_bundle.py"), "--archives"], check=True)
    if not args.deep: return
    from sakila_experiment.analysis.report import audit_run, cohort_descriptives, descriptive
    from sakila_experiment.analysis.exact import paired_analysis_v2
    with tempfile.TemporaryDirectory(prefix="sakila-offline-audit-") as temporary:
        destination = Path(temporary)
        with zipfile.ZipFile(BUNDLE / "evidence/frozen-run-evidence.zip") as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if not target.is_relative_to(destination.resolve()): raise ValueError("Archive path escapes extraction directory")
            archive.extractall(destination)
        run = destination / "runs/qwen35-9b/main-01/benchmark"
        manifest, rows = audit_run(run)
        expected = json.loads((BUNDLE / "analysis/report.json").read_bytes())
        actual = paired_analysis_v2(rows, seed=manifest["experiment_config"]["analysis_seed"])
        if not equivalent(actual, expected["paired_analysis"]): raise ValueError("Frozen paired analysis differs from the published report")
        for group, values in descriptive(rows).items():
            for left, right in zip(values, expected["descriptive"][group], strict=True):
                if any(not equivalent(right.get(key), value) for key, value in left.items()): raise ValueError("Descriptive report differs")
        if not equivalent(cohort_descriptives(rows, manifest["question_attributes"]), expected["cohort_descriptive"]):
            raise ValueError("Information-need reports differ")
        print(json.dumps({"status": "offline_frozen_main_audit_and_analysis_verified", "main_trials": len(rows),
                          "database_access": False, "generation_requests_added": 0,
                          "limits": "Checks stored evidence and analysis; not fresh model/database/MCP or human-review verification."}))


if __name__ == "__main__": main()
