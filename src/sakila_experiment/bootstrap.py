"""Explicit administrative setup, isolated from untrusted query execution.

Credentials are generated locally and supplied through mounted files or stdin.
This module is never used by the model query executor.
"""

from __future__ import annotations

import io
import json
import os
import re
import secrets
import subprocess
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import canonical_json, publish_artifact, sha256_bytes
from .config import AppConfig, ConfigurationError

CONTAINER = "sakila-research-mysql"
OFFICIAL_ARCHIVE = "https://downloads.mysql.com/docs/sakila-db.tar.gz"


class BootstrapError(RuntimeError):
    """Safe administrative setup failure; never contains SQL or credentials."""


def private_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise BootstrapError("An existing secret file has unsafe permissions")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def run_command(arguments: list[str], *, data: bytes | None = None, timeout: int = 180) -> bytes:
    try:
        result = subprocess.run(arguments, input=data, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BootstrapError("An infrastructure command failed or timed out") from None
    if result.returncode:
        # MySQL errors can echo statements, so do not print captured stderr.
        raise BootstrapError(f"Infrastructure command failed ({arguments[0]} {arguments[1] if len(arguments) > 1 else ''}, exit {result.returncode})")
    return result.stdout


def admin_sql(sql: bytes | str, container_name: str = CONTAINER) -> str:
    return run_command([
        "docker", "exec", "-i", container_name, "mysql",
        "--defaults-extra-file=/run/secrets/admin_client", "--batch", "--raw", "--skip-column-names",
    ], data=sql.encode() if isinstance(sql, str) else sql).decode("utf-8")


def prepare_official_source(config: AppConfig) -> dict:
    destination = config.resolve("downloads/sakila")
    manifest_path = destination / "source-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, digest in manifest["files"].items():
            if sha256_bytes((destination / name).read_bytes()) != digest:
                raise BootstrapError("Cached official source hash mismatch")
        return manifest
    # The official download CDN rejects some custom user-agent strings.
    request = urllib.request.Request(OFFICIAL_ARCHIVE, headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            archive = response.read(16 * 1024 * 1024 + 1)
            final_url = response.url
    except OSError:
        raise BootstrapError("Official Sakila download failed") from None
    if len(archive) > 16 * 1024 * 1024:
        raise BootstrapError("Official archive exceeded the bounded download size")
    files = {"sakila-db.tar.gz": archive}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for name in ("sakila-schema.sql", "sakila-data.sql"):
                member = bundle.getmember("sakila-db/" + name)
                if not member.isfile() or member.size > 64 * 1024 * 1024:
                    raise BootstrapError("Unexpected official source member")
                handle = bundle.extractfile(member)
                if handle is None:
                    raise BootstrapError("Official source member cannot be read")
                files[name] = handle.read()
    except (tarfile.TarError, KeyError):
        raise BootstrapError("Official archive layout is not the expected Sakila distribution") from None
    for name, content in files.items():
        publish_artifact(destination / name, content)
    manifest = {
        "source_url": OFFICIAL_ARCHIVE, "resolved_url": final_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {name: sha256_bytes(content) for name, content in files.items()},
        "policy": "Official SQL files are imported byte-for-byte without modifications",
    }
    publish_artifact(manifest_path, canonical_json(manifest))
    return manifest


def bootstrap_database(config: AppConfig, *, container_name: str = CONTAINER) -> dict:
    standard = container_name == CONTAINER and config.database.port == 13306
    reproduction = bool(re.fullmatch(r"sakila-repro-[a-z0-9-]+-mysql", container_name)) and config.database.port >= 1024 and config.database.port not in {3306, 13306}
    if config.database.host != "127.0.0.1" or config.database.database != "sakila" or not (standard or reproduction):
        raise ConfigurationError("Bootstrap is restricted to the isolated local Sakila topology")
    def execute_admin(sql):
        return admin_sql(sql, container_name)
    manifest_path = config.resolve("runs/database/import-manifest.json")
    secret_dir = config.resolve("secrets")
    private_file(secret_dir / "root_password.txt", secrets.token_hex(32))
    private_file(secret_dir / "reader_password.txt", secrets.token_hex(32))
    private_file(secret_dir / "metadata_password.txt", secrets.token_hex(32))
    root_secret = (secret_dir / "root_password.txt").read_text().strip()
    private_file(secret_dir / "admin-client.cnf", f"[client]\nuser=root\npassword={root_secret}\n")
    source = prepare_official_source(config)
    compose = ["docker", "compose", "-f", str(config.resolve("infra/compose.yaml"))]
    run_command(compose + ["config", "--quiet"])
    print("Starting isolated research MySQL; existing mysql-dev is unchanged", flush=True)
    run_command(compose + ["up", "-d", "--wait", "--wait-timeout", "150"], timeout=180)
    inspection = json.loads(run_command(["docker", "inspect", container_name]))[0]
    mounts = [m for m in inspection["Mounts"] if m["Destination"] == "/run/secrets/admin_client"]
    ports = inspection["NetworkSettings"]["Ports"].get("3306/tcp", [])
    if len(mounts) != 1 or Path(mounts[0]["Source"]).resolve() != (secret_dir / "admin-client.cnf").resolve() or ports != [{"HostIp": "127.0.0.1", "HostPort": str(config.database.port)}]:
        raise BootstrapError("Database container mounts/port differ from this isolated workspace")
    exists = execute_admin("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='sakila';").strip() == "1"
    if exists:
        if not manifest_path.exists():
            raise BootstrapError("Sakila exists without a completed import manifest; refusing to overwrite or repair it automatically")
        recorded = json.loads(manifest_path.read_text())
        if recorded["source"]["files"] != source["files"]:
            raise BootstrapError("Existing import source does not match the cached distribution")
        return {"status": "already_imported", "manifest": str(manifest_path)}
    if manifest_path.exists():
        raise BootstrapError("Import manifest exists but Sakila is missing; refusing an unrecorded reimport")
    source_dir = config.resolve("downloads/sakila")
    print("Importing official Sakila schema and data", flush=True)
    execute_admin((source_dir / "sakila-schema.sql").read_bytes())
    execute_admin((source_dir / "sakila-data.sql").read_bytes())
    names = execute_admin("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='sakila' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME;").splitlines()
    if not names or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names):
        raise BootstrapError("Installed base table inventory is invalid")
    readers = [(config.database.username, "reader_password.txt"), ("metadata_reader", "metadata_password.txt")]
    statements = []
    for username, password_file in readers:
        password = (secret_dir / password_file).read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", password):
            raise BootstrapError("Bootstrap credentials must be locally generated hexadecimal secrets")
        statements.append(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}';")
        for name in names:
            statements.append(f"GRANT SELECT ON `sakila`.`{name}` TO '{username}'@'%';")
    execute_admin("\n".join(statements))
    # Freeze persists across restarts; only this administrative module has root access.
    execute_admin("SET PERSIST read_only=ON; SET PERSIST super_read_only=ON;")
    info = execute_admin("SELECT VERSION(), @@global.read_only, @@global.super_read_only;").strip().split("\t")
    image = json.loads(run_command(["docker", "inspect", container_name, "--format", "{{json .Image}}"]))
    manifest = {
        "manifest_version": 1, "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source, "mysql_version": info[0], "image_id": image,
        "read_only": info[1] == "1", "super_read_only": info[2] == "1",
        "base_tables": names, "reader_account": config.database.username,
        "metadata_account": "metadata_reader", "host_port": config.database.port, "container_name": container_name,
    }
    publish_artifact(manifest_path, canonical_json(manifest))
    return {"status": "imported_and_frozen", "base_table_count": len(names), "mysql_version": info[0], "manifest": str(manifest_path)}

