"""Reject damaged/incomplete run artifacts before calculating any metrics."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from ..artifacts import canonical_json, publish_artifact, sha256_bytes


class IntegrityError(ValueError):
    pass


def audit_run(directory: Path) -> tuple[dict, list[dict]]:
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    completion = json.loads((directory / "completion.json").read_bytes())
    if completion["manifest_sha256"] != sha256_bytes(manifest_bytes) or not completion.get("database_unchanged"):
        raise IntegrityError("Run completion does not match its manifest or database consistency check")
    assignments = json.loads((directory / "plan.json").read_bytes())
    if sha256_bytes(canonical_json(assignments)) != manifest["trial_plan_sha256"]:
        raise IntegrityError("Trial plan hash mismatch")
    plan = {a["trial_id"]: a for a in assignments}
    if len(plan) != len(assignments):
        raise IntegrityError("Duplicate planned trial")
    rows = [json.loads(line) for line in (directory / "trials.jsonl").read_bytes().splitlines() if line.strip()]
    records = {row["trial_id"]: row for row in rows}
    if len(records) != len(rows) or records.keys() != plan.keys() or len(rows) != completion["completed_trials"]:
        raise IntegrityError("Missing or duplicate terminal trial")
    with sqlite3.connect((directory / "ledger.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as ledger:
        registered = ledger.execute("SELECT manifest_json,manifest_sha256 FROM experiments WHERE experiment_id=?", (manifest["experiment_id"],)).fetchone()
        if not registered or registered != (manifest_bytes.decode(), sha256_bytes(manifest_bytes)):
            raise IntegrityError("Registered manifest differs from the published manifest")
        terminal = {}
        events = []
        for sequence, trial_id, attempt, kind, timestamp, payload, digest in ledger.execute("SELECT sequence,trial_id,attempt_id,kind,timestamp_utc,payload_json,payload_sha256 FROM events WHERE experiment_id=? ORDER BY sequence", (manifest["experiment_id"],)):
            if sha256_bytes(payload.encode()) != digest:
                raise IntegrityError("Ledger event content hash mismatch")
            events.append(canonical_json({"sequence": sequence, "experiment_id": manifest["experiment_id"], "trial_id": trial_id,
                                          "attempt_id": attempt, "kind": kind, "timestamp_utc": timestamp, "payload": json.loads(payload), "payload_sha256": digest}))
            if kind == "trial_completed":
                if trial_id in terminal:
                    raise IntegrityError("Duplicate terminal ledger event")
                terminal[trial_id] = json.loads(payload)
        if terminal != records:
            raise IntegrityError("Exported trials differ from durable ledger outcomes")
        if b"".join(events) != (directory / "events.jsonl").read_bytes():
            raise IntegrityError("Exported event log differs from the durable ledger")
    for trial_id, row in records.items():
        if any(row[key] != value for key, value in plan[trial_id].items()):
            raise IntegrityError("Trial identity differs from its assignment")
        if type(row.get("execution_accuracy")) is not int or row["execution_accuracy"] not in (0, 1):
            raise IntegrityError("An infrastructure outcome cannot be counted as a completed EX trial")
        if row["model_version_or_hash"] != manifest["model_version_or_hash"] or row["inference_config"] != manifest["inference_config"]:
            raise IntegrityError("Model or inference configuration changed")
        if row["snapshot_sha256"] != manifest["snapshots"]["snapshot_sha256"][row["scenario_id"]]:
            raise IntegrityError("Scenario snapshot changed")
        if manifest.get("comparator_version") == "ex-results-v3-column-permutation":
            if row.get("column_order_policy") != "permutation":
                raise IntegrityError("Trial column-order policy differs from the frozen comparator")
            if row["execution_accuracy"] == 1:
                width = json.loads((directory / "gold-results" / f"{row['question_id']}.json").read_bytes())["column_count"]
                mapping = row.get("column_permutation")
                if (not isinstance(mapping, list) or any(type(i) is not int for i in mapping)
                        or sorted(mapping) != list(range(width))):
                    raise IntegrityError("Correct v3 outcome lacks a complete global column bijection")
        if manifest.get("benchmark_manifest_sha256") or manifest.get("candidate_manifest_sha256"):
            settings = manifest["inference_config"]
            expected_request = {"model": manifest["model_id"], "temperature": settings["temperature"],
                                "top_p": settings["top_p"], "top_k": settings["top_k"],
                                "max_tokens": settings["max_output_tokens"], "seed": row["inference_seed"],
                                **manifest["fixed_request_parameters"], "messages_sha256": row["prompt_hash"]}
            if row.get("resolved_request_parameters") != expected_request:
                raise IntegrityError("Resolved request differs from frozen settings, seed or prompt")
        files = [(directory / "prompts" / f"{row['prompt_hash']}.json", row["prompt_hash"]),
                 (directory / "gold-results" / f"{row['question_id']}.json", row["gold_result_hash"])]
        if row["execution_result_hash"] is not None:
            files.append((directory / "results" / f"{trial_id}.json", row["execution_result_hash"]))
        for path, digest in files:
            if sha256_bytes(path.read_bytes()) != digest:
                raise IntegrityError("Prompt or execution result hash mismatch")
    if manifest["mode"] in {"main", "preliminary"}:
        if len(rows) != 600 or (manifest["mode"] == "main" and manifest.get("main_experiment_allowed") is not True):
            raise IntegrityError("Main analysis requires a reviewed complete 600-trial run")
        if Counter(r["scenario_id"] for r in rows) != {s: 150 for s in ("S0", "S1", "S2", "S3")}:
            raise IntegrityError("Main scenario denominators are incomplete")
        if Counter(r["complexity"] for r in rows) != {s: 200 for s in ("simple", "medium", "complex")}:
            raise IntegrityError("Main complexity denominators are incomplete")
        identifiers = {r["question_id"] for r in rows}
        expected = {(q, s, r) for q in identifiers for s in ("S0", "S1", "S2", "S3") for r in range(1, 6)}
        if len(identifiers) != 30 or {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in rows} != expected:
            raise IntegrityError("Paired question/scenario/repetition structure is incomplete")
    elif manifest["mode"] == "diagnostic":
        from ..experiment.diagnostics import VARIANTS
        identifiers = {r["question_id"] for r in rows}
        expected = {(q, v, r) for q in identifiers for v in VARIANTS for r in range(1, 4)}
        if len(rows) != 180 or len(identifiers) != 12 or any(not q.startswith("P") for q in identifiers):
            raise IntegrityError("Diagnostic requires 12 separate pilot questions and 180 outcomes")
        if {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in rows} != expected or any(r.get("variant_id") != r["scenario_id"] for r in rows):
            raise IntegrityError("Diagnostic variant/repetition structure is incomplete")
        if manifest.get("benchmark_manifest_sha256") is None:
            raise IntegrityError("Diagnostic lacks its versioned benchmark binding")
    elif manifest["mode"] == "candidate_pilot":
        identifiers = {r["question_id"] for r in rows}
        expected = {(q, s, r) for q in identifiers for s in ("S0", "S1", "S2", "S3") for r in (1, 2)}
        if (len(rows) != 96 or len(identifiers) != 12 or any(not q.startswith("P3") for q in identifiers)
                or {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in rows} != expected
                or manifest.get("main_experiment_allowed") is not False
                or manifest.get("evaluation_status") != "engineering_draft_reference"
                or not manifest.get("candidate_manifest_sha256")):
            raise IntegrityError("Capability pilot must retain its separate complete12-by4-by2design")
    elif manifest["mode"] == "engineering_smoke":
        identifiers = {r["question_id"] for r in rows}
        expected = {(q, s, 1) for q in identifiers for s in ("S0", "S1", "S2", "S3")}
        if (len(rows) != 12 or len(identifiers) != 3 or any(not q.startswith("P") for q in identifiers)
                or {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in rows} != expected
                or not manifest.get("smoke_manifest_sha256")):
            raise IntegrityError("Engineering smoke requires its complete separate3-by4design")
    elif manifest["mode"] not in {"pilot", "pilot_smoke", "preliminary_pilot"}:
        raise IntegrityError("Unknown run mode")
    if manifest["mode"].startswith("preliminary") or manifest["mode"] == "diagnostic":
        if manifest.get("main_experiment_allowed") is not False or manifest.get("evaluation_status") != "provisional" or manifest.get("allow_unreviewed") is not True:
            raise IntegrityError("Preliminary status/authorization is inconsistent")
    return manifest, rows


def descriptive(records: list[dict]) -> dict:
    scenarios, complexity, pairs = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in records:
        scenarios[row["scenario_id"]].append(row)
        complexity[(row["scenario_id"], row["complexity"])].append(row)
        pairs[(row["question_id"], row["scenario_id"])].append(row)
    def summarize(rows):
        result = {"trials": len(rows), "correct": sum(r["execution_accuracy"] for r in rows),
                  "execution_accuracy_percent": mean(r["execution_accuracy"] for r in rows) * 100,
                  "execution_status_counts": dict(Counter(r["execution_status"] for r in rows)),
                  "validation_status_counts": dict(Counter(r.get("validation_status", "not_recorded") for r in rows)),
                  "execution_error_code_counts": dict(Counter(str(r["execution_error_code"]) for r in rows if r.get("execution_error_code") is not None))}
        for key in ("inference_latency_ms", "sql_execution_latency_ms", "input_tokens", "output_tokens"):
            values = [r[key] for r in rows if r.get(key) is not None]
            result[key] = {"available": len(values), "missing": len(rows) - len(values),
                           "mean": mean(values) if values else None, "median": median(values) if values else None}
        return result
    return {"by_scenario": [{"scenario_id": s, **summarize(rows)} for s, rows in sorted(scenarios.items())],
            "by_complexity": [{"scenario_id": s, "complexity": c, **summarize(rows)} for (s, c), rows in sorted(complexity.items())],
            "by_question": [{"question_id": q, "scenario_id": s, "repetitions": len(rows),
                             "complexity": rows[0]["complexity"],
                             "correct": sum(r["execution_accuracy"] for r in rows),
                             "execution_accuracy_percent": mean(r["execution_accuracy"] for r in rows) * 100,
                             "outcome_consistent": len({r["execution_accuracy"] for r in rows}) == 1,
                             "unique_extracted_sql": len({r["extracted_sql"] for r in rows if r["extracted_sql"] is not None})}
                            for (q, s), rows in sorted(pairs.items())]}


def csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def cohort_descriptives(records, attributes):
    if set(attributes) != {r["question_id"] for r in records}:
        raise IntegrityError("Question-profile coverage differs from the frozen outcomes")
    output = {}
    for key in ("primary_need", "spider_level", "semantic_family"):
        groups = defaultdict(list)
        for row in records:
            groups[row["scenario_id"], attributes[row["question_id"]][key]].append(row)
        output[key] = [{"scenario_id": scenario, "profile": profile,
                        "questions": len({row["question_id"] for row in rows}), "trials": len(rows),
                        "correct": sum(row["execution_accuracy"] for row in rows),
                        "execution_accuracy_percent": mean(row["execution_accuracy"] for row in rows) * 100}
                       for (scenario, profile), rows in sorted(groups.items())]
    return output


def analyze_run(directory: Path, output: Path) -> dict:
    manifest, rows = audit_run(directory)
    report = {"mode": manifest["mode"], "experiment_id": manifest["experiment_id"], "integrity_verified": True,
              "main_research_results": manifest["mode"] == "main", "descriptive": descriptive(rows)}
    report["evaluation_status"] = manifest.get("evaluation_status", "engineering")
    report["gold_review_status"] = manifest.get("gold_review_status", ["unknown"])
    report["public_results_embargo"] = manifest.get("public_results_embargo", True)
    if manifest.get("review_attestation"):
        report["review_attestation"] = manifest["review_attestation"]
        report["reviewer_identity_status"] = manifest["reviewer_identity_status"]
    events = [json.loads(line) for line in (directory / "events.jsonl").read_bytes().splitlines() if line.strip()]
    incidents = [e for e in events if e["kind"] == "infrastructure_failure"]
    report["infrastructure_accounting"] = {"assigned_trials": len(rows),
        "request_attempts_started": sum(e["kind"] == "request_started" for e in events),
        "infrastructure_incidents": len(incidents),
        "incident_types": dict(Counter(e["payload"].get("error_type", "unknown") for e in incidents)),
        "policy": "Infrastructure incidents remain separate from completed binary EX; stored responses are reused, never semantically repaired."}
    if manifest.get("question_attributes"):
        report["cohort_descriptive"] = cohort_descriptives(rows, manifest["question_attributes"])
    if manifest["mode"] == "diagnostic":
        from .diagnostics import diagnostic_analysis
        report["diagnostic_analysis"] = diagnostic_analysis(rows, seed=manifest["experiment_config"]["analysis_seed"])
    if manifest["mode"] in {"main", "preliminary"}:
        if manifest.get("analysis_protocol_id") == "paired-question-permutation-exact-v2":
            from .exact import paired_analysis_v2 as paired_analysis
        else:
            from .statistics import paired_analysis
        report["paired_analysis"] = paired_analysis(rows, seed=manifest["experiment_config"]["analysis_seed"])
    if manifest["mode"].startswith("preliminary"):
        report["note"] = "PROVISIONAL EX against draft references. External annotation pending. Statistical outputs are exploratory/conditional, not final thesis conclusions. Results remain local."
    elif manifest["mode"] != "main":
        report["note"] = "Engineering pilot only; no inferential tests or thesis metadata-effect conclusions"
    elif manifest.get("evaluation_status") == "user_attested_review":
        report["note"] = "Review completion declared by researcher; reviewer identities/date remain to be supplied. No independent signed-review claim."
    for group in report["descriptive"].values():
        for row in group:
            row["evaluation_status"] = report["evaluation_status"]
    publish_artifact(output / "report.json", canonical_json(report))
    publish_artifact(output / "execution-accuracy.csv", csv_bytes(report["descriptive"]["by_scenario"], ["evaluation_status", "scenario_id", "trials", "correct", "execution_accuracy_percent"]))
    publish_artifact(output / "complexity.csv", csv_bytes(report["descriptive"]["by_complexity"], ["evaluation_status", "scenario_id", "complexity", "trials", "correct", "execution_accuracy_percent"]))
    publish_artifact(output / "questions.csv", csv_bytes(report["descriptive"]["by_question"], ["evaluation_status", "question_id", "scenario_id", "complexity", "repetitions", "correct", "execution_accuracy_percent", "outcome_consistent", "unique_extracted_sql"]))
    measurements = [{"evaluation_status": report["evaluation_status"], "scenario_id": r["scenario_id"], "measurement": key, **r[key]}
                    for r in report["descriptive"]["by_scenario"] for key in ("inference_latency_ms", "sql_execution_latency_ms", "input_tokens", "output_tokens")]
    publish_artifact(output / "measurements.csv", csv_bytes(measurements, ["evaluation_status", "scenario_id", "measurement", "available", "missing", "mean", "median"]))
    for profile, group in report.get("cohort_descriptive", {}).items():
        publish_artifact(output / (profile + ".csv"), csv_bytes(group, ["scenario_id", "profile", "questions", "trials", "correct", "execution_accuracy_percent"]))
    if "paired_analysis" in report:
        contrast_rows = [{"evaluation_status": report["evaluation_status"], **r} for r in report["paired_analysis"]["contrasts"]]
        publish_artifact(output / "paired-contrasts.csv", csv_bytes(contrast_rows, ["evaluation_status", "contrast", "difference_pp", "p_value", "p_value_holm", "confidence_interval_95_pp"]))
        from .figures import plot_statistics, plot_descriptive
        plot_statistics(report["paired_analysis"], output, label="EX pendahuluan — draft gold" if manifest["mode"] == "preliminary" else "Pengaruh kondisi metadata terhadap EX")
        plot_descriptive(report["descriptive"], output, label="Pendahuluan — draft gold" if manifest["mode"] == "preliminary" else "Reviewed benchmark")
    if "diagnostic_analysis" in report:
        publish_artifact(output / "diagnostic-contrasts.csv", csv_bytes(report["diagnostic_analysis"]["contrasts"],
                         ["contrast", "difference_pp", "pointwise_bootstrap_interval_95_pp"]))
    lines = ["# Laporan EX Pendahuluan" if manifest["mode"].startswith("preliminary") else "# Laporan Execution Accuracy", "",
             report.get("note", "Reviewed reference evaluation."), "", f"Experiment: {manifest['experiment_id']}; evaluable trials: {len(rows)}.", "",
             "| Kondisi | Benar | Trial | EX (%) |", "|---|---:|---:|---:|"]
    for row in report["descriptive"]["by_scenario"]:
        lines.append(f"| {row['scenario_id']} | {row['correct']} | {row['trials']} | {row['execution_accuracy_percent']:.2f} |")
    if report.get("cohort_descriptive"):
        lines += ["", "| Kondisi | Kebutuhan informasi | Pertanyaan | Trial | EX (%) |", "|---|---|---:|---:|---:|"]
        for row in report["cohort_descriptive"]["primary_need"]:
            lines.append(f"| {row['scenario_id']} | {row['profile']} | {row['questions']} | {row['trials']} | {row['execution_accuracy_percent']:.2f} |")
        lines += ["", "Profil kebutuhan/keluarga berasal dari instrumen yang dibekukan. Subkelompok bersifat deskriptif, berkaitan dengan complexity, dan bukan tambahan pertanyaan independen."]
    if "diagnostic_analysis" in report:
        lines += ["", "Diagnostik terpisah; bukan perbandingan utama S0–S3. Gold tetap draft.", "",
                  "| Kontras terencana | Selisih EX (pp) | 95% pointwise composition interval (pp) |", "|---|---:|---|"]
        for contrast in report["diagnostic_analysis"]["contrasts"]:
            lines.append(f"| {contrast['contrast']} | {contrast['difference_pp']:.2f} | {contrast['pointwise_bootstrap_interval_95_pp']} |")
        lines += ["", report["diagnostic_analysis"]["limits"]]
    if "paired_analysis" in report:
        stats = report["paired_analysis"]
        lines += ["", "Unit berpasangan adalah pertanyaan; lima pengulangan diagregasi per question–scenario.", "",
                  f"Omnibus paired permutation p={stats['omnibus']['p_value']:.6g}; seed={stats['seed']}.", "",
                  "| Kontras | Selisih EX (pp) | p | p Holm | 95% paired CI (pp) |", "|---|---:|---:|---:|---|"]
        for contrast in stats["contrasts"]:
            lines.append(f"| {contrast['contrast']} | {contrast['difference_pp']:.2f} | {contrast['p_value']:.6g} | {contrast['p_value_holm']:.6g} | {contrast['confidence_interval_95_pp']} |")
        lines += ["", "Nonsignificance does not establish equivalence. Confidence intervals are pointwise. Draft-reference errors can change EX and all derived statistics."]
    publish_artifact(output / "report.md", ("\n".join(lines) + "\n").encode())
    return report
