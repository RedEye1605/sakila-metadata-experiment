"""Audit the Git index for private artifacts and credential signatures.

Print file names and rule names only, never matching secret text. Scientific
embargo review of narrative claims is performed separately before publication.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ("runs/", "secrets/", "downloads/", "reports/local/", "docs/private/", "annotations/submissions/", "annotations/identities/")
SIGNATURES = {
    "github_token": rb"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "github_fine_grained_token": rb"\bgithub_pat_[A-Za-z0-9_]{30,}",
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
}


def audit():
    names = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.split(b"\0")
    problems, checked = [], 0
    for raw in names:
        if not raw: continue
        path = raw.decode()
        if path.startswith(PRIVATE) or path.endswith(".gguf") or (Path(path).name.startswith(".env") and Path(path).name != ".env.example"):
            problems.append({"path": path, "rule": "private_artifact"}); continue
        result = subprocess.run(["git", "show", ":" + path], cwd=ROOT, capture_output=True)
        if result.returncode: continue  # staged deletion
        checked += 1
        for name, pattern in SIGNATURES.items():
            if re.search(pattern, result.stdout): problems.append({"path": path, "rule": name})
    print(json.dumps({"status": "passed" if not problems else "rejected", "staged_files_checked": checked, "problems": problems}))
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(audit())
