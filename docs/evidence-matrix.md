# Matriks requirement, verifikasi dan bukti

Matriks ini mendampingi BAB IV. Bukti pilot memakai referensi draft dan bukan hasil eksperimen utama. Jumlah tests final harus diambil dari output pytest milestone yang bersangkutan, bukan diasumsikan dari tabel.

| Requirement | Implementasi/verifikasi | Bukti lokal | Status |
|---|---|---|---|
| Sakila resmi tidak dimodifikasi | Import byte-for-byte dan fingerprint skema/DDL/data | `runs/database/import-manifest.json`, `baseline.json` | Terverifikasi pada database penelitian |
| Akses SQL read-only | Grants per base table, global freeze, single statement dan timeout | `tests/integration/test_database.py` | Integration test |
| Metadata sesuai installed schema | Audit connector; fidelity receipt untuk native geometry | `runs/metadata/connector-validation.json`, `fidelity-receipt.json` | Terverifikasi |
| Catalog melalui DataHub | Authenticated ingestion dan penulisan anotasi | `runs/metadata/catalog-ingestion.json`, `annotation-writes/` | Terverifikasi |
| Retrieval melalui MCP | Tools aktual, raw response, hash dan pagination | `runs/metadata/mcp-tool-inventory.json`, `exports/` | Terverifikasi |
| Kontrol empat kondisi | Technical schema sama, coverage sama, S3 aditif | `snapshots/candidates-v2`, `tests/unit/test_snapshots.py` | Kandidat tervalidasi; review semantik pending |
| Tidak ada gold di generation input | Public/private contracts, prompt tests dan literal leakage scan | `tests/unit/test_generation.py`, `runs/verification/annotation-literal-leakage.json` | Struktur teruji; semantik anotasi tetap direview |
| Referensi benar secara makna | Human review dan validasi ulang setelah revisi | `runs/reviews/closure-02`, `data/reviews/decisions.json` | Pending, tidak dibuat otomatis |
| Context lengkap | Apply-template dan tokenizer dengan output reserve/margin | `runs/preliminary/benchmark-01/manifest.json` | Seluruh 120 prompt terverifikasi; maksimum 7.450 input token, cadangan output/margin tersedia |
| Kandidat tambahan | Official pinned model, hash, 24 GPU layers dan context 16.384 | `models/qwen25-coder-7b-q4km.json`, `runs/inference/coder7b/backend-final-24/verification.json` | Backend/context verification tanpa generation; qualification pilot terpisah sudah selesai |
| Verification tidak melakukan generation | Mock server menolak endpoint selain pemeriksaan | `tests/unit/test_runtime_verification.py` | Unit test |
| Bukti sampler khusus backend | Model hash/backend hash/pilot manifest dicocokkan | `runs/inference/coder7b/backend-final-24/sampler-verification.json` | Terverifikasi sesudah 36-trial pilot pendahuluan pada 7B yang sama |
| EX menjaga duplikat dan tipe | Multiset/ordered comparison, exact numbers, NULL, one-to-one approximate matching | `tests/unit/test_compare.py`, `test_values.py` | Unit test |
| Model error berbeda dari infra | Persist response sebelum evaluasi, EX biner hanya untuk evaluable trials | `tests/unit/test_runner.py`, `test_ledger.py` | Unit test dan pilot awal |
| Resume tidak generation ulang | Live replay completed pilot tanpa task/event baru | `runs/verification/live-resume-pilot-01.json` | Terverifikasi pada milestone pilot awal |
| 600 assignment terkendali | Balanced schedule dan simulasi outage/crash/recovery | `tests/unit/test_schedule.py`, `test_runner.py` | Simulasi sintetis, bukan main run |
| Log tidak dapat diganti diam-diam | Append-only triggers, manifest/hash validation, audit exports/results | `tests/unit/test_report.py`, `test_ledger.py` | Unit test |
| Readiness tidak cukup dari completion flag | Audit ledger dan kecocokan seluruh input pilot/main | `tests/unit/test_readiness.py` | Unit test; main tetap blocked |
| Analisis berpasangan | Question-block permutation, Holm, paired stratified bootstrap | `tests/unit/test_statistics.py`, `docs/analysis-plan.md` | Sintetis teruji; persetujuan metodologi pending |
| Reproduksi terisolasi | New Python environment dan MySQL port 13309/volume terpisah; replay raw MCP evidence | `infra/reproduce.py`, `runs/reproduction/closure-final/report.json` | Berhasil; database/empat payload identik dan 133 tests; bukan fresh DataHub ingestion |
| Tidak memalsukan hasil utama | Draft gate sebelum model preparation | `runs/verification/live-main-draft-gate.json` | Reviewed main tetap pending; 600 pendahuluan terpisah |
| Jalur pendahuluan jujur | Explicit opt-in, provisional record/CSV/figures | `tests/unit/test_preliminary.py`, `test_report.py` | 141 tests pada source pendahuluan lulus lokal dan CI; reviewed gates tetap terpisah |
| Review independen | 152 template item/A01 dan A02, immutable source/hash | `annotations/round-01`, `test_annotations.py` | Siap distribusi; belum ada keputusan manusia |
| Rescore gold saja | Same-input guard, typed decode, complete adjudication binding | `evaluation/reevaluate.py`, `test_reevaluate.py` | Fixture teruji; real rescore menunggu review |
| Publikasi tanpa hasil/secret | Staged-index audit dan review naskah | `infra/publication.py`, `docs/publication.md` | Source awal 207 file diaudit sebelum publikasi; scores/predictions lokal |
| Run 600 pendahuluan nyata | 600 responses dan outcomes, 150/kondisi, 200/complexity; database tetap | `runs/preliminary/benchmark-01`, `runs/analysis/preliminary-01` | Lengkap/lolos audit; actual EX/statistics privat dan provisional |
| Reproduksi source akhir | New workspace/environment dan MySQL port 13310; archived MCP replay | `runs/reproduction/publication-01/report.json` | 144 tests lulus; schema/data/empat payload identik; nol generation |

## Membaca bukti yang berubah versi

Payload snapshot yang identik dapat mempunyai manifest provenance berbeda saat direproduksi pada directory baru. Yang dibandingkan untuk determinisme konten adalah hash payload. Artifact lama tidak ditimpa. Source yang berubah dapat membuat pilot lama tidak cukup sebagai qualification untuk main, meskipun hasil lama masih valid sebagai bukti historis.

Reproduksi awal menemukan healthcheck socket dapat lolos saat MySQL masih menjalankan server sementara. Healthcheck diperbaiki ke query TCP `SELECT 1`; percobaan gagal dipertahankan pada `runs/reproduction/closure-01`. Percobaan kedua berhasil; reproduksi final juga berhasil pada versi source penutupan, termasuk 133 tests. Report serta logs tersedia pada `runs/reproduction/closure-final`.
