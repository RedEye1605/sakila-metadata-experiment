"""Portable standard-library-only check of the published writing/evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archives", action="store_true", help="Also hash every archived evidence entry")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_bytes())
    for name, record in manifest["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root): raise ValueError("Package path escapes its root")
        data = path.read_bytes()
        if len(data) != record["size_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Package file changed: " + name)
    rows = [json.loads(line) for line in (root / "evidence/main-trials.jsonl").read_bytes().splitlines() if line.strip()]
    if len(rows) != 600 or len({r["trial_id"] for r in rows}) != 600: raise ValueError("Main outcomes are incomplete or duplicated")
    if Counter(r["scenario_id"] for r in rows) != {s: 150 for s in ("S0", "S1", "S2", "S3")}:
        raise ValueError("Main scenario denominators differ")
    if Counter(r["complexity"] for r in rows) != {s: 200 for s in ("simple", "medium", "complex")}:
        raise ValueError("Main complexity denominators differ")
    report = json.loads((root / "analysis/report.json").read_bytes())
    totals = {}
    for record in report["descriptive"]["by_scenario"]:
        selected = [row for row in rows if row["scenario_id"] == record["scenario_id"]]
        correct = sum(row["execution_accuracy"] for row in selected)
        if record["trials"] != len(selected) or record["correct"] != correct: raise ValueError("Published totals differ from stored outcomes")
        totals[record["scenario_id"]] = correct
    archive_count = 0
    if args.archives:
        with zipfile.ZipFile(root / manifest["archive"]["path"]) as archive:
            index = json.loads(archive.read("ARCHIVE_INDEX.json"))
            if len(archive.namelist()) != len(set(archive.namelist())): raise ValueError("Duplicate archive entry")
            if set(archive.namelist()) != {"ARCHIVE_INDEX.json", *index["entries"]}: raise ValueError("Archive coverage differs")
            for name, record in index["entries"].items():
                path = Path(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name: raise ValueError("Unsafe archive path")
                data = archive.read(name)
                if len(data) != record["size_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise ValueError("Archived evidence changed: " + name)
            archive_count = len(index["entries"])
    print(json.dumps({"status": "published_bundle_verified", "files_verified": len(manifest["files"]),
        "archive_entries_verified": archive_count, "main_trials": len(rows), "correct": totals,
        "generation_requests_added": 0, "database_access": False}, indent=2))


if __name__ == "__main__": main()
