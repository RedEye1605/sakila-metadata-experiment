"""Publish an explicitly authorized, credential-checked thesis/evidence bundle.

Copies immutable artifacts; never invokes inference, MySQL or metadata services.
The completed run remains unchanged. SQLite backup captures its WAL consistently.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sakila_experiment.analysis.report import audit_run
from sakila_experiment.artifacts import canonical_json

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/qwen35-9b/main-01"
OUT = ROOT / "reports/qwen35-9b-main-01"
STATEMENT = "eh ini saya mau pindah windows buat ngerjai skripsinya, jadi tolong laporan bab iv-v dan lain lainnya yang mungkin berguna di commit dan push aja, annti saya sendiri kalau sudah selesai bakal hapus. tapi ini commit dan push aja yang berguna nanti buat saya kasih ke agent baru yang bakal ngerjai skrpsi saya jadi dia paham apa saja yang mau di tulis."
SIGNATURES = {
    "github_token": rb"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "github_fine_grained_token": rb"\bgithub_pat_[A-Za-z0-9_]{30,}",
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "jwt": rb"\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def secret_values() -> list[bytes]:
    values = []
    for path in (ROOT / "secrets").rglob("*"):
        if path.is_file() and path.stat().st_size <= 16384:
            data = path.read_bytes().strip()
            if 12 <= len(data) <= 4096 and b"\n" not in data:
                values.append(data)
    return values


def safe_path(name: str) -> None:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("Unsafe publication path: " + name)
    if any(part in {"secrets", ".venv", ".git", "downloads"} or part.startswith(".env") for part in path.parts):
        raise ValueError("Private publication path: " + name)
    if path.suffix in {".gguf", ".pem", ".key"}:
        raise ValueError("Private publication file type: " + name)
    reserved = {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}
    if any(re.search(r'[<>:"|?*]', part) or part.endswith((".", " ")) or Path(part).stem.upper() in reserved for part in path.parts):
        raise ValueError("Not a portable Windows path: " + name)


def safe_content(name: str, data: bytes, secrets: list[bytes]) -> None:
    for rule, pattern in SIGNATURES.items():
        if re.search(pattern, data):
            raise ValueError(f"Credential signature in {name}: {rule}")
    if any(value in data for value in secrets):
        raise ValueError("Local credential value found in " + name)


def main():
    manifest, rows = audit_run(RUN / "benchmark")
    if len(rows) != 600 or manifest["experiment_id"] != "qwen35-9b-main-01":
        raise ValueError("Only the completed selected main run can enter this bundle")
    secrets = secret_values()
    provenance = {}

    def copy(source: Path, destination: str):
        safe_path(destination)
        data = source.read_bytes()
        safe_content(destination, data, secrets)
        target = OUT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Refusing to overwrite different original evidence: " + destination)
        target.write_bytes(data)
        provenance[destination] = {"kind": "byte_identical_copy", "source_repository_path": str(source.relative_to(ROOT)), "source_sha256": digest(data)}

    for directory in ("thesis", "analysis"):
        for source in sorted((RUN / directory).rglob("*")):
            if source.is_file():
                copy(source, str(source.relative_to(RUN)))
    input_names = {"questions": "questions.jsonl", "gold": "gold.jsonl", "contracts": "contracts.jsonl",
        "annotation_specification": "annotations.json", "fact_inventory": "facts.json", "prompt_template": "generation-instruction.txt",
        "execution_review": "review-attestation.json", "execution_amendment": "execution-amendment.json",
        "reference_validation": "reference-validation-summary.json", "reference_validation_lock": "reference-validation-lock.json",
        "information_audit": "information-audit.json", "selection_receipt": "selection-receipt.json"}
    for name, destination in input_names.items():
        copy(ROOT / manifest["instrument_paths"][name], "inputs/" + destination)
    for source, destination in {
        "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md",
        "configs/models/qwen35-9b-q4km.json": "inputs/model-spec.json",
        "configs/qwen35-9b-main.toml": "inputs/configuration.toml",
        "infra/inference/compose.qwen35-9b.yaml": "inputs/inference-compose.yaml",
        "data/benchmarks/revision-03/qwen35-9b-execution-01/manifest.json": "inputs/instrument-manifest.json",
        "docs/revision-03/analysis-plan.md": "methods/analysis-plan.md",
        "docs/revision-03/evaluation-protocol.md": "methods/evaluation-protocol.md",
        "docs/revision-02/dataset-methodology.md": "methods/dataset-methodology.md",
        "research/revision-02/spider-source-lock.json": "methods/spider-source-lock.json",
        "research/revision-03/evaluator-source-lock.json": "methods/evaluator-source-lock.json",
        "research/revision-03/fixture_cases.json": "methods/fixture-cases.json",
        "data/benchmarks/revision-03/mutations.json": "methods/semantic-mutants.json",
        "runs/database/baseline.json": "evidence/database-baseline.json",
        "runs/database/import-manifest.json": "evidence/sakila-import.json",
        "runs/metadata/runtime-images.json": "evidence/metadata-runtime-images.json",
        "runs/qwen35-9b/checks/launch-verified.xml": "evidence/prelaunch-tests.xml",
        "runs/revision-03/main-01/analysis/report.md": "history/qwen25-coder-7b-main/report.md",
        "runs/revision-03/main-01/analysis/report.json": "history/qwen25-coder-7b-main/report.json",
        "runs/model-selection/qwen3-8b-01/readout.md": "history/qwen3-8b-capability-pilot/readout.md",
        "runs/model-selection/qwen3-8b-01/capability-decision.json": "history/qwen3-8b-capability-pilot/capability-decision.json",
        "runs/model-selection/qwen3-8b-01/completion.json": "history/qwen3-8b-capability-pilot/completion.json",
    }.items():
        copy(ROOT / source, destination)
    for source in sorted((ROOT / "runs/revision-02/metadata/preparation-03/snapshots").rglob("*.json")):
        copy(source, "inputs/snapshots/" + str(source.relative_to(ROOT / "runs/revision-02/metadata/preparation-03/snapshots")))
    for source, destination in {
        "benchmark/manifest.json": "evidence/main-manifest.json", "benchmark/plan.json": "evidence/main-plan.json",
        "benchmark/freeze.json": "evidence/main-freeze.json", "benchmark/completion.json": "evidence/main-completion.json",
        "benchmark/trials.jsonl": "evidence/main-trials.jsonl", "auxiliary/report.json": "evidence/auxiliary-report.json",
        "auxiliary/plan.json": "evidence/auxiliary-plan.json", "pipeline-completion.json": "evidence/pipeline-completion.json",
        "primary-completion.json": "evidence/primary-completion.json", "backend/verification.json": "evidence/backend-verification.json",
        "backend/chat-template.jinja": "evidence/chat-template.jinja", "download.json": "evidence/model-download.json",
    }.items():
        copy(RUN / source, destination)
    for base, destination in [(RUN / "postrun-independent-audit-01", "evidence/postrun-audit"),
                              (ROOT / "runs/qwen35-9b/prelaunch-audit-01", "evidence/prelaunch-audit")]:
        for source in base.iterdir():
            if source.is_file(): copy(source, destination + "/" + source.name)
    for source in RUN.glob("post-completion-database-check*.json"):
        copy(source, "evidence/" + source.name)

    authorization = {"status": "researcher_authorized_public_writing_bundle", "source": "direct_user_statement", "statement": STATEMENT,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "reports/qwen35-9b-main-01 including measured reports, thesis, figures and curated raw evidence",
        "supersedes_for_export": "Historical local_only/public_results_embargo flags remain unchanged in original manifests; this later authorization permits this curated export.",
        "credentials_and_model_weights": "excluded", "new_human_review_claimed": False, "generation_requests_added": 0}
    auth_path = OUT / "PUBLICATION_AUTHORIZATION.json"
    if auth_path.exists(): authorization["recorded_at_utc"] = json.loads(auth_path.read_bytes())["recorded_at_utc"]
    auth_path.write_bytes(canonical_json(authorization))

    selected = {}
    for relative in ["runs/qwen35-9b/main-01/benchmark", "runs/qwen35-9b/main-01/auxiliary",
                     "runs/qwen35-9b/reference-checks-01", "runs/revision-02/metadata/preparation-03",
                     "runs/revision-03/independent-review-01"]:
        for source in (ROOT / relative).rglob("*"):
            if source.is_file() and source.suffix in {".json", ".jsonl", ".sha256"}:
                selected[str(source.relative_to(ROOT))] = source
    for relative in ["runs/revision-03/reference-checks-02/summary.json", "runs/revision-03/reference-checks-02/input-lock.json",
                     "runs/revision-03/main-01/benchmark/manifest.json"]:
        selected[relative] = ROOT / relative
    archive_path = OUT / "evidence/frozen-run-evidence.zip"
    archive_entries = {}
    folded_paths = [name.casefold() for name in selected]
    if len(folded_paths) != len(set(folded_paths)):
        raise ValueError("Case-insensitive Windows archive path collision")
    with tempfile.TemporaryDirectory(prefix="sakila-publication-") as temporary:
        backup = Path(temporary) / "ledger.sqlite3"
        source_connection = sqlite3.connect((RUN / "benchmark/ledger.sqlite3").as_uri() + "?mode=ro", uri=True)
        destination_connection = sqlite3.connect(backup)
        try: source_connection.backup(destination_connection)
        finally:
            destination_connection.close(); source_connection.close()
        selected["runs/qwen35-9b/main-01/benchmark/ledger.sqlite3"] = backup
        staged_archive = Path(temporary) / "evidence.zip"
        with zipfile.ZipFile(staged_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, source in sorted(selected.items()):
                safe_path(name); data = source.read_bytes(); safe_content(name, data, secrets)
                item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, data, compresslevel=6)
                archive_entries[name] = {"sha256": digest(data), "size_bytes": len(data),
                    "kind": "consistent_sqlite_backup" if source == backup else "byte_identical_copy"}
            content = canonical_json({"entries": archive_entries, "generation_requests_added": 0,
                "sqlite_backup": "Logical snapshot including committed WAL; original ledger/WAL are not modified or claimed byte-identical."})
            item = zipfile.ZipInfo("ARCHIVE_INDEX.json", (1980, 1, 1, 0, 0, 0)); item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, content, compresslevel=6)
        if staged_archive.stat().st_size >= 50 * 2**20:
            raise ValueError("Evidence archive exceeds the publication size budget")
        archive_path.write_bytes(staged_archive.read_bytes())

    entries = {}
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name == "PACKAGE_MANIFEST.json": continue
        name = str(path.relative_to(OUT)); safe_path(name); data = path.read_bytes()
        if path != archive_path: safe_content(name, data, secrets)
        entries[name] = {"sha256": digest(data), "size_bytes": len(data), **provenance.get(name, {"kind": "publication_document"})}
    casefolded = [name.casefold() for name in entries]
    if len(set(casefolded)) != len(casefolded): raise ValueError("Case-insensitive Windows path collision")
    package = {"package_version": 1, "experiment_id": manifest["experiment_id"], "experiment_source_commit": manifest["source_version"]["git_commit"],
        "main_manifest_sha256": digest((RUN / "benchmark/manifest.json").read_bytes()), "files": entries,
        "archive": {"path": str(archive_path.relative_to(OUT)), "entries": len(archive_entries), "uncompressed_bytes": sum(x["size_bytes"] for x in archive_entries.values())},
        "contains_credentials_or_model_weights": False, "generation_requests_added": 0,
        "security_check": "All plaintext and archive entries scanned for credential signatures and locally stored credential values; no matching secret values printed."}
    (OUT / "PACKAGE_MANIFEST.json").write_bytes(canonical_json(package))
    print(json.dumps({"status": "curated_windows_bundle_exported", "files": len(entries), "archive_entries": len(archive_entries),
                      "archive_bytes": archive_path.stat().st_size, "generation_requests_added": 0}, indent=2))


if __name__ == "__main__": main()
