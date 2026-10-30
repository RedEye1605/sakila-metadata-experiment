# Revisi instrumen 02 — protokol exploratory

Judul tetap **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**. Revisi berada pada penyusunan anotasi, dataset, pipeline, pengujian dan analisis dalam delapan tahap penelitian yang telah disepakati.

## Keputusan sebelum generation baru

Peneliti memilih 30 soal baru, 180 trial diagnostik, lalu 600 trial exploratory. Review manusia belum tersedia. Tidak membuat persetujuan manusia dan tidak mengubah status menjadi main. Sasaran ialah pengaruh empat paket metadata terhadap EX, termasuk ketersediaan pengetahuan domain; bukan efek murni panjang teks. Hasil lama tidak ditimpa. Hasil baru tidak boleh dipilih berdasarkan S3 menang atau signifikansi.

Satu model tetap: Qwen2.5-Coder 7B Q4_K_M, backend dan decoder terverifikasi. Database utama, technical metadata, serialization, cakupan, prompt dan gold tetap antarkondisi. Phase A tetap DataHub/MCP; inference hanya memakai frozen snapshots. DataHub dan llama-server dijalankan bergantian.

## Dasar penyusunan dan kompleksitas

Spider §3 memisahkan penulisan, SQL review, bahasa dan final review. §6 menetapkan empat tingkat berdasarkan kombinasi komponen SQL. Revisi mengadopsi batas `eval_hardness` pada commit yang tercantum di `research/revision-02/spider-source-lock.json`, dengan adapter AST MySQL yang fail closed. Ini adaptasi, bukan penggunaan evaluator SQLite untuk grading MySQL. Parser v1 dan dataset lama tetap tersedia untuk reproduksi.

Pemetaan: easy → simple (10), medium → medium (10), hard → complex (5), extra → complex (5). Kuota ini adalah desain sampling penelitian, bukan proporsi workload nyata. Label menjelaskan canonical reference, bukan kemampuan intrinsik soal atau jaminan kesulitan model. Semua komponen, adaptations dan reference alternatif dicatat. Tidak menambahkan clause atau wrapper yang tidak dibutuhkan untuk menaikkan label. CTE/window dapat menjadi jawaban sah tetapi membutuhkan canonical reference lain untuk klasifikasi rubric ini.

`component1` mencatat WHERE/GROUP/ORDER/LIMIT, tambahan table units, OR dan LIKE. `component2` mengikuti nested/set branches pada routine upstream. `others` mengikuti indikator multiple aggregates/selections/conditions/group expressions upstream. Quirk penghitungan kondisi NOT upstream dipertahankan dan diberi label; derived FROM, SELECT subqueries dan struktur lain yang tidak terpetakan ditolak. Fungsi scalar MySQL dan aggregate wrapper ditandai sebagai adaptation. Threshold dan label mengikuti urutan kondisi upstream, termasuk batas yang mungkin tidak intuitif.

Profil kebutuhan pengetahuan terpisah, terinspirasi BIRD §3 dan Appendix B.1. Tidak mengklaim memiliki label BIRD resmi. Ambiguitas belum terselesaikan membuat kandidat tidak eligible; tidak dijadikan kesulitan yang sengaja ditambahkan.

Alokasi awal sembilan sel dibatalkan melalui amendment A01 setelah audit menemukan bahwa local field meaning tidak cukup menjadi kebutuhan eksklusif S3. Alokasi source-feasible yang diusulkan adalah nol soal domain sederhana, dua menengah, dan empat kompleks, dalam tiga keluarga aturan resmi. Kuota utama tetap 10/10/10; raw Spider tetap 10 easy/10 medium/5 hard/5 extra. Enam soal domain tetap harus lolos audit informasi dan semantic witnesses, bukan otomatis eligible karena sudah ditulis.

Source/fact inventory mendahului penulisan kandidat. Pool bertambah dari 45 ke 54 untuk aturan resmi, lalu 60 untuk mengatasi dominasi agregasi pada calon soal sederhana. Simple sampling dibagi lima single-predicate filters dan lima unfiltered aggregates. Exclusion, sorted pools, fixed seed 2026102801 dan stratum draws dicatat sebelum generation. Penulis soal melihat kebutuhan dan sumber domain, bukan model outputs atau target EX. Question-only review mendahului gold. Dua penulis reference bekerja terpisah. Proposal 30 belum menjadi benchmark yang disahkan. Tidak sekadar mengganti angka/nama pada soal lama. High-level SQL capabilities boleh berulang; semantic-family overlap dilaporkan. Tidak mengklaim held-out dari pretraining model.

Setiap question card mengunci tujuan, grain/population/measure, roles, units/time, zero/NULL/duplicates, ordering/ties, precision, sources, required facts dan availability, structural profile, references, counterexamples dan review history. Pending human review ditampilkan di seluruh laporan. AI-assisted authors/reviewers dilaporkan secara jujur; bukan double-blind human annotation.

## Metadata dan information availability

S0 technical baseline identik. S1/S2/S3 mencakup 106 elemen yang sama. S2 menambah informasi lokal yang bersumber; elemen trivial boleh sama dengan S1. S3 mempertahankan S2 byte-for-byte dan menambah konteks lintas konsep yang mempunyai sumber. Tidak memaksa seluruh kolom lebih panjang. Atomic facts memiliki owner, source, dan exposure. Catat fakta eksplisit, derivable atau absent, tanpa menganggap baseline pasti gagal.

Larangan: gold SQL, aggregate recipes, join instructions, answer rows, benchmark IDs/thresholds, kebijakan bisnis rekaan. Home store versus inventory store, payment optional references dan retained inactive records mempunyai sumber resmi; sumber tidak menetapkan semua default reporting policies. Population, periode, tie-breaking dan pilihan pelaporan tetap jelas. Jika tidak tersedia fakta untuk kuota domain, laporkan blocker instrumen tanpa mengarangnya.

## Pelaksanaan

Diagnostik:12 soal terpisah × A/B/C/B-order 1/B-order 2 ×3 seeds =180. A adalah snapshot S3 canonical. B membungkus setiap deskripsi dengan dua kalimat penjelas tetap tanpa proposisi domain baru. C mempertahankan deskripsi A dan mengulang tiga definisi domain yang benar tetapi tidak dibutuhkan oleh pilot. Counts setiap kartu dibatasi 1–12, dipilih berdasarkan tokenizer tanpa generation agar annotation tokens berjarak maksimum 5% dari B. C menguji irrelevant exposition/repetition; tidak diklaim menambah pengetahuan baru atau menjadi padding inert. Dua rotasi B memindahkan blok deskripsi sebesar floor(106/3) dan floor(212/3), menjaga teks dan technical schema. A/B/C melalui DataHub/MCP; rotasi merupakan transform eksplisit dari B. Empat contrasts: B−A,C−A,B-order 1−B,B-order 2−B. Tidak mengklaim pure length isolation. Tidak ada model sweep atau tuning pada main question outcomes.

Benchmark: 30 × S0–S3 × 5 = 600; randomized repetition blocks; matched q/repeat seeds, independent requests, no repair/history/tools/gold. Full 120 benchmark prompts dan 60 diagnostic prompts diverifikasi sebelum run. Metadata/benchmark tidak dipilih ulang berdasar hasil diagnostik. Perubahan stimulus setelah freeze memerlukan amendment dan versi baru. Extra generation tidak ditambahkan diam-diam.

Database utama selalu beku. Delapan schema-valid isolated data variations menguji zero groups, grain/fan-out, roles/store, NULL/optional references, ties/top-k, temporal buckets/gaps, numeric boundary/precision, serta catalog language variation. Semua outputs tersimpan dinilai pada primary instance dan auxiliary cases dengan SQL sama. Primary EX dan robustness dilaporkan terpisah. Minimal satu plausible wrong variant per soal harus dapat dibedakan. Finite suite bukan proof semantic equivalence.

## Analysis dan penghentian

EX utama mempertahankan question blocks (bukan 600 independent tasks). Omnibus 100,000 within-question permutations; enam exact sign-flip contrasts dan Holm; efek percentage points; 10,000 whole-question bootstrap stratified by structural complexity, pointwise 95%. Alpha .05; seed dan assumptions dibekukan. Profil business need, consistency, tokens, latency dan robustness deskriptif. Semua tied questions dipertahankan. Tidak menyebut nonsignificance sebagai equivalence. Bootstrap tidak menjadikan fixed selected questions sampel representatif seluruh workload.

Gate wajib: semantic contracts/provenance valid, required data fixtures membedakan mutants, context lengkap, model/settings verified, read-only/safety/grants benar, input hashes cocok, append-only ledger/resume valid. Tidak ada accuracy threshold atau significant-p stopping. Infrastructure failure EX=null; jangan mengubah ke model EX=0. Stored responses direplay tanpa generation. Dispatch ambigu dihentikan untuk rekonsiliasi, tidak otomatis digenerate ulang.

## Sumber primer

- Spider §3/§6: https://aclanthology.org/D18-1425/
- Pinned source: `research/revision-02/spider-source-lock.json`.
- BIRD §3/Appendix B.1: https://arxiv.org/html/2305.03111 v 3
- Semantic evaluation/test suites: https://aclanthology.org/2020.emnlp-main.29/
- Controlled robustness diagnostics: https://arxiv.org/abs/2301.08881
- Metadata descriptions, batas transfer: https://arxiv.org/abs/2408.04691

Dokumen ini merupakan protokol yang disusun setelah preliminary-01 dan audit. Bukan preregistration retrospektif, human approval, atau klaim bahwa pipeline revisi telah selesai diuji. Bukti implementasi dan status berikutnya dicatat terpisah.
