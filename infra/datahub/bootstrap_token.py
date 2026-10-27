"""Bootstrap a local preparation PAT via the authenticated frontend session.

The built-in local account belongs to this isolated research catalog. Token
content and session cookies are never printed or included in tracked files.
"""

from __future__ import annotations

import hashlib
import json
import os
import argparse
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renew", action="store_true", help="Rotate the one-hour preparation token; preserve an audit hash of its predecessor")
    args = parser.parse_args(argv)
    path = ROOT / "secrets/datahub_token.txt"
    if path.exists() and not args.renew:
        print(json.dumps({"status": "credential_file_already_exists", "note": "No token was replaced"}))
        return 0
    previous_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    with httpx.Client(timeout=30, trust_env=False) as client:
        login = client.post("http://127.0.0.1:19002/logIn", json={"username": "datahub", "password": "datahub"})
        if login.status_code != 200:
            print(json.dumps({"status": "frontend_login_failed", "http_status": login.status_code}))
            return 1
        mutation = 'mutation { createAccessToken(input: { type: PERSONAL, actorUrn: "urn:li:corpuser:datahub", duration: ONE_HOUR, name: "sakila-metadata-preparation" }) { accessToken } }'
        response = client.post("http://127.0.0.1:19002/api/v2/graphql", json={"query": mutation, "variables": {}})
        body = {}
        try:
            body = response.json()
            token = body.get("data", {}).get("createAccessToken", {}).get("accessToken")
        except (ValueError, AttributeError):
            token = None
        if response.status_code != 200 or not isinstance(token, str) or not token:
            print(json.dumps({"status": "token_creation_failed", "http_status": response.status_code, "graphql_errors_present": isinstance(body, dict) and bool(body.get("errors"))}))
            return 1
        probe = client.post("http://127.0.0.1:18080/api/graphql", headers={"Authorization": "Bearer " + token}, json={"query": "query { __typename }"})
        if probe.status_code != 200:
            print(json.dumps({"status": "gms_credential_probe_failed", "http_status": probe.status_code}))
            return 1
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".datahub-token-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(token)
            handle.flush()
            os.fsync(handle.fileno())
        if args.renew:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    stamp = datetime.now(timezone.utc)
    report = {"created_at_utc": stamp.isoformat(), "duration": "ONE_HOUR", "actor_urn": "urn:li:corpuser:datahub", "token_sha256": hashlib.sha256(token.encode()).hexdigest(), "previous_token_sha256": previous_hash, "credential_file": "secrets/datahub_token.txt", "gms_authenticated": True}
    destination = ROOT / ("runs/metadata/token-bootstrap-" + stamp.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": "preparation_token_created", "gms_authenticated": True, "token_printed": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPError:
        print(json.dumps({"status": "authentication_service_unavailable"}))
        raise SystemExit(1)

