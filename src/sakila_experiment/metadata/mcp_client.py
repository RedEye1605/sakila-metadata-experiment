"""Audited MCP-only retrieval using the observed SDK v1.30 wire contracts."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ..artifacts import canonical_json, publish_artifact, sha256_bytes


class MetadataRetrievalError(RuntimeError):
    pass


def unpack_tool_result(result: dict):
    if result.get("isError"):
        raise MetadataRetrievalError("MCP tool returned an error")
    structured = result.get("structuredContent")
    if structured is not None:
        return structured["result"] if isinstance(structured, dict) and set(structured) == {"result"} else structured
    texts = [entry["text"] for entry in result.get("content", []) if entry.get("type") == "text"]
    if len(texts) != 1:
        raise MetadataRetrievalError("Expected one complete JSON text or structured response")
    try:
        return json.loads(texts[0])
    except ValueError:
        raise MetadataRetrievalError("MCP response is not complete JSON") from None


def registry_from_events(events: list[dict]) -> tuple[str, ...]:
    urns = set()
    for event in events:
        for snapshot in event.get("proposedSnapshot", {}).values():
            if any(any(kind.endswith(".SchemaMetadata") for kind in aspect) for aspect in snapshot.get("aspects", [])):
                urns.add(snapshot["urn"])
        if event.get("aspectName") == "schemaMetadata":
            urns.add(event["entityUrn"])
    if not urns:
        raise MetadataRetrievalError("Explicit dataset scope is empty")
    return tuple(sorted(urns))


async def export_metadata(root: Path, scenario: str, destination: Path, *, page_size: int = 100) -> dict:
    # Imported only in the separate metadata tooling environment.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    if scenario not in {"S0", "S1", "S2", "S3"} or page_size < 1:
        raise MetadataRetrievalError("Invalid scenario or pagination configuration")
    if (destination / "export.json").exists():
        raise MetadataRetrievalError("A completed export already exists")
    events_path = root / "runs/metadata/validated-ingestion.json"
    datasets = registry_from_events(json.loads(events_path.read_text()))
    specification = json.loads((root / "data/annotations/specification.json").read_text())
    terms = tuple(sorted(term["urn"] for term in specification["business_terms"])) if scenario == "S3" else ()
    token = (root / "secrets/datahub_token.txt").read_text().strip()
    environment = dict(os.environ)
    environment.update({"DATAHUB_GMS_URL": "http://127.0.0.1:18080", "DATAHUB_GMS_TOKEN": token,
                        "TOOLS_IS_MUTATION_ENABLED": "false", "DATAHUB_MCP_DOCUMENT_TOOLS_DISABLED": "true",
                        "SAVE_DOCUMENT_TOOL_ENABLED": "false", "FIELD_DESCRIPTION_LENGTH_LIMIT": "16384",
                        "DESCRIPTION_LENGTH_LIMIT": "65536", "DATAHUB_TELEMETRY_ENABLED": "false"})
    executable = root / "environments/metadata/.venv/bin/mcp-server-datahub"
    destination.mkdir(parents=True, exist_ok=True)
    calls = []
    with (destination / "server-stderr.log").open("a") as error_log:
        async with asyncio.timeout(300):
            async with stdio_client(StdioServerParameters(command=str(executable), env=environment), errlog=error_log) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    tools = await session.list_tools()
                    listing = {tool.name: tool.model_dump(mode="json") for tool in tools.tools}
                    if not {"get_entities", "list_schema_fields"} <= listing.keys():
                        raise MetadataRetrievalError("Required live tools are missing")
                    inventory_digest = publish_artifact(destination / "tools.json", canonical_json(listing))

                    async def call(name: str, arguments: dict, kind: str):
                        if name not in {"get_entities", "list_schema_fields"}:
                            raise MetadataRetrievalError("Tool is outside the retrieval allowlist")
                        request = {"name": name, "arguments": arguments}
                        relative = f"calls/{len(calls):03d}.json"
                        raw = (await session.call_tool(name, arguments)).model_dump(mode="json")
                        digest = publish_artifact(destination / relative, canonical_json(raw))
                        calls.append({"kind": kind, **request, "request_sha256": sha256_bytes(canonical_json(request)), "response_file": relative, "response_sha256": digest})
                        return unpack_tool_result(raw)

                    entities = await call("get_entities", {"urns": list(datasets)}, "datasets")
                    if not isinstance(entities, list) or {entity.get("urn") for entity in entities} != set(datasets):
                        raise MetadataRetrievalError("Entity response does not cover the fixed dataset scope")
                    for urn in datasets:
                        offset = 0
                        seen = set()
                        while True:
                            page = await call("list_schema_fields", {"urn": urn, "limit": page_size, "offset": offset}, "schema_fields")
                            if not isinstance(page, dict) or page.get("urn") != urn or not isinstance(page.get("fields"), list):
                                raise MetadataRetrievalError("Observed schema page contract changed")
                            returned = page.get("returned")
                            remaining = page.get("remainingCount")
                            if type(returned) is not int or type(remaining) is not int or returned != len(page["fields"]) or page.get("offset") != offset:
                                raise MetadataRetrievalError("Inconsistent pagination counters")
                            fields = [field["fieldPath"] for field in page["fields"]]
                            if seen.intersection(fields) or len(set(fields)) != len(fields):
                                raise MetadataRetrievalError("Duplicate schema fields across pages")
                            seen.update(fields)
                            if not remaining:
                                if len(seen) != page.get("totalFields"):
                                    raise MetadataRetrievalError("Schema field count is incomplete")
                                break
                            if returned < 1:
                                raise MetadataRetrievalError("Pagination made no progress")
                            offset += returned
                    if terms:
                        await call("get_entities", {"urns": list(terms)}, "business_terms")
    bundle = {"export_version": 1, "scenario_id": scenario, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
              "transport": "stdio", "gms_url": "http://127.0.0.1:18080", "server_info": initialized.serverInfo.model_dump(mode="json"),
              "protocol_version": initialized.protocolVersion, "package_versions": {name: importlib.metadata.version(name) for name in ("mcp", "mcp-server-datahub", "fastmcp", "acryl-datahub")},
              "tool_inventory_sha256": inventory_digest, "credential_sha256": sha256_bytes(token.encode()),
              "field_description_length_limit": 16384, "description_length_limit": 65536,
              "dataset_urns": list(datasets), "term_urns": list(terms), "calls": calls,
              "scope_registry_sha256": sha256_bytes(events_path.read_bytes()), "model_generation_enabled": False}
    publish_artifact(destination / "export.json", canonical_json(bundle))
    return bundle

