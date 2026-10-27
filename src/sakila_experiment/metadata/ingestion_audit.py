"""Audit real connector diagnostics without mislabeling them as MCP snapshots."""

from __future__ import annotations

from copy import deepcopy

from sqlglot import exp

from ..artifacts import canonical_json, sha256_bytes


def type_signature(value: str) -> str:
    return exp.DataType.build(value, dialect="mysql").sql(dialect="mysql")


def connector_schemas(events: list[dict]) -> dict[str, dict]:
    schemas = {}
    for event in events:
        for snapshot in event.get("proposedSnapshot", {}).values():
            for aspect in snapshot.get("aspects", []):
                for kind, value in aspect.items():
                    if kind.endswith(".SchemaMetadata"):
                        schemas[snapshot["urn"]] = value
        if event.get("aspectName") == "schemaMetadata":
            schemas[event["entityUrn"]] = event["aspect"]["json"]
    return schemas


def audit_connector(events: list[dict], database_audit: dict) -> dict:
    schemas = connector_schemas(events)
    actual = {schema["schemaName"].split(".")[-1]: schema for schema in schemas.values()}
    expected = {table["name"]: table for table in database_audit["technical_schema"]["tables"]}
    errors = []
    if actual.keys() != expected.keys():
        errors.append("base_table_coverage_mismatch")
    for name in actual.keys() & expected.keys():
        fields = {field["fieldPath"]: field for field in actual[name]["fields"]}
        columns = {column["name"]: column for column in expected[name]["columns"]}
        if fields.keys() != columns.keys():
            errors.append(f"{name}:column_coverage")
        for column in fields.keys() & columns.keys():
            if type_signature(fields[column]["nativeDataType"]) != type_signature(columns[column]["data_type"]):
                errors.append(f"{name}.{column}:native_type")
            if fields[column]["nullable"] != columns[column]["nullable"]:
                errors.append(f"{name}.{column}:nullability")
        if {f["fieldPath"] for f in fields.values() if f.get("isPartOfKey")} != set(expected[name]["primary_key"]):
            errors.append(f"{name}:primary_key_members")
        actual_keys = {key["name"]: key for key in actual[name].get("foreignKeys", [])}
        expected_keys = {key["name"]: key for key in expected[name]["foreign_keys"]}
        if actual_keys.keys() != expected_keys.keys():
            errors.append(f"{name}:foreign_key_coverage")
        for key in actual_keys.keys() & expected_keys.keys():
            source = [field.rsplit(",", 1)[-1][:-1] for field in actual_keys[key]["sourceFields"]]
            target = [field.rsplit(",", 1)[-1][:-1] for field in actual_keys[key]["foreignFields"]]
            target_table = actual_keys[key]["foreignDataset"].split(",")[-2].split(".")[-1]
            reference = expected_keys[key]
            if source != reference["source_columns"] or target != reference["target_columns"] or target_table != reference["target_table"]:
                errors.append(f"{name}.{key}:foreign_key_mapping")
    return {"status": "passed" if not errors else "failed", "errors": sorted(errors),
            "base_tables": len(actual), "columns": sum(len(s["fields"]) for s in actual.values()),
            "foreign_keys": sum(len(s.get("foreignKeys", [])) for s in actual.values()),
            "mcp_snapshot": False, "catalog_ingestion_verified": False,
            "provenance": "Real MySQL connector file output compared against direct installed-schema audit"}


def reconcile_native_types(events: list[dict], database_audit: dict) -> tuple[list[dict], dict]:
    """Correct reflection loss before catalog ingestion, with an explicit receipt.

    No snapshot builder consumes this database audit. The corrected metadata must
    first be persisted in DataHub and later retrieved independently through MCP.
    """
    before = audit_connector(events, database_audit)
    if any(not error.endswith(":native_type") for error in before["errors"]):
        raise ValueError("Non-type connector mismatch requires a separate reviewed fix")
    updated = deepcopy(events)
    schemas = connector_schemas(updated)
    expected = {table["name"]: table for table in database_audit["technical_schema"]["tables"]}
    changes = []
    for urn, schema in schemas.items():
        table = schema["schemaName"].split(".")[-1]
        columns = {column["name"]: column for column in expected[table]["columns"]}
        for field in schema["fields"]:
            installed = columns[field["fieldPath"]]["data_type"]
            if type_signature(field["nativeDataType"]) != type_signature(installed):
                changes.append({"urn": urn, "column": field["fieldPath"], "connector_native_type": field["nativeDataType"], "installed_native_type": installed})
                field["nativeDataType"] = installed
    after = audit_connector(updated, database_audit)
    if after["status"] != "passed":
        raise ValueError("Reconciled connector output still differs from installed schema")
    receipt = {"receipt_version": 1, "input_sha256": sha256_bytes(canonical_json(events)),
               "output_sha256": sha256_bytes(canonical_json(updated)),
               "database_schema_sha256": database_audit["schema_sha256"], "changes": changes,
               "validation": after,
               "purpose": "Explicit ingestion fidelity reconciliation before DataHub catalog persistence; not an MCP scenario snapshot"}
    return updated, receipt


