"""Discover the installed MCP server's actual tools without claiming catalog access."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["DATAHUB_TELEMETRY_ENABLED"] = "false"

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import httpx

ROOT = Path(__file__).resolve().parents[2]


async def main() -> int:
    output = ROOT / "runs/metadata/mcp-tool-inventory.json"
    if output.exists():
        print("MCP tool inventory already exists; refusing to overwrite")
        return 2
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            response = client.get("http://127.0.0.1:18080/health")
            if response.status_code != 200:
                raise RuntimeError("backend_not_healthy")
    except (httpx.HTTPError, RuntimeError):
        print(json.dumps({"status": "blocked_backend_unavailable", "backend_metadata_verified": False,
                          "note": "Installed server tests GMS /config at startup; live MCP discovery requires a running DataHub backend"}))
        return 2
    environment = dict(os.environ)
    environment.update({
        "DATAHUB_GMS_URL": "http://127.0.0.1:18080",
        "TOOLS_IS_MUTATION_ENABLED": "false",
        "DATAHUB_MCP_DOCUMENT_TOOLS_DISABLED": "true",
        "SAVE_DOCUMENT_TOOL_ENABLED": "false",
        "FIELD_DESCRIPTION_LENGTH_LIMIT": "16384",
        "DESCRIPTION_LENGTH_LIMIT": "65536",
        "DATAHUB_TELEMETRY_ENABLED": "false",
    })
    token_path = ROOT / "secrets/datahub_token.txt"
    if token_path.exists():
        environment["DATAHUB_GMS_TOKEN"] = token_path.read_text().strip()
    executable = str(Path(sys.executable).parent / "mcp-server-datahub")
    parameters = StdioServerParameters(command=executable, env=environment)
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.parent / "mcp-server-stderr.log").open("a") as error_log:
        async with asyncio.timeout(45):
            async with stdio_client(parameters, errlog=error_log) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    inventory = []
                    cursor = None
                    while True:
                        listing = await session.list_tools(cursor=cursor)
                        inventory.extend(tool.model_dump(mode="json") for tool in listing.tools)
                        cursor = listing.nextCursor
                        if not cursor:
                            break
    names = sorted(tool["name"] for tool in inventory)
    document = {"server": initialized.serverInfo.model_dump(mode="json"), "protocol_version": initialized.protocolVersion,
                "tools": inventory, "tool_names": names, "backend_metadata_verified": False,
                "note": "Real installed server/SDK stdio discovery only; no catalog metadata or scenario snapshot retrieved"}
    with output.open("x") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": "mcp_protocol_and_tool_discovery_verified", "tool_names": names, "backend_metadata_verified": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as error:
        # Server logs are retained separately; never print a credential-bearing env.
        print(json.dumps({"status": "mcp_discovery_failed", "error_class": type(error).__name__}))
        raise SystemExit(1)

