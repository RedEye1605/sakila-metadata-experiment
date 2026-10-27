"""Compatibility entrypoint; use the parameterized research CLI."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sakila_experiment.cli import main

if __name__ == "__main__":
    raise SystemExit(main(['backend', 'verify'] + sys.argv[1:]))
