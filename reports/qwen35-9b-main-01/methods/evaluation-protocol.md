# Evaluasi revision-03

Revision-03 memakai `ex-results-v3-column-permutation`, ditetapkan sebelum generation benchmark baru. Hasil revision-02 dan pendahuluan lama tetap memakai aturan yang dicatat dalam manifest masing-masing. Tidak ada regrading diam-diam.

## Kesetaraan hasil

Jumlah kolom harus sama. Alias dan urutan kolom diabaikan: evaluator mencari satu bijeksi kolom aktual ke kolom gold yang berlaku konsisten untuk seluruh baris. Gold `(nama, pendapatan)` dan aktual `(pendapatan, nama)` dapat memperoleh EX=1. Pendapatan milik seseorang tidak boleh dipindahkan ke orang lain. Equal column marginals, independent column sorting atau sorting isi tiap baris bukan bukti kesetaraan.

Tanpa permintaan ordering/ranking, bandingkan multiset whole rows sesudah pemetaan kolom. Multiplicity duplikat dipertahankan. Bila soal meminta pengurutan/peringkat, urutan baris harus cocok sesudah pemetaan kolom. Gold SQL berbeda secara struktural dari prediksi tidak menghalangi EX=1.

Konvensi pelaporan yang sama pada S0–S3 tercantum dalam `prompts/generation-v3.txt`: prioritas urutan mengikuti permintaan bisnis, sisa ties memakai identifier numerik unik entitas secara ascending. Top-k menghasilkan tepat k baris, atau seluruh baris eligible jika kurang dari k. Tidak memperluas batas untuk memasukkan seluruh ties. Identifier pemecah seri tidak perlu menjadi kolom keluaran.

NULL berbeda dari string `NULL`, string kosong dan angka nol. Integer/Decimal dibandingkan secara numerik tanpa konversi lossy ke float. Monetary sums dan counts exact. Tolerance 1e-9 absolute + 1e-12 relative hanya pada kolom rerata/rasio yang ditetapkan gold, dihitung terhadap nilai gold. Kontrak DATE/ISO-string dan tolerance tetap memakai posisi kolom gold sesudah mapping. Datetime, tanggal dan numeric strings tidak digabung secara sembarang.

Dua hasil kosong tetap memerlukan lebar kolom sama; tidak tersedia nilai untuk mengidentifikasi kolom kosong. Keterbatasan ini dicatat, bukan diselesaikan dengan alias atau klaim semantic equivalence universal.

## Algoritme dan batas sumber daya

Candidate mapping memakai signature setiap kolom, lalu deterministic bijection search dan whole-row verification. Ordered exact/date columns memakai aligned sequences. Approximate candidates menjaga kategori numeric/non-numeric; whole-row matching tetap menentukan hasil. Algoritme tidak memakai random pruning. Correct outcomes merekam mapping `gold_column -> actual_column` dalam ledger.

Batas: 32 kolom, 10.000 search nodes, 10 juta constraint/leaf cells dan shared approximate comparison/augmenting-edge work budget. Pencocokan approximate per group juga mempertahankan batas satu juta row pairs. Budget exhaustion adalah `EvaluationError`/infrastructure incident dengan EX belum ditetapkan; respons tersimpan dapat dievaluasi kembali setelah koreksi evaluator yang terversi. Bukan alasan mengirim ulang request model atau memberi model EX=0 tanpa penilaian lengkap.

Primary EX memakai Sakila resmi yang tetap. Seluruh SQL tersimpan kemudian dapat diuji pada delapan variations clone terisolasi. Fixtures revision-03 menambahkan tariff ties, dua staf eligible yang tied untuk top1, serta sedikitnya 12 pelanggan tied pada batas top10. Primary schema/data tidak diubah. Wrong variants yang diuji mencakup arah urutan, k yang salah, serta tie-breaking yang salah.

## Landasan dan batas adopsi

Implementasi [Test Suite SQL Evaluation](https://github.com/taoyds/test-suite-sql-eval/blob/master/exec_eval.py) mencari global column permutation dan mempertahankan bag semantics; urutan baris diperiksa bila relevan. Revision ini menerapkan prinsip tersebut pada MySQL dengan deterministic search, contract-aware dates/numerics, empty-width checks dan explicit resource budgets. Tidak mengklaim semua benchmark menggunakan aturan identik. Dasar penggunaan database pembeda adalah [Zhong, Yu dan Klein (2020)](https://aclanthology.org/2020.emnlp-main.29/). Delapan variations lokal bukan implementasi lengkap distilled test suites.

Safety SELECT-only, timeout, batas hasil, satu kesempatan generation, tanpa repair/error feedback, infrastructure accounting, dan paired question-level analysis tetap berlaku. Review manusia tetap pending. Agreement dua reference AI dan finite fixtures merupakan bukti engineering, bukan human approval atau proof universal.
