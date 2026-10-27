import copy
import json
from pathlib import Path

import pytest

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.metadata.snapshots import SnapshotError, build_candidate, normalize_export, read_export, validate_scenario_set

ROOT = Path(__file__).resolve().parents[2]


def export_fixture(path, scenario):
    observed = json.loads((ROOT / "tests/fixtures/metadata-live-wire.json").read_bytes())
    spec = json.loads((ROOT / "data/annotations/specification.json").read_bytes())
    elements = {a["element_id"]: a for a in spec["annotations"]}
    datasets, fields = observed["datasets"], observed["fields"]
    names = {urn: e["schemaMetadata"]["name"].rsplit(".", 1)[-1] for urn, e in datasets.items()}
    for urn, entity in datasets.items():
        style = "short" if scenario == "S1" else "detailed"
        entity["editableProperties"]["description"] = elements[names[urn]][style] if scenario != "S0" else ""
        if scenario != "S3":
            entity.pop("glossaryTerms", None)
        for field in fields[urn]:
            field["editedDescription"] = elements[names[urn] + "." + field["fieldPath"]][style] if scenario != "S0" else ""
            if scenario != "S3":
                field.pop("editedGlossaryTerms", None)
                field.pop("glossaryTerms", None)
    bundle = {"scenario_id": scenario, "transport": "stdio", "model_generation_enabled": False,
              "tool_inventory_sha256": publish_artifact(path / "tools.json", canonical_json({})),
              "dataset_urns": sorted(datasets), "term_urns": sorted(observed["terms"]) if scenario == "S3" else [], "calls": []}
    def call(kind, name, args, payload):
        relative = f"calls/{len(bundle['calls'])}.json"
        content = canonical_json({"structuredContent": payload, "isError": False})
        bundle["calls"].append({"kind": kind, "name": name, "arguments": args, "request_sha256": sha256_bytes(canonical_json({"name": name, "arguments": args})),
                                "response_file": relative, "response_sha256": publish_artifact(path / relative, content)})
    call("datasets", "get_entities", {"urns": sorted(datasets)}, {"result": list(datasets.values())})
    for urn, columns in fields.items():
        call("schema_fields", "list_schema_fields", {"urn": urn}, {"urn": urn, "fields": columns})
    if scenario == "S3":
        call("business_terms", "get_entities", {"urns": sorted(observed["terms"])}, {"result": list(observed["terms"].values())})
    publish_artifact(path / "export.json", canonical_json(bundle))
    return observed["audit"], spec


def test_real_wire_schema_descriptions_glossary_and_all_conditions(tmp_path):
    for scenario in ("S0", "S1", "S2", "S3"):
        first, second = tmp_path / (scenario + "-a"), tmp_path / (scenario + "-b")
        audit, spec = export_fixture(first, scenario)
        export_fixture(second, scenario)
        manifest = build_candidate(first, second, audit, spec, tmp_path / "snapshots")
        assert manifest["description_count"] == (0 if scenario == "S0" else 106)
        assert manifest["business_term_count"] == (7 if scenario == "S3" else 0)
    assert validate_scenario_set(tmp_path / "snapshots")["main_experiment_allowed"] is False


def test_mcp_response_tampering_and_path_escape_are_rejected(tmp_path):
    export_fixture(tmp_path, "S0")
    bundle = json.loads((tmp_path / "export.json").read_bytes())
    bundle["calls"][0]["response_file"] = "../outside.json"
    (tmp_path / "export.json").chmod(0o644)
    (tmp_path / "export.json").write_bytes(canonical_json(bundle))
    with pytest.raises(SnapshotError, match="escapes"):
        read_export(tmp_path)


def test_database_schema_cannot_silently_complete_missing_mcp_metadata(tmp_path):
    audit, spec = export_fixture(tmp_path, "S2")
    altered = copy.deepcopy(audit)
    altered["technical_schema"]["tables"][0]["columns"][0]["nullable"] = not altered["technical_schema"]["tables"][0]["columns"][0]["nullable"]
    with pytest.raises(SnapshotError, match="no fallback"):
        normalize_export(tmp_path, altered, spec)


def test_truncation_or_changed_business_binding_is_rejected(tmp_path):
    audit, spec = export_fixture(tmp_path, "S3")
    altered = copy.deepcopy(spec)
    altered["annotations"][0]["detailed"] += " Changed expected description."
    with pytest.raises(SnapshotError, match="truncated"):
        normalize_export(tmp_path, audit, altered)
    altered = copy.deepcopy(spec)
    altered["business_terms"][0]["applies_to"] = []
    with pytest.raises(SnapshotError, match="binding"):
        normalize_export(tmp_path, audit, altered)


def test_independent_export_drift_prevents_publication(tmp_path):
    audit, spec = export_fixture(tmp_path / "first", "S1")
    export_fixture(tmp_path / "second", "S2")
    with pytest.raises(SnapshotError):
        build_candidate(tmp_path / "first", tmp_path / "second", audit, spec, tmp_path / "snapshots")
    assert not (tmp_path / "snapshots").exists()
