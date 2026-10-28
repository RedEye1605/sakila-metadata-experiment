"""Apply authoring specs to DataHub; snapshot retrieval remains MCP-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

os.environ["DATAHUB_TELEMETRY_ENABLED"] = "false"
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import AuditStampClass, EditableDatasetPropertiesClass, EditableSchemaMetadataClass, EditableSchemaFieldInfoClass, GlossaryTermInfoClass, GlossaryTermsClass, GlossaryTermAssociationClass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sakila_experiment.artifacts import canonical_json, publish_artifact
from sakila_experiment.metadata.mcp_client import registry_from_events


def apply(scenario: str, receipt: Path | None = None, specification_path: Path | None = None) -> dict:
    receipt = receipt or ROOT / f"runs/metadata/annotation-writes/{scenario}.json"
    if receipt.exists():
        raise FileExistsError("Annotation receipt already exists; use a new --receipt path before changing the catalog")
    spec_path = specification_path or ROOT / "data/annotations/specification.json"
    specification = json.loads(spec_path.read_text())
    registry = registry_from_events(json.loads((ROOT / "runs/metadata/validated-ingestion.json").read_text()))
    by_table = {urn.split(",")[-2].split(".")[-1]: urn for urn in registry}
    elements = {entry["element_id"]: entry for entry in specification["annotations"]}
    audit = AuditStampClass(time=int(time.time() * 1000), actor="urn:li:corpuser:datahub")
    associations = {element: [] for element in elements}
    token = (ROOT / "secrets/datahub_token.txt").read_text().strip()
    emitter = DatahubRestEmitter(gms_server="http://127.0.0.1:18080", token=token)
    emitted = []

    def emit(urn, aspect):
        proposal = MetadataChangeProposalWrapper(entityUrn=urn, aspect=aspect)
        emitter.emit_mcp(proposal, async_flag=False)
        emitted.append({"urn": urn, "aspect": aspect.get_aspect_name(), "aspect_sha256": hashlib.sha256(canonical_json(aspect.to_obj())).hexdigest()})

    if scenario == "S3":
        for term in specification["business_terms"]:
            emit(term["urn"], GlossaryTermInfoClass(definition=term["definition"], termSource="INTERNAL", name=term["name"], sourceUrl=term["sources"][0]))
            for target in term["applies_to"]:
                associations[target].append(GlossaryTermAssociationClass(urn=term["urn"], actor="urn:li:corpuser:datahub"))
    style = None if scenario == "S0" else "short" if scenario == "S1" else "detailed"
    for table in sorted(by_table):
        urn = by_table[table]
        table_terms = GlossaryTermsClass(terms=associations[table], auditStamp=audit)
        emit(urn, EditableDatasetPropertiesClass(description=elements[table][style] if style else None))
        emit(urn, table_terms)
        fields = []
        for identity, annotation in sorted(elements.items()):
            if annotation["table"] == table and annotation["kind"] == "column":
                fields.append(EditableSchemaFieldInfoClass(fieldPath=annotation["column"], description=annotation[style] if style else None,
                                                          glossaryTerms=GlossaryTermsClass(terms=associations[identity], auditStamp=audit)))
        emit(urn, EditableSchemaMetadataClass(editableSchemaFieldInfo=fields))
    report = {"scenario_id": scenario, "annotation_spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
              "specification_version": specification["specification_version"], "catalog_written_at_utc": datetime.now(timezone.utc).isoformat(),
              "actor_urn": "urn:li:corpuser:datahub", "credential_sha256": hashlib.sha256(token.encode()).hexdigest(),
              "description_style": style, "annotation_elements": len(elements), "business_terms": len(specification["business_terms"]) if scenario == "S3" else 0,
              "writes": emitted, "note": "SDK metadata administration only; experimental snapshot content must be retrieved independently through MCP"}
    publish_artifact(receipt, canonical_json(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=("S0", "S1", "S2", "S3"))
    parser.add_argument("--receipt", type=Path, help="New immutable receipt path when intentionally rebuilding a condition")
    parser.add_argument("--spec", type=Path, help="Explicit versioned authoring specification; default preserves the original")
    args = parser.parse_args()
    report = apply(args.scenario, args.receipt, args.spec)
    print(json.dumps({"status": "catalog_annotations_applied", "scenario": args.scenario, "aspect_writes": len(report["writes"])}))

