"""One-shot read-only progress for the researcher; no background monitoring."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
run = ROOT / "runs/qwen35-9b/main-01"
ledger = run / "benchmark/ledger.sqlite3"
counts = {}
if ledger.exists():
    with sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True) as connection:
        counts = dict(connection.execute("SELECT kind,COUNT(*) FROM events GROUP BY kind"))
events = run / "driver-events.jsonl"
latest = json.loads(events.read_text().splitlines()[-1]) if events.exists() and events.stat().st_size else None
print(json.dumps({"assigned_main_trials": 600, "event_counts": counts,
                  "completed_main_trials": counts.get("trial_completed", 0),
                  "latest_stage": latest, "primary_report_ready": (run / "primary-completion.json").exists(),
                  "pipeline_complete": (run / "pipeline-completion.json").exists()}, ensure_ascii=False, indent=2))
