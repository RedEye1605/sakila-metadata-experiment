"""Check resource separation before starting the pinned local inference server."""
import argparse
import json
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-file", type=Path, default=ROOT / "infra/inference/compose.coder7b.yaml")
    args = parser.parse_args()
    memory = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")}
    if memory["MemAvailable"] < 7 * 1024 ** 3:
        raise SystemExit("Need at least 7 GiB MemAvailable before starting inference")
    active = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], check=True, capture_output=True, text=True).stdout.splitlines()
    if any("datahub" in name.lower() for name in active):
        raise SystemExit("Stop the research DataHub services before local inference")
    print(json.dumps({"precheck": "passed", "available_ram_gib": round(memory["MemAvailable"] / 1024 ** 3, 2)}), flush=True)
    subprocess.run(["docker", "compose", "-f", str(args.compose_file), "up", "-d"], check=True, cwd=ROOT)
    deadline = time.monotonic() + 180
    with httpx.Client(timeout=3, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get("http://127.0.0.1:18081/health")
                if response.status_code == 200:
                    print("Pinned local inference server is healthy", flush=True); return
            except httpx.HTTPError:
                pass
            time.sleep(2)
    raise SystemExit("Inference server did not become healthy; inspect local container logs")


if __name__ == "__main__":
    main()
