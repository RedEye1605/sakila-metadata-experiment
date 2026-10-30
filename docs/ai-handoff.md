# Mulai di sini — handoff penulisan skripsi

**Pipeline dan run Qwen3.5-9B sudah selesai.** Peneliti meminta paket aktual dipublikasikan agar dapat melanjutkan penulisan di Windows dengan agent baru. Tugas berikutnya adalah penyusunan/penyuntingan naskah berdasarkan evidence, bukan menjalankan ulang eksperimen.

## Paket yang harus dibaca

1. [Paket penulisan dan hasil aktual](../reports/qwen35-9b-main-01/README.md).
2. [Brief lengkap untuk agent baru](../reports/qwen35-9b-main-01/AGENT_BRIEF.md).
3. [Panduan Windows dan pemeriksaan offline](../reports/qwen35-9b-main-01/WINDOWS.md).
4. [BAB IV — Perancangan dan Implementasi](../reports/qwen35-9b-main-01/thesis/BAB_IV.md), [BAB V — Hasil dan Pembahasan](../reports/qwen35-9b-main-01/thesis/BAB_V.md).
5. [Satu naskah BAB IV–V beserta lampiran](../reports/qwen35-9b-main-01/thesis/NASKAH_BAB_IV_V_LENGKAP.md).
6. [Laporan EX/statistik](../reports/qwen35-9b-main-01/analysis/report.md), [audit pascarun](../reports/qwen35-9b-main-01/evidence/postrun-audit/report.md), [riwayat run](../reports/qwen35-9b-main-01/HISTORY.md).

Judul tetap: **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**.

## Run utama saat ini

Run `qwen35-9b-main-01`: 30 soal Indonesia × 4 kondisi × 5 repetitions = **600 trial lengkap**; 150/kondisi, 200/complexity. Model upstream Qwen/Qwen3.5-9B, GGUF Q4_K_M dari Unsloth. Source eksperimen `ab3860c2742936073ded5b1bed66951b738b2a5f`; source penulisan/publikasi sesudahnya tidak mengganti source run.

| Kondisi | Benar/150 | EX (%) |
|---|---:|---:|
| S0 | 98 | 65,33 |
| S1 | 111 | 74,00 |
| S2 | 109 | 72,67 |
| S3 | 121 | 80,67 |

Omnibus paired permutation `p=0.001019989800101999`. Hanya S3–S0 signifikan setelah Holm enam kontras: +15,33 poin persentase, `p_Holm=0.0234375`. Lima repetitions tidak membuat 600 observasi menjadi independen; statistik memakai 30 question blocks. Jangan menyatakan semua tambahan metadata signifikan atau lebih panjang selalu lebih baik.

Terdapat 600 durable responses/outcomes/sampler proofs, 0 infrastructure incidents, 576 SQL successes, 23 model execution errors, 1 parser rejection. Delapan variasi terisolasi menghasilkan 4.800 auxiliary SQL outcomes tanpa generation baru. Audit independen pascarun mencatat 17 checks lulus. Database fisik sesudah completion cocok dengan schema/data fingerprint beku. Periksa cakupan tepatnya dalam laporan audit, bukan klaim bebas bug universal.

## Kontrol dan batas klaim

DataHub/MCP hanya digunakan pada metadata preparation. Inference menerima snapshot beku, pertanyaan dan instruksi sama; model tidak mengakses MySQL, gold, tools atau history. S3 menambah tiga domain definitions, bukan tujuh istilah pada versi awal. Evaluator menerima satu global column permutation, mempertahankan whole-row duplicates, typed values dan row order yang diminta. Tiga ordered tasks mencakup dua top-k tasks.

Model dipilih peneliti sesudah hasil model terdahulu diketahui; pilot/smoke generation tambahan secara eksplisit ditiadakan. Run ini mempunyai 600 main requests, **0 additional pilot, 0 smoke**. Jangan menulis bahwa model ini lulus capability pilot atau dipilih prospektif. Hasil lama tetap tersedia untuk disclosure dan tidak boleh diganti label menjadi pilot.

Review completion stimulus merupakan pernyataan peneliti; nama/tanggal reviewer belum diberikan dan harus diisi peneliti. Raw gold mempertahankan label draft historis; user attestation terpisah mengikat versi yang dieksekusi. AI/reference agreement tidak menggantikan bukti reviewer manusia. BAB I–III, template kampus dan identitas reviewer tidak boleh dikarang.

## Petunjuk kerja

Gunakan angka dari JSON/CSV aktual dan lampiran input di paket. Bedakan engineering validation, human review attestation dan inferensi statistik. Pertahankan delapan tahap metodologi, satu database/model tetap dalam run dan batas generalisasi 30 purposively selected questions. Simpan revisi editorial terpisah dari evidence beku.

Tidak diperlukan model weights, Python, Docker, DataHub, MCP atau MySQL untuk membaca/menulis bab. Arsip evidence dan verifier tersedia untuk pemeriksaan offline. Path absolut Linux dalam receipts adalah provenance historis, bukan konfigurasi Windows.

Dokumen arsip yang masih menyebut pra-run, pilot lama, embargo atau model lama harus dibaca menurut versinya. [Otorisasi publikasi baru](../reports/qwen35-9b-main-01/PUBLICATION_AUTHORIZATION.json) berlaku untuk curated writing bundle; manifest historis tetap byte-identical. Credentials, weights dan volume database tidak dipublikasikan.
