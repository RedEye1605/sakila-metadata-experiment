from copy import deepcopy

from sakila_experiment.metadata.ingestion_audit import audit_connector, reconcile_native_types


def fixture():
    audit = {"schema_sha256": "frozen-schema", "technical_schema": {"tables": [{"name": "address", "columns": [{"name": "location", "data_type": "geometry", "nullable": False}], "primary_key": [], "foreign_keys": []}]}}
    schema = {"schemaName": "sakila.address", "fields": [{"fieldPath": "location", "nativeDataType": "BLOB", "nullable": False}]}
    events = [{"proposedSnapshot": {"snapshot": {"urn": "dataset-urn", "aspects": [{"com.linkedin.pegasus2avro.schema.SchemaMetadata": schema}]}}}]
    return events, audit


def test_geometry_fidelity_is_detected_and_reconciled_without_mutating_raw_evidence():
    events, audit = fixture()
    original = deepcopy(events)
    assert audit_connector(events, audit)["errors"] == ["address.location:native_type"]
    updated, receipt = reconcile_native_types(events, audit)
    assert events == original
    assert audit_connector(updated, audit)["status"] == "passed"
    assert receipt["changes"][0]["installed_native_type"] == "geometry"
    assert receipt["validation"]["mcp_snapshot"] is False

