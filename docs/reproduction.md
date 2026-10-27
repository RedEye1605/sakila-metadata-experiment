# Instalasi ulang dan tingkat reproduksi

Pilih source commit pada manifest, Python 3.12 dan lockfiles yang sama. Jalankan dari repository root pada host terisolasi. Source publik tidak mengandung credentials, raw runtime receipts atau weights; file tersebut harus dihasilkan kembali atau disediakan melalui arsip bukti yang diaudit. Jangan menjalankan setup terhadap database pengguna yang sudah ada.

## Runtime dan database

```bash
uv sync --frozen --group analysis
uv run --frozen sakila-experiment doctor --offline --output runs/environment/rebuild.json
uv run --frozen --group analysis pytest -q
uv run --frozen sakila-experiment database bootstrap
uv run --frozen sakila-experiment database inspect --output runs/database/baseline.json
uv run --frozen --group analysis pytest -q --run-integration
```

Bootstrap membuat private credentials, mengunduh official Sakila, memverifikasi sumber dan mengimpor SQL byte-for-byte ke port 13306. Baseline dicatat dari instance, bukan dibuat dari snapshot. Bandingkan source/schema/data hashes jika mengulang run historis; official download versi berbeda tidak otomatis ekuivalen.

## Fresh DataHub preparation

Pastikan RAM memadai dan inference berhenti. Perintah berikut untuk **workspace baru**; default receipts menolak overwrite. Untuk workspace lama, gunakan artifact version baru dan perhatikan dependensi path pada scripts.

```bash
uv sync --frozen --project environments/metadata
uv run --frozen --project environments/metadata python infra/datahub/prepare.py
docker compose --env-file secrets/datahub.env -f infra/datahub/compose.yaml --profile quickstart up -d --wait --wait-timeout 600
uv run --frozen python infra/datahub/bootstrap_token.py
uv run --frozen --project environments/metadata python infra/datahub/check_ingestion.py
uv run --frozen sakila-experiment metadata reconcile --events runs/metadata/connector-diagnostic.json --audit runs/database/baseline.json --output-directory runs/metadata
uv run --frozen --project environments/metadata python infra/datahub/ingest_catalog.py
uv run --frozen --project environments/metadata python infra/datahub/mcp_inventory.py
```

Native-type reconciliation dipublikasikan ke catalog **sebelum** retrieval MCP. Snapshot builder tetap menolak metadata berbeda dan tidak menambalnya dari MySQL. Ketidakcocokan versi/field adalah blocker terbuka, bukan alasan mengganti protokol diam-diam.

Manifest membutuhkan `runs/metadata/runtime-images.json`. Contoh berikut mengambil field terbatas dari research containers, termasuk yang stopped, tanpa menyimpan Env/secrets. Flag Compose telah diperiksa pada versi terpasang.

```bash
uv run --frozen python - <<'PY'
import json
import subprocess
from pathlib import Path

compose = ["docker", "compose", "--env-file", "secrets/datahub.env",
           "-f", "infra/datahub/compose.yaml", "--profile", "quickstart"]
containers = subprocess.run(compose + ["ps", "--all", "--quiet"],
                            check=True, capture_output=True, text=True).stdout.split()
if not containers:
    raise SystemExit("No research DataHub containers found")
records = {}
for container_id in containers:
    container = json.loads(subprocess.run(["docker", "inspect", container_id],
                           check=True, capture_output=True, text=True).stdout)[0]
    image = json.loads(subprocess.run(["docker", "image", "inspect", container["Image"]],
                       check=True, capture_output=True, text=True).stdout)[0]
    records[container["Config"]["Image"]] = {
        "image_id": image["Id"], "repo_digests": image.get("RepoDigests", [])}
with Path("runs/metadata/runtime-images.json").open("x") as handle:
    json.dump(records, handle, sort_keys=True, indent=2)
    handle.write("\n")
PY
```

## Empat kondisi melalui MCP

Kerjakan S0, S1, S2 lalu S3 secara berurutan. Apply annotations, tunggu catalog konsisten, ekspor dua kali ke directory berbeda dan build snapshot. Jangan mengubah kondisi sebelum kedua ekspor sebelumnya selesai. Contoh S0:

```bash
uv run --frozen --project environments/metadata python infra/datahub/apply_annotations.py --scenario S0 --receipt runs/metadata/annotation-writes/S0.json
uv run --frozen --project environments/metadata python infra/datahub/export_mcp.py --scenario S0 --page-size 5 --output-directory runs/metadata/exports/S0-a
uv run --frozen --project environments/metadata python infra/datahub/export_mcp.py --scenario S0 --page-size 5 --output-directory runs/metadata/exports/S0-b
uv run --frozen sakila-experiment metadata snapshot-build --first-export runs/metadata/exports/S0-a --second-export runs/metadata/exports/S0-b --audit runs/database/baseline.json --spec data/annotations/specification.json --output-directory snapshots/candidates-v2
```

Ulangi dengan ID/path S1–S3, lalu validate-set dan hentikan DataHub sesuai [runbook](runbook.md). Token kedaluwarsa direnew melalui bootstrap_token.py dan receipt rotasinya disimpan. Pagination/truncation/tool errors tidak boleh diabaikan. `snapshots/distribution-v1` dapat diinspeksi offline; ia tidak menggantikan bukti retrieval host baru.

## Referensi, model dan run

Validasi 39 gold melalui `validate-gold`; lakukan review A01/A02/adjudikasi; download GGUF terpin; verifikasi backend. Ikuti pilot → sampler → freeze → run → analysis pada runbook. Metadata services tidak diperlukan selama generation.

Pendahuluan memerlukan opt-in dan provisional outputs; reviewed route memerlukan keputusan manusia nyata. Source/model/settings/snapshots/prompt tidak boleh berubah antara qualification pilot dan benchmark. Untuk historical replay, gunakan source commit/hashes historis, bukan branch main terbaru.

| Tingkat bukti | Membuktikan | Tidak membuktikan |
|---|---|---|
| Unit tests | Kontrak komponen/kasus sengaja salah | Gold benar secara makna |
| Fresh isolated MySQL | Import, privileges, fingerprint | Retrieval catalog baru |
| Archived MCP replay | Payload deterministik dari receipts sama | Fresh DataHub ingestion |
| Fresh DataHub/MCP | Ingestion/catalog/retrieval runtime baru | Identical stochastic model output |
| Fixed-run audit | Trial uniqueness/provenance/integritas | General semantic equivalence |

`infra/reproduce.py` memerlukan archived raw exports, official source archive dan baseline lokal. Ia membangun locked environment, fresh isolated database dan archived-MCP replay tanpa LLM. Milestone lama memverifikasi 133 tests; source pendahuluan memverifikasi 141 lokal/CI. Jangan memindahkan angka terbaru ke laporan lama. Jangan mengarsipkan seluruh reproduction workspace yang berisi venv/generated credentials; hanya kumpulkan bukti terpilih yang diaudit.
