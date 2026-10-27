# Local experiment runbook

Perintah dijalankan dari repository root. Jangan menyalin secret ke CLI arguments atau Git. Run IDs dan output directories baru mempertahankan artifact lama; gunakan directory yang sama hanya untuk resume input yang identik.

## Preparation services

Database penelitian memakai `infra/compose.yaml`, port 13306. DataHub memakai port 18080 dan 19002. Local inference memakai port 18081. Seluruh published ports terikat loopback.

```bash
uv sync --frozen --project environments/metadata
uv run --frozen --project environments/metadata python infra/datahub/prepare.py
docker compose --env-file secrets/datahub.env -f infra/datahub/compose.yaml --profile quickstart up -d --wait --wait-timeout 600
uv run --frozen python infra/datahub/bootstrap_token.py
```

Token preparation berlaku satu jam. Jika kedaluwarsa, jalankan `bootstrap_token.py --renew`; secret diganti lokal dengan permission 0600 dan hash pendahulunya masuk receipt baru. Account UI lokal bawaan hanya digunakan pada catalog penelitian yang terikat loopback. Catalog reader/MCP tidak digunakan saat inference.

Ingestion awal: `check_ingestion.py` menghasilkan diagnostik; audit/reconciliation harus dilakukan sebelum `ingest_catalog.py`. File diagnostik bukan snapshot. Bukti instalasi ini ada pada `runs/metadata/connector-validation.json`, `fidelity-receipt.json`, `roundtrip-validation.json`, dan `catalog-ingestion.json`.

Untuk membangun ulang kondisi, gunakan receipt dan export directory baru. Terapkan satu kondisi, selesaikan dua ekspor dan validasi, baru ubah kondisi berikutnya. Contoh satu kondisi:

```bash
uv run --frozen --project environments/metadata python infra/datahub/apply_annotations.py --scenario S2 --receipt runs/metadata/rebuild-02/writes/S2.json
uv run --frozen --project environments/metadata python infra/datahub/export_mcp.py --scenario S2 --page-size 5 --output-directory runs/metadata/rebuild-02/S2-a
uv run --frozen --project environments/metadata python infra/datahub/export_mcp.py --scenario S2 --page-size 5 --output-directory runs/metadata/rebuild-02/S2-b
```

`metadata.snapshots.build_candidate` memeriksa kedua ekspor terhadap audit schema dan authoring specification; `validate_scenario_set` memeriksa seluruh kondisi. Builder tidak melengkapi metadata dari MySQL/API. Original S0–S3 dan candidates v2 dipertahankan; source URL v1 yang keliru telah diarsipkan dan dikoreksi tanpa mengubah wording anotasi.

## Inference and pilot — current candidate workflow

Hentikan DataHub untuk menghindari kompetisi RAM. Volume tidak dihapus.

```bash
docker compose --env-file secrets/datahub.env -f infra/datahub/compose.yaml --profile quickstart stop
uv run --frozen sakila-experiment model fetch --spec models/qwen25-coder-7b-q4km.json --receipt runs/inference/coder7b/download.json
docker compose -f infra/inference/compose.coder7b.yaml up -d
uv run --frozen sakila-experiment backend verify --config configs/coder7b.toml --model-receipt runs/inference/coder7b/download.json --compose-file infra/inference/compose.coder7b.yaml --container sakila-research-llama --output-directory runs/inference/coder7b/backend-new
```

Kandidat 7B sudah diunduh dan loading/token budget diverifikasi di `runs/inference/coder7b/backend-24`. Gunakan directory baru untuk pemeriksaan berbeda; jangan menimpa bukti lama. Pilih backend evidence yang memang dipakai untuk run berikutnya. Model download menerima revision, byte count dan SHA-256 yang dipin. Pastikan tersedia RAM sebelum startup, DataHub berhenti dan endpoint sudah siap sebelum verifikasi. Server memakai satu slot, context 16.384, 24 GPU layers, fit/cache/context shift off. Verifikasi ini tidak melakukan generation.

**Pilot/gold tetap draft. Perintah pilot dan probe akan ditolak sebelum ada review semantik.** Contoh di bawah hanya digunakan setelah reviewer menyelesaikan koreksi dan status referensi disetujui. Gunakan run ID baru karena source dan kebijakan telah berubah dari pilot 3B historis.

```bash
uv run --frozen sakila-experiment validate-gold --questions data/pilot/questions.jsonl --gold data/pilot/gold.jsonl --output-directory runs/gold/pilot-reviewed-01
uv run --frozen sakila-experiment pilot --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --experiment-id coder7b-reviewed-01 --output-directory runs/pilot/coder7b-reviewed-01
uv run --frozen sakila-experiment backend verify-sampler --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/pilot/coder7b-reviewed-01 --output runs/inference/coder7b/backend-final-24/sampler-verification.json
uv run --frozen sakila-experiment backend probe --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --output-directory runs/inference/coder7b/probe-reviewed-01
```

Urutkan sampler verification segera setelah pilot selesai, sebelum request probe mengubah last slot settings. Bukti sampler harus mempunyai model hash, backend hash dan pilot manifest yang sesuai; bukti 3B tidak dipakai untuk 7B. Probe memakai lima request pilot independen tanpa scoring atau feedback.

Resume menggunakan perintah dan semua input yang sama. Perubahan source, prompt, snapshots, questions, gold, settings atau manifest ditolak. Response tersimpan hanya dievaluasi ulang. Model error mendapat EX=0; infrastructure interruption menghentikan proses dan tetap pending. Hentikan runner sebelum mengklasifikasikan crash ambigu. Recovery CLI menolak respons tersimpan dan trial selesai:

```bash
uv run --frozen sakila-experiment experiment recover --run-directory runs/main/main-01 --trial-id Q001-S0-r01 --attempt-id 1 --operator NAMA_OPERATOR --note "Runner sudah berhenti; insiden dispatch dicatat dan tidak ada respons tersimpan"
```

Perintah tersebut hanya mencatat insiden, tidak memanggil model dan tidak memperbaiki SQL. Gunakan ID/attempt yang benar dari ledger; contoh bukan instruksi untuk membuat main run sekarang.

`analyze` mengaudit manifest, plan, SQLite events, JSONL export, prompt hashes dan result hashes. Pilot mendapat tabel deskriptif saja.

## Main gates — currently pending

```bash
uv run --frozen sakila-experiment readiness --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/pilot/coder7b-reviewed-01 --output runs/readiness/main-review-new.json
```

Exit status 1 berarti review/artifact belum lengkap. Report memisahkan `automated_checks` dan empat `required_reviews`: benchmark (termasuk kontrak EX dan pemisahan pilot), metadata, generation dan analysis. `data/reviews/decisions.json` hanya diisi berdasarkan keputusan manusia dengan component, artifact_sha256, status approved, reviewed_by dan reviewed_at_utc; sistem tidak membuat approval. Gold utama/pilot juga harus approved sesudah pemeriksaan makna. Rancangan statistik masih menunggu bimbingan.

Setelah review selesai, gunakan konfigurasi final yang direview untuk kedua perintah berikut. Perintah pertama tidak melakukan generation; perintah kedua dapat menghasilkan 600 trial dan tidak boleh dijalankan sebelum freeze sukses.

```bash
uv run --frozen sakila-experiment freeze-main --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/pilot/coder7b-reviewed-01 --experiment-id main-01 --output-directory runs/main/main-01
uv run --frozen sakila-experiment run-main --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/pilot/coder7b-reviewed-01 --experiment-id main-01 --output-directory runs/main/main-01
uv run --frozen --group analysis sakila-experiment analyze --run-directory runs/main/main-01 --output-directory runs/analysis/main-01
```

Jangan mengubah protokol setelah melihat hasil utama. Hash perubahan akan memerlukan freeze baru; perubahan metodologi harus dicatat dan dibahas, bukan digunakan untuk memilih hasil yang signifikan.

## Releasing resources

```bash
docker compose -f infra/inference/compose.coder7b.yaml stop
```

Database dan catalog volumes tetap ada. Jangan memakai `down -v` untuk menutup sesi penelitian.

## Metadata normalization dan reproduksi

```bash
uv run --frozen sakila-experiment metadata reconcile --events runs/metadata/connector-diagnostic.json --audit runs/database/baseline.json --output-directory runs/metadata/reconcile-new
uv run --frozen sakila-experiment metadata snapshot-build --first-export runs/metadata/exports/S0-a --second-export runs/metadata/exports/S0-b --audit runs/database/baseline.json --spec data/annotations/specification.json --output-directory snapshots/rebuild-new
uv run --frozen sakila-experiment metadata validate-set --snapshot-root snapshots/candidates-v2 --output runs/metadata/set-check-new.json
uv run --frozen sakila-experiment review package --output-directory runs/reviews/review-new
uv run --frozen python infra/reproduce.py --id closure-new --port 13309 --output-directory runs/reproduction/closure-new
```

Reproduksi membuat workspace/venv, project/container/volume dan credentials baru; hanya loopback port alternatif digunakan. Fresh official import dibandingkan terhadap skema/DDL/data baseline. Snapshot direkonstruksi dari dua ekspor MCP aktual yang diarsipkan untuk setiap kondisi dan hash payload harus identik. Ini bukan fresh DataHub catalog test dan tidak menjalankan LLM. Report/failure receipt dan cleanup dipertahankan; container reproduksi dihentikan tanpa menghapus volume.

Tiga script lama pada `infra/inference` kini merupakan compatibility entrypoint untuk CLI parameterized yang sama dan memerlukan argumen eksplisit. Model 3B tetap tersedia melalui `models/qwen25-3b-q4km.json` dan config/compose historis, tetapi belum menjadi model final. Source lama untuk mengulang milestone lama tersedia dalam bundle evidence historis; jangan menggunakan source baru untuk mengklaim resume manifest lama cocok.
