"""Deterministic snapshots built exclusively from audited MCP response bytes."""

from __future__ import annotations

import json
from pathlib import Path

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from .ingestion_audit import type_signature
from .mcp_client import unpack_tool_result


class SnapshotError(RuntimeError):
    pass


def expected_technical_schema(audit: dict) -> dict:
    tables = []
    for table in audit["technical_schema"]["tables"]:
        keys = [{"name": key["name"], "source_columns": key["source_columns"], "target_table": key["target_table"], "target_columns": key["target_columns"]} for key in table["foreign_keys"]]
        tables.append({"name": table["name"], "columns": [{"name": c["name"], "type": type_signature(c["data_type"]), "nullable": c["nullable"]} for c in sorted(table["columns"], key=lambda c: c["name"])], "primary_key": sorted(table["primary_key"]), "foreign_keys": sorted(keys, key=lambda key: key["name"])})
    return {"database": audit["technical_schema"]["database"], "tables": sorted(tables, key=lambda t: t["name"])}


def read_export(directory: Path) -> tuple[dict, dict, dict, dict]:
    bundle = json.loads((directory / "export.json").read_text())
    if bundle.get("transport") != "stdio" or bundle.get("model_generation_enabled") is not False:
        raise SnapshotError("Export is not from the approved preparation-only MCP transport")
    if sha256_bytes((directory / "tools.json").read_bytes()) != bundle["tool_inventory_sha256"]:
        raise SnapshotError("Live tool inventory hash mismatch")
    datasets, fields, terms = {}, {}, {}
    base = directory.resolve()
    for receipt in bundle["calls"]:
        required_tool = {"datasets": "get_entities", "schema_fields": "list_schema_fields", "business_terms": "get_entities"}.get(receipt["kind"])
        if required_tool is None or receipt["name"] != required_tool:
            raise SnapshotError("Receipt does not use an approved MCP metadata tool")
        path = (directory / receipt["response_file"]).resolve()
        if not path.is_relative_to(base):
            raise SnapshotError("Response path escapes its export directory")
        content = path.read_bytes()
        if sha256_bytes(content) != receipt["response_sha256"]:
            raise SnapshotError("MCP response hash mismatch")
        request = {"name": receipt["name"], "arguments": receipt["arguments"]}
        if sha256_bytes(canonical_json(request)) != receipt["request_sha256"]:
            raise SnapshotError("MCP request hash mismatch")
        payload = unpack_tool_result(json.loads(content))
        if receipt["kind"] == "datasets":
            for entity in payload:
                if entity["urn"] in datasets:
                    raise SnapshotError("Duplicate dataset entity")
                datasets[entity["urn"]] = entity
        elif receipt["kind"] == "schema_fields":
            fields.setdefault(payload["urn"], []).extend(payload["fields"])
        elif receipt["kind"] == "business_terms":
            for entity in payload:
                terms[entity["urn"]] = entity
        else:
            raise SnapshotError("Unexpected retrieval receipt kind")
    if set(datasets) != set(bundle["dataset_urns"]) or set(fields) != set(datasets):
        raise SnapshotError("MCP export does not cover the fixed dataset scope")
    if set(terms) != set(bundle["term_urns"]):
        raise SnapshotError("MCP export does not cover the designated glossary scope")
    for urn, columns in fields.items():
        names = [field["fieldPath"] for field in columns]
        if len(set(names)) != len(names):
            raise SnapshotError("Duplicate column in retrieved pages")
    return bundle, datasets, fields, terms


def normalize_export(directory: Path, audit: dict, specification: dict) -> dict:
    bundle, datasets, fields, terms = read_export(directory)
    if bundle.get("annotation_specification_canonical_sha256", sha256_bytes(canonical_json(specification))) != sha256_bytes(canonical_json(specification)):
        raise SnapshotError("MCP export was retrieved for a different annotation specification")
    scenario = bundle["scenario_id"]
    urn_names = {urn: entity["schemaMetadata"]["name"].rsplit(".", 1)[-1] for urn, entity in datasets.items()}
    database_names = {entity["schemaMetadata"]["name"].rsplit(".", 1)[0] for entity in datasets.values()}
    if len(database_names) != 1:
        raise SnapshotError("Retrieved datasets span unexpected database schemas")
    tables, descriptions = [], []
    assignments = {urn: set() for urn in terms}
    term_names = {}
    for urn, entity in terms.items():
        properties = entity.get("properties", {})
        name, definition = properties.get("name"), properties.get("description")
        if not isinstance(name, str) or not isinstance(definition, str) or name in term_names:
            raise SnapshotError("Glossary names/definitions are missing or ambiguous through MCP")
        term_names[name] = urn
    for urn, entity in sorted(datasets.items(), key=lambda pair: urn_names[pair[0]]):
        table = urn_names[urn]
        metadata = entity["schemaMetadata"]
        columns = []
        for field in sorted(fields[urn], key=lambda f: f["fieldPath"]):
            if type(field.get("nullable")) is not bool or not field.get("nativeDataType"):
                raise SnapshotError("Column technical metadata is incomplete")
            columns.append({"name": field["fieldPath"], "type": type_signature(field["nativeDataType"]), "nullable": field["nullable"]})
            if scenario != "S0":
                description = field.get("editedDescription", field.get("description"))
                if not isinstance(description, str) or not description:
                    raise SnapshotError(f"Missing MCP column description: {table}.{field['fieldPath']}")
                descriptions.append({"target": table + "." + field["fieldPath"], "description": description})
            for term_name in field.get("editedGlossaryTerms", []) + field.get("glossaryTerms", []):
                if term_name not in term_names:
                    raise SnapshotError("An undesignated glossary term entered column context")
                assignments[term_names[term_name]].add(table + "." + field["fieldPath"])
        keys = []
        for key in metadata.get("foreignKeys", []):
            target = key["foreignDataset"]["urn"]
            if target not in urn_names:
                raise SnapshotError("Foreign key references an asset outside the fixed scope")
            keys.append({"name": key["name"], "source_columns": [f["fieldPath"] for f in key["sourceFields"]], "target_table": urn_names[target], "target_columns": [f["fieldPath"] for f in key["foreignFields"]]})
        primary = sorted(field["fieldPath"] for field in fields[urn] if field.get("isPartOfKey", False))
        if metadata.get("primaryKeys") and sorted(metadata["primaryKeys"]) != primary:
            raise SnapshotError("Primary-key representations disagree")
        tables.append({"name": table, "columns": columns, "primary_key": primary, "foreign_keys": sorted(keys, key=lambda k: k["name"])})
        if scenario != "S0":
            description = entity.get("editableProperties", {}).get("description") or entity.get("properties", {}).get("description")
            if not isinstance(description, str) or not description:
                raise SnapshotError(f"Missing MCP table description: {table}")
            descriptions.append({"target": table, "description": description})
        for association in entity.get("glossaryTerms", {}).get("terms", []):
            term_urn = association["term"]["urn"]
            if term_urn not in assignments:
                raise SnapshotError("An undesignated glossary term entered table context")
            assignments[term_urn].add(table)
    technical = {"database": next(iter(database_names)), "tables": tables}
    if technical != expected_technical_schema(audit):
        raise SnapshotError("MCP technical schema differs from installed-schema audit; no fallback enrichment is permitted")
    descriptions.sort(key=lambda item: item["target"])
    if scenario != "S0":
        style = "short" if scenario == "S1" else "detailed"
        expected = [{"target": annotation["element_id"], "description": annotation[style]} for annotation in sorted(specification["annotations"], key=lambda a: a["element_id"])]
        if descriptions != expected:
            actual = {d["target"]: d["description"] for d in descriptions}
            mismatches = [d["target"] for d in expected if actual.get(d["target"]) != d["description"]]
            raise SnapshotError("Descriptions changed or were truncated through MCP: " + ", ".join(mismatches))
    business = []
    if scenario == "S3":
        expected_terms = {term["urn"]: term for term in specification["business_terms"]}
        if terms.keys() != expected_terms.keys():
            raise SnapshotError("Glossary coverage differs from the approved specification")
        for urn, entity in sorted(terms.items()):
            properties = entity["properties"]
            expected = expected_terms[urn]
            if properties["name"] != expected["name"] or properties["description"] != expected["definition"] or assignments[urn] != set(expected["applies_to"]):
                raise SnapshotError("Glossary definition or binding did not survive MCP retrieval")
            business.append({"name": properties["name"], "definition": properties["description"], "applies_to": sorted(assignments[urn])})
    elif terms or any(assignments.values()):
        raise SnapshotError("Business context leaked into a non-business condition")
    return {"technical_schema": technical, "descriptions": descriptions, "business_context": business}


def build_candidate(first_export: Path, second_export: Path, audit: dict, specification: dict, destination: Path) -> dict:
    first = normalize_export(first_export, audit, specification)
    second = normalize_export(second_export, audit, specification)
    if canonical_json(first) != canonical_json(second):
        raise SnapshotError("Consecutive MCP exports differ; catalog is not stable")
    scenario = json.loads((first_export / "export.json").read_text())["scenario_id"]
    if json.loads((second_export / "export.json").read_text())["scenario_id"] != scenario:
        raise SnapshotError("Stability exports belong to different conditions")
    content = canonical_json(first)
    digest = sha256_bytes(content)
    directory = destination / scenario
    publish_artifact(directory / f"{digest}.json", content)
    manifest = {"snapshot_format_version": 1, "snapshot_id": f"candidate-{scenario}-{digest[:16]}", "scenario_id": scenario,
                "snapshot_sha256": digest, "payload_file": f"{digest}.json", "technical_schema_sha256": sha256_bytes(canonical_json(first["technical_schema"])),
                "annotation_spec_sha256": sha256_bytes(canonical_json(specification)), "database_schema_sha256": audit["schema_sha256"],
                "source_exports": [{"path": str(path.resolve()), "sha256": sha256_bytes((path / "export.json").read_bytes())} for path in (first_export, second_export)],
                "provenance": "DataHub catalog retrieved through Model Context Protocol; no direct-API or database completion in snapshot builder",
                "description_count": len(first["descriptions"]), "business_term_count": len(first["business_context"]),
                "status": "candidate", "main_experiment_allowed": False, "two_export_stability_verified": True}
    publish_artifact(directory / "manifest.json", canonical_json(manifest))
    return manifest


def validate_scenario_set(root: Path) -> dict:
    payloads, manifests = {}, {}
    for scenario in ("S0", "S1", "S2", "S3"):
        manifest = json.loads((root / scenario / "manifest.json").read_text())
        content = (root / scenario / manifest["payload_file"]).read_bytes()
        if sha256_bytes(content) != manifest["snapshot_sha256"]:
            raise SnapshotError("Snapshot content changed after publication")
        if manifest.get("scenario_id") != scenario or manifest.get("two_export_stability_verified") is not True:
            raise SnapshotError("Snapshot identity or stability evidence is inconsistent")
        manifests[scenario] = manifest
        payloads[scenario] = json.loads(content)
        payload = payloads[scenario]
        if set(payload) != {"technical_schema", "descriptions", "business_context"}:
            raise SnapshotError("Snapshot contains an unapproved metadata section")
        if sha256_bytes(canonical_json(payload["technical_schema"])) != manifest["technical_schema_sha256"]:
            raise SnapshotError("Technical schema hash does not match its manifest")
        targets = [d["target"] for d in payload["descriptions"]]
        scope = {table["name"] for table in payload["technical_schema"]["tables"]}
        scope.update(table["name"] + "." + column["name"] for table in payload["technical_schema"]["tables"] for column in table["columns"])
        if len(targets) != len(set(targets)) or (scenario != "S0" and set(targets) != scope):
            raise SnapshotError("Annotation coverage is duplicated or incomplete")
        if len(targets) != manifest["description_count"] or len(payload["business_context"]) != manifest["business_term_count"]:
            raise SnapshotError("Manifest annotation counts disagree with the payload")
    for field in ("annotation_spec_sha256", "database_schema_sha256"):
        if len({m[field] for m in manifests.values()}) != 1:
            raise SnapshotError("Scenario manifests refer to different preparation baselines")
    if any(payloads[s]["technical_schema"] != payloads["S0"]["technical_schema"] for s in payloads):
        raise SnapshotError("Technical metadata changed across scenarios")
    if payloads["S0"]["descriptions"] or any(payloads[s]["business_context"] for s in ("S0", "S1", "S2")):
        raise SnapshotError("Unexpected annotation treatment")
    if {d["target"] for d in payloads["S1"]["descriptions"]} != {d["target"] for d in payloads["S2"]["descriptions"]}:
        raise SnapshotError("Short/detailed annotation coverage differs")
    if payloads["S2"]["descriptions"] != payloads["S3"]["descriptions"]:
        raise SnapshotError("S3 changed existing S2 descriptions")
    if not payloads["S3"]["business_context"]:
        raise SnapshotError("S3 lacks business context")
    return {"status": "candidate_set_validated", "technical_schema_sha256": manifests["S0"]["technical_schema_sha256"],
            "snapshot_sha256": {s: m["snapshot_sha256"] for s, m in manifests.items()}, "main_experiment_allowed": False}


def validate_mcp_provenance(project_root: Path, directory: Path, specification: dict, audit: dict) -> None:
    """Recheck actual paired MCP receipts, not just a provenance status flag."""
    manifest = json.loads((directory / "manifest.json").read_bytes())
    content = (directory / manifest["payload_file"]).read_bytes()
    if sha256_bytes(content) != manifest["snapshot_sha256"]:
        raise SnapshotError("Snapshot content changed")
    if manifest["annotation_spec_sha256"] != sha256_bytes(canonical_json(specification)):
        raise SnapshotError("Snapshot provenance belongs to another authoring specification")
    sources = manifest.get("source_exports", [])
    if len(sources) != 2 or len({source["path"] for source in sources}) != 2:
        raise SnapshotError("Two distinct audited MCP exports are required")
    for source in sources:
        folder = Path(source["path"]).resolve()
        if not folder.is_relative_to(project_root.resolve()):
            raise SnapshotError("Local MCP provenance escapes the project")
        if sha256_bytes((folder / "export.json").read_bytes()) != source["sha256"]:
            raise SnapshotError("MCP source export changed")
        if canonical_json(normalize_export(folder, audit, specification)) != content:
            raise SnapshotError("Snapshot is not the normalized content of its MCP export")

