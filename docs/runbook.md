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

**Pilot/gold tetap draft. Jalur reviewed menolak draft; jalur pendahuluan terpisah memakai opt-in eksplisit.** Contoh reviewed di bawah hanya digunakan setelah koreksi dan persetujuan semantik. Jalur pendahuluan yang dipilih peneliti dijelaskan pada bagian tersendiri; tidak mengubah review status.

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

## Preliminary route — explicit draft authorization

Urutan ini dipilih peneliti untuk memperoleh laporan teknis sebelum review. Semua actual scores/predictions tetap lokal. Gunakan source commit yang sama dari pilot sampai 600 trial selesai; jangan commit perubahan atau mengubah source/config/prompt/input di tengah run. Perubahan naskah Markdown diperbolehkan kecuali analysis plan yang sudah di-hash. Gunakan directory baru untuk percobaan baru. Perintah berikut merujuk bukti backend lokal; pada host baru lakukan backend verification dengan bukti baru terlebih dahulu.

```bash
uv run --frozen python infra/inference/start_local.py
uv run --frozen sakila-experiment run-preliminary --pilot --allow-unreviewed --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --experiment-id prelim-pilot-01 --output-directory runs/preliminary/pilot-01
uv run --frozen sakila-experiment backend verify-sampler --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/preliminary/pilot-01 --output runs/inference/coder7b/backend-final-24/sampler-verification.json
uv run --frozen sakila-experiment backend probe --allow-unreviewed --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --output-directory runs/inference/coder7b/probe-preliminary-01
uv run --frozen sakila-experiment freeze-preliminary --allow-unreviewed --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/preliminary/pilot-01 --experiment-id preliminary-01 --output-directory runs/preliminary/benchmark-01
uv run --frozen sakila-experiment run-preliminary --allow-unreviewed --config configs/coder7b.toml --backend-evidence runs/inference/coder7b/backend-final-24/verification.json --pilot-directory runs/preliminary/pilot-01 --experiment-id preliminary-01 --output-directory runs/preliminary/benchmark-01
uv run --frozen --group analysis sakila-experiment analyze --run-directory runs/preliminary/benchmark-01 --output-directory runs/analysis/preliminary-01
```

Pilot berisi 36 assignment dengan satu repetition; benchmark berisi 600 assignment. Freeze memeriksa semua 120 prompt serta gold execution tanpa generation. `--allow-unreviewed` tidak membuat approval. Report/CSV/figures menyatakan provisional; statistics tetap exploratory/conditional. Model failures tidak diperbaiki/diulang. Infra incident mengikuti kebijakan recovery yang sama dengan reviewed route.

Public clone memakai `snapshots/distribution-v1` untuk inspect/validate dengan `--snapshot-root`. Untuk run yang auditable, lakukan persiapan DataHub/MCP pada host tersebut atau sediakan arsip raw receipts asli dan baseline pendukung. Candidate manifests lokal dan receipts runtime sengaja tidak disebarkan sebagai bukti instalasi host baru.

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

## Independent annotation and reference-only reevaluation

Paket siap distribusi: `annotations/round-01`. Berikan hanya folder A01 kepada A01 dan A02 kepada A02, ditambah GUIDE.md, schema.json serta material reference bersama. Path panduan detail adalah **`reference/review-guide.md`** (huruf kecil). Jangan berikan actual model output/EX. File template read-only: reviewer mengedit salinannya pada directory kerja privat.

```bash
uv run --frozen sakila-experiment review consolidate --package annotations/round-01 --a01 annotations/submissions/A01 --a02 annotations/submissions/A02 --output-directory annotations/submissions/consolidation-01
```

Program menolak source cells/ID berubah dan memvalidasi criterion, decision, alasan serta tanggal. Submission parsial boleh dikonsolidasikan untuk memantau kemajuan, tetapi adjudikasi/rescore mensyaratkan kedua submission lengkap. Tidak ada approval otomatis. Adjudikator mengisi final_decision, final_correction, adjudicator, rationale dan adjudicated_at_utc pada salinan adjudication.csv. Untuk gold-only correction, final_correction harus JSON berisi hanya gold_sql/column_count/ordered/approximate_columns/semantic_notes. Koreksi metadata atau pertanyaan menuntut generation baru.

Rescore kemudian memerlukan receipt nyata dengan status adjudicated, reviewers A01/A02, adjudicator/tanggal, generation_signature, gold_sha256, adjudication_sha256, consolidation_report_sha256 dan review_package_sha256. Generation signature dihitung dari manifest sumber melalui `evaluation.reevaluate.generation_signature`; hash lain memakai SHA-256 byte file sebenarnya. Jangan mengisi receipt dengan nama/tanggal contoh dan menyebutnya keputusan sebenarnya. `report.json` konsolidasi lengkap harus berada bersama adjudication.csv.

```bash
uv run --frozen --group analysis sakila-experiment experiment reevaluate --config configs/coder7b.toml --source-run runs/preliminary/benchmark-01 --questions data/public/main.questions.jsonl --gold data/private/main.reviewed.gold.jsonl --snapshot-root snapshots/candidates-v2 --review-package annotations/round-01 --adjudication-file annotations/submissions/consolidation-01/adjudication.csv --receipt annotations/submissions/adjudication-receipt.json --output-directory runs/reevaluation/reviewed-01
```

Perintah contoh ini **belum dapat dijalankan** sebelum review sesungguhnya. Tidak ada reviewed replacement gold/receipt yang dibuat otomatis. Reevaluation menjalankan gold baru serta membandingkan typed prediction results yang tersimpan, tanpa inference baru atau modifikasi ledger asal. Jangan mengganti mode pendahuluan menjadi reviewed main secara retroaktif.

## Figures and publication

Diagram menggunakan Mermaid CLI 12.0.0 terpin. Node 22.13+ dan Chrome diperlukan; `tools/diagrams/puppeteer.json` menetapkan executable Linux lokal dan dapat disesuaikan pada host lain. Sesuaikan hanya tooling visual, bukan runtime eksperimen.

```bash
PUPPETEER_SKIP_DOWNLOAD=1 npm ci --prefix tools/diagrams --ignore-scripts --no-audit --no-fund
uv run --frozen python infra/render_diagrams.py
uv run --frozen python infra/publication.py
```

Audit publikasi membaca **staged index**; pemeriksaan naskah manual tetap diperlukan. Jangan memasukkan directory reproduksi workspace secara utuh ke archive karena berisi credentials/venv. Hanya kumpulkan file bukti yang dipilih dan sudah diaudit. `docs/publication.md` menetapkan embargo aktual model results sebelum external review.
