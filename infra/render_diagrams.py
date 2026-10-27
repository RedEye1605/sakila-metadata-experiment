"""Render versioned Mermaid sources to SVG and PNG with pinned local tooling."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    cli = ROOT / "tools/diagrams/node_modules/.bin/mmdc"
    for source in sorted((ROOT / "docs/figures/source").glob("*.mmd")):
        for extension in ("svg", "png"):
            subprocess.run([str(cli), "-i", str(source), "-o", str(ROOT / "docs/figures" / (source.stem + "." + extension)),
                            "-t", "neutral", "-b", "white", "--size", "1800", "-s", "2",
                            "--puppeteerConfigFile", str(ROOT / "tools/diagrams/puppeteer.json")], check=True)


if __name__ == "__main__":
    main()
