# Status implementasi — 28 Oktober 2026

Pipeline end-to-end sudah menyelesaikan **36 trial pilot dan 600 trial pendahuluan nyata**. Audit lengkap lulus: 600 unique IDs, 150/kondisi, 200/complexity, seluruh responses/terminal outcomes tersimpan dan database tidak berubah. Tidak ada insiden infrastruktur selama run benchmark. Gold/anotasi tetap **draft**; EX/statistik bukan persetujuan semantik.

## Terimplementasi dan terverifikasi

- Official Sakila di MySQL terisolasi: 16 base tables, 90 kolom, 22 FK dan 47.268 baris. Reader hanya SELECT; session policy, AST, single statement, timeout dan result bounds diuji nyata.
- DataHub Core 1.8.0, ingestion SDK 1.7.0.17, MCP server 0.8.0, SDK 1.30.0 dan FastMCP 3.2.0 telah diuji melalui authenticated ingestion/retrieval. Native geometry reconciliation terjadi sebelum catalog ingestion, bukan fallback snapshot.
- Empat candidate snapshots berasal dari dua ekspor MCP/kondisi yang stabil. Coverage/technical schema sama; S1/S2 mempunyai 106 deskripsi, S3 mempertahankan S2 dan menambah tujuh istilah. Payload/hashes tetap sama setelah run.
- Qwen2.5-Coder-7B-Instruct Q4_K_M terpin revision/hash; llama.cpp b11206, context 16.384 dan 24 GPU layers. Semua 120 benchmark prompts diperiksa tanpa truncation; maksimum input 7.450 token plus reserve/margin tetap muat.
- Prompt dan requests stateless; tanpa tools, gold, conversation history atau error feedback. Lima request per question–scenario, paired seeds, balanced randomized repetition blocks.
- Typed EX comparator mempertahankan duplikat, NULL, posisi kolom, exact numerics dan ordering contracts. Tidak ada semantic repair.
- SQLite append-only, durable responses, explicit ambiguous-dispatch recovery dan safe resume tersedia. Audit memeriksa ledger/events/exports/prompt/results, bukan hanya completion flag.
- Laporan EX, complexity, per-question consistency, latency/tokens, paired permutation/Holm/bootstrap dan lima figure PNG/PDF sudah dibuat **lokal** dengan label provisional. Actual scores/predictions tetap tidak dipublikasikan.
- Paket A01/A02 masing-masing 152 item siap distribusi tanpa actual model outputs. Konsolidasi mempertahankan hash enam submission dan final adjudication tetap pending.
- Gold-only reevaluation memiliki guard terhadap perubahan generation inputs, unrecorded corrections, complexity, database session, comparator dan analysis implementation. Synthetic rescore membuktikan stored results dapat dinilai ulang tanpa HTTP/LLM atau ledger mutation. Real reevaluation menunggu review.
- Verifikasi sampler membedakan toleransi float32 dan exact integer parameters. Pemeriksaan postrun cocok dengan final assigned seed dan cache nol; tidak menambah generation.

## Versi dan bukti

Generation serta original analysis memakai frozen commit **bb32938**, dengan 141 tests lokal/CI pada versi tersebut. Hardening review/sampler ditambahkan setelah 600 trial selesai, kemudian **144 tests** lulus lokal dan pada workspace reproduksi `publication-01`.

Reproduksi terbaru memakai environment baru dan fresh isolated MySQL port 13310. Schema/DDL/data serta empat snapshot payload cocok. Ia mereplay archived MCP receipts; tidak diklaim sebagai fresh DataHub ingestion atau pengulangan stochastic outputs. Milestone `closure-final` terdahulu dengan 133 tests tetap dipertahankan dan tidak diberi angka baru secara retroaktif.

| Bukti lokal | Isi |
|---|---|
| `runs/preliminary/benchmark-01` | Frozen manifest/plan/freeze, 600 durable outcomes, prompts/results, completion dan supplementary resource observations |
| `runs/analysis/preliminary-01` | Laporan aktual privat, interpretasi, CSV dan PNG/PDF |
| `runs/verification/postrun-snapshots.json` | Snapshot coverage/hash/additivity sesudah run |
| `runs/verification/postrun-sampler.json` | Requested/observed sampler parameters dan exact final seed |
| `runs/verification/postrun-float-diagnostic.json` | Postrun check float serialization; tidak mengubah trial/EX |
| `runs/inference/coder7b/backend-postrun-01` | Model/container/context verification pascarun tanpa generation |
| `runs/reproduction/publication-01/report.json` | Latest isolated reconstruction dan seluruh stage receipts |
| `annotations/round-01` | Independent blank templates, schema/gold material, guide dan hashes |
| `runs/reviews/annotator-distribution-01` | ZIP A01/A02 tanpa actual scores/predictions |

## Masih memerlukan manusia

Review independen A01/A02 dan adjudikasi makna soal/gold, kontrak, complexity, pemisahan pilot, deskripsi serta glossary belum selesai. Tidak ada nama reviewer, tanggal atau approval yang diisi otomatis. Keputusan analysis eksternal dan penetapan versi akhir penelitian perlu dicatat sesuai bimbingan.

Jika hanya gold/kontrak dikoreksi dan seluruh generation inputs tetap, lakukan derived rescore dengan receipt terikat hash. Perubahan pertanyaan/metadata/prompt/model/settings memerlukan generation baru. Hasil yang telah dilihat tidak otomatis menjadi konfirmatori; ungkapkan timing dan perubahan post hoc.

DataHub dan inference dihentikan dengan volumes/weights dipertahankan. Research MySQL tetap read-only. Instance mysql-dev pengguna tidak dimodifikasi.
