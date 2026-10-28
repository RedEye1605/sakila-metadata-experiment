# Handoff untuk penulisan penelitian

Dokumen ini mengarahkan penulis/AI pendamping; bukan sumber untuk mengarang hasil penelitian.

**Instrumen terkini revision-03:** gunakan `docs/revision-03/`, `data/benchmarks/revision-03/final-02/`, `configs/revision03.toml` dan `prompts/generation-v3.txt`. Soal tidak lagi memiliki footer kolom teknis, dan EX menerima satu pemetaan bijektif kolom global. Ranking/ordering tetap memerlukan urutan baris benar. Tiga soal ordered mencakup dua top-k dengan konvensi ties seragam. Gold A/B sepakat pada sembilan database cases; human review tetap pending. Belum ada generation atau EX revision03. Hasil diagnostik revision02 tetap milik versi lama dan tidak boleh dipindahkan ke revision03. BAB IV bagian4.13 menjelaskan perubahan. Uraian berikutnya adalah sejarah versi lama kecuali diberi label terkini.

**Pembaruan revision-02:** tabel dan penjelasan pendahuluan di bawah mengacu pada instrumen lama. Revisi setelah audit ada pada `docs/bab-iv.md` bagian 4.12 dan `docs/revision-02/`. Revisi memakai tiga kartu domain dan 12 pilot diagnostik, berbeda dari tujuh istilah/sembilan pilot lama. Input akhir `data/benchmarks/revision-02/final-02` berisi 30 soal dari pool 60 dengan rubric adaptasi Spider dan kebutuhan pengetahuan terpisah. Reference utama/pilot lolos sembilan database; source checkpoint lulus 228 tests dan driver dry-run tanpa generation. Tidak ada EX revisi pada checkpoint ini; jangan menyalin skor lama menjadi skor revisi. Gunakan run completion/laporan aktual nanti, bukan status source pra-run, untuk menulis hasil. Human review tetap pending; paket akhir berada di `annotations/round-02`.

Judul wajib: **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**.

Gunakan delapan tahap metodologi yang disepakati: Studi Literatur; Penyusunan Anotasi Metadata; Penyusunan Dataset Pengujian; Perancangan Pipeline Text-to-SQL; Implementasi Pipeline Text-to-SQL; Pengujian Text-to-SQL; Analisis Hasil; Penarikan Kesimpulan dan Saran. Setup Sakila dan pemeriksaan model adalah kegiatan teknis, bukan tahap penelitian tambahan. EX dihitung dalam pengujian; statistik masuk analisis hasil.

## Sumber wajib

| Kebutuhan | Sumber |
|---|---|
| BAB IV: rancangan dan implementasi | `docs/bab-iv.md`, `docs/implementation-plan.md`, `docs/reproduction.md`, source modules |
| Kontrol dan keputusan | `docs/decisions.md`, `docs/evaluation-protocol.md`, `docs/analysis-plan.md` |
| Diagram editable dan siap pakai | `docs/figures/source/*.mmd`, SVG/PNG pada directory induk |
| Soal/gold dan kontrak | `data/public/main.questions.jsonl`, `data/private/main.gold.jsonl`, `data/pilot` |
| Anotasi dan skenario | `data/annotations/specification.json`, `snapshots/distribution-v1` |
| Review independen | `annotations/round-01/GUIDE.md`, template A01/A02; submission privat terpisah |
| Klaim pengujian | `docs/evidence-matrix.md`, laporan pytest/reproduction aktual di `runs/` lokal |
| BAB V | **Hanya** laporan EX aktual, manifest, ledger dan adjudikasi yang disediakan peneliti secara privat |

Repository publik sengaja tidak menyertakan keluaran model, angka EX, p-values atau grafik hasil sebelum review. Ketiadaan hasil di repository bukan izin mengisi angka ilustratif sebagai hasil nyata. Jangan membuat nama reviewer, tanggal, jumlah persetujuan, tingkat akurasi atau signifikansi.

## Fakta desain yang harus dipertahankan

- S0–S3 memakai database, data, technical schema, coverage, urutan serialisasi, prompt, pertanyaan, model/settings dan evaluator yang sama. S1/S2 mencakup 106 elemen; S3 mempertahankan deskripsi S2 verbatim lalu menambah tujuh istilah bisnis.
- Sakila aktual mempunyai 16 base tables, 90 kolom, 22 FK, 47.268 baris. Views/routines tidak menjadi konteks model. Gunakan diagram yang diturunkan dari audit aktual, bukan skema buatan.
- DataHub mengelola anotasi; MCP mengambilnya pada persiapan. Eksperimen memakai snapshot beku. Model tidak memiliki akses MySQL, MCP, DataHub, gold atau hasil sebelumnya.
- Desain 30×4×5 menghasilkan 600 trial, bukan 600 pertanyaan independen. Lima request dapat menghasilkan SQL identik. Sembilan soal pilot terpisah dari 30 utama.
- EX menilai ekuivalensi hasil pada database tetap. Duplicate multiplicity, NULL, posisi kolom, numerik dan ordering mengikuti kontrak; exact SQL matching bukan metrik utama. Hasil sama pada satu database tidak membuktikan general semantic equivalence.
- Model error adalah terminal EX=0. Infrastruktur gagal tidak otomatis EX=0. Tidak ada repair semantik, error feedback atau kesempatan kedua untuk trial model yang sudah selesai.
- Input length meningkat dengan deskripsi dan dicatat. Jangan mengklaim efek metadata terpisah dari panjang token melalui kontrol yang tidak dilakukan.

## Status ilmiah dan batas klaim

Benchmark/gold/anotasi masih **draft**. Peneliti mengizinkan 36 pilot dan 600 trial **pendahuluan** untuk menghasilkan laporan teknis. Software tidak mengubah draft menjadi approved. Gunakan kata pendahuluan/provisional pada semua keluaran yang belum melewati review.

Run pendahuluan sudah lengkap dan lolos audit. Laporan aktual berada secara lokal di `runs/analysis/preliminary-01`, khususnya `interpretation.md`, `report.md` dan `report.json`. Jangan mengirim paket penulis yang memuat skor kepada A01/A02 sebelum submission independen mereka selesai. Source generation/analisis asli adalah commit bb32938; hardening review ditambahkan sesudah completion, bukan mengganti source di tengah run.

Rencana analisis dipilih sebelum run pendahuluan dan di-hash: agregasi skor/5 per question–scenario, omnibus permutation dalam question blocks, enam paired contrasts dengan Holm, 10.000 bootstrap question-level berstrata complexity; seed dan implementasi tercatat. Uraikan asumsi exchangeability, keterbatasan 30 soal terpilih, tied/discrete scores, pointwise CI, dan bahwa nonsignificance bukan bukti ekuivalensi.

Sesudah adjudikasi, perubahan gold/kontrak saja dapat menghasilkan rescore turunan tanpa generation jika seluruh generation inputs identik. Pertanyaan/metadata/prompt/model/settings berubah memerlukan run baru. Jangan menyebut hasil pascareview otomatis konfirmatori ketika skor sebelumnya sudah dilihat. Catat setiap koreksi dan urutan waktu secara terbuka.

## Petunjuk menyusun BAB IV dan BAB V

BAB IV menjelaskan tujuan instrumen, kebutuhan, lingkungan, arsitektur dua fase, Sakila aktual, metadata, normalisasi/provenance, dataset, prompt/model, safety/comparator, scheduler/logging, review serta pengujian implementasi. Tabel kebutuhan dan bukti membantu membedakan planned, implemented, tested dan reviewed.

BAB V memakai hanya file aktual lokal yang diberikan peneliti: `report.json`, `report.md`, `execution-accuracy.csv`, `complexity.csv`, `questions.csv`, `paired-contrasts.csv`, `measurements.csv`, grafik PNG/PDF, manifest/freeze/completion dan catatan review. Periksa 600 ID unik, denominator 150/kondisi, 200/complexity dan database_unchanged. Jangan menafsirkan pilot sebagai efek metadata utama. Laporkan effect size dan uncertainty bersama p-values; diskusikan ketepatan gold serta error model tanpa cherry-picking.

Naskah harus menyatakan bahwa pipeline merupakan instrumen eksperimen kuantitatif analitis, bukan produk chatbot atau model baru. Jangan mengubah judul, menambah studi banding model besar-besaran, atau membuat hasil yang belum ada.
