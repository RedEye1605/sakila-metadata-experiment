# Dasar penyusunan dataset revision 02

Dokumen ini menjelaskan desain yang disusun sesudah preliminary 01 dan audit, sebelum generation revision 02. Revisi bukan preregistration retrospektif. Hasil pendahuluan lama dipertahankan dan tidak digunakan untuk memilih soal yang membuat S3 menang.

## Apa yang diadopsi dari benchmark

[Spider](https://aclanthology.org/D18-1425/) menggunakan komponen SQL untuk mengelompokkan kesulitan dan proses penyusunan/review dataset. Penelitian ini mengadaptasi routine `eval_hardness` dari source resmi yang dikunci pada `research/revision-02/spider-source-lock.json`. Ia tidak menggunakan exact SQL matching sebagai metrik utama. Spider berorientasi cross-domain; penelitian satu database Sakila tidak diklaim setara dengan cakupan tersebut.

[BIRD](https://arxiv.org/html/2305.03111v3) mendasari pemisahan struktur SQL dari kebutuhan pemahaman data dan pengetahuan eksternal. Revisi menggunakan profil schema mapping, local semantics, dan domain integration sebagai label operasional penelitian sendiri. Label ini bukan hardness/knowledge taxonomy resmi BIRD. Dua penulis reference bekerja terpisah, tetapi keduanya AI-assisted; tidak dilaporkan sebagai dua anotator manusia.

[Zhong, Yu, dan Klein](https://aclanthology.org/2020.emnlp-main.29/) menunjukkan alasan memakai database pembeda ketika satu hasil eksekusi dapat meloloskan SQL yang maknanya berbeda. Penelitian ini memakai delapan data variations terkontrol, bukan mengklaim mengimplementasikan keseluruhan test-suite generation mereka. [Dr.Spider](https://arxiv.org/abs/2301.08881) menjadi dasar umum controlled robustness diagnostics; A/B/C serta rotasi metadata dalam penelitian ini adalah desain lokal dan bukan task resmi Dr.Spider.

## Definisi kompleksitas yang dapat diperiksa

|Komponen adapter|Yang dihitung pada root scope|
|---|---|
|component 1|Keberadaan WHERE, GROUP BY, ORDER BY, LIMIT; tambahan table units; kemunculan OR dan LIKE|
|component 2|Nested queries pada condition scopes dan cabang set operations yang dipetakan ke routine upstream|
|others|Indikator multiple aggregates, multiple selected expressions, multiple WHERE conditions, multiple GROUP expressions|

Keputusan easy/medium/hard/extra mengikuti urutan kondisi routine upstream, bukan label berdasarkan jumlah join saja. Hasilnya kadang tidak intuitif: dua aggregate dan beberapa output dapat menaikkan label meskipun tabel sedikit. Quirk upstream pada NOT-condition aggregate count dipertahankan dan dilaporkan. Sembilan belas oracle cases diturunkan dari pinned upstream source; unit tests memeriksa batas/struktur, bukan sekadar menghasilkan label yang sama dengan implementasi sendiri.

SQLGlot membaca dialect MySQL. Scalar functions dan aggregate wrappers dicatat sebagai adaptation. CTE/window, derived FROM, projection subqueries dan bentuk lain yang tidak terpetakan ditolak untuk canonical profiling. Bentuk tersebut tetap dapat menjadi SQL jawaban model yang valid. Alternative reference dapat memiliki struktur lebih sederhana atau hardness berbeda; label menjelaskan canonical reference yang dibekukan dan tidak membuktikan kesulitan intrinsik pertanyaan.

Pembagian 30 soal ialah 10 easy→simple,10 medium→medium,5 hard+5 extra→complex. Ini kuota desain penelitian, bukan frekuensi query produksi. Canonical query tidak boleh ditambah wrapper, join, nesting, atau clause yang tidak diperlukan untuk memperoleh label lebih tinggi. Tidak ada klaim bahwa Sakila, soal atau pola SQL tidak pernah dilihat model saat pretraining.

## Pengetahuan yang diuji

|Profil|Contoh kebutuhan|Batas interpretasi|
|---|---|---|
|Schema mapping|Identitas entitas, PK/FK, membership dan cakupan relasi|Nama kolom/FK pada S0 sudah memberi petunjuk kuat; baseline tidak diasumsikan gagal|
|Local semantics|Periode sewa katalog, unit durasi film, home store, payment versus rental staff|Makna field lokal tetap berada di S1/S2; tidak dipindahkan ke S3 untuk membuat novelty semu|
|Domain integration|Stock availability, monthly rewards, returned-rental late component|Kebutuhan bersumber pada executable routine resmi dan harus belum terspesifikasi dalam complete input S0–S2|

S3 menambah tiga kartu global. Stock membedakan salinan yang belum pernah disewa dari salinan dengan open rental. Rewards memakai payment events, periode bulan kalender lengkap sebelumnya, dua threshold strict dan tanpa syarat active. Komponen keterlambatan mengikuti perilaku kalender, NULL-return, cutoff serta zero-total pada routine executable. Full customer balance dikeluarkan karena komentar dan body mempunyai perbedaan penting. Penelitian tidak menggeneralisasikan perilaku routine lama sebagai kebijakan rental yang semestinya berlaku di semua bisnis.

Enam kandidat domain mencakup dua bentuk pelaporan untuk setiap keluarga. Alokasi source-feasible ialah 0 simple/2 medium/4 complex. Enam soal bukan enam kebijakan independen: hanya tiga keluarga dan satu database. Generalisasi harus menyebut ketergantungan keluarga ini. Profil lengkap kebutuhan diperiksa dari question+common instructions+snapshot, bukan dari count glossary atau first occurrence suatu kalimat.

## Bahasa alami, scope dan kebocoran

Soal memakai permintaan analitik singkat dalam bahasa Indonesia. Output columns ditulis berurutan; nilai filter, interval, threshold atau reference date yang diperlukan tetap merupakan parameter tugas. Definisi domain, satuan yang tersimpan, role distinctions dan exceptions ada pada metadata global. Soal tidak memuat gold SQL, join paths atau langkah penyelesaian.

Ambiguitas istilah yang terjawab oleh definisi S3 adalah treatment yang disengaja. Maksud target yang masih mempunyai beberapa jawaban wajar sesudah membaca S3 adalah defect. Contohnya top-five tanpa ties policy, missing text tanpa aturan NULL/blank, elapsed-versus-calendar duration, atau observed groups versus complete grid yang belum ditetapkan. Kandidat seperti itu ditahan/dikeluarkan. Kalimat yang sulit dipahami bukan ukuran kompleksitas SQL.

Kontrak private tetap menyimpan grain, population, measure, units, roles, time, NULL/zero, duplicates, ties, precision, sources dan counterexamples. Common formatting conventions dibekukan sama untuk semua kondisi. Gold dan kontrak private tidak masuk generation input. Scenario ID, complexity dan question ID juga tidak diteruskan ke model.

## Penyaringan dan pemilihan

Pool authored bertambah 45→54 untuk tiga keluarga source-based rules dan 54→60 untuk menambah single-predicate filters. Penambahan terakhir mengatasi dominasi agregasi pada calon simple questions. Simple stratum berisi lima filter dan lima aggregate tanpa filter. Main domain allocation dan 10–10–10 tetap.

Exclusions mencatat ambiguity, disagreement pada fixture, canonical deadline, dan rendahnya discrimination pada primary Sakila seperti release years yang seragam atau original-language count yang selalu nol. Kriteria menggunakan sumber, kebutuhan tugas dan reference/data checks sebelum model inference. Ia tidak menggunakan hasil EX, token generation, latency atau p-values. Daftar dan alasan per ID ada pada selection receipt.

Eligible pools diurutkan berdasarkan ID. `random.Random(2026102801)` memilih dalam urutan stratum simple-filter, simple-aggregate, medium, hard, extra; enam source-rule IDs merupakan constrained coverage yang dipilih secara purposive. Setiap pool, mandatory IDs dan draw disimpan. Proposal yang belum lolos review diberi `conditional_draft_not_eligible`, bukan frozen benchmark. Jika independent review membatalkan kandidat, instrumen harus diamendemen sebelum generation; hasil model tidak boleh menjadi alasan mengganti soal.

Proposal02 menggunakan 13 dari 16 base tables. `film_text`, `language` dan `store` tidak dirujuk langsung, meskipun seluruh technical/descriptive metadata tetap diberikan pada semua kondisi. Profilnya mencakup 9 schema-mapping, 15 local-semantics dan 6 domain-integration questions. Canonical references mempunyai WHERE pada 15 soal, GROUP BY pada 13, join components pada 14, dan nested/set branches pada 5. Belum ada ORDER BY, LIMIT atau LIKE pada canonical main references; text-pattern requests berada pada pilot. Cakupan ini harus dilaporkan sebagai batas desain, bukan disebut mencakup semua pola SQL operasional. Angka coverage berasal dari AST/reference proposal dan bukan hasil model.

Semua selected gold harus berhasil, dua reference harus sepakat pada baseline+delapan variations, dan setiap predeclared critical mutant harus mempunyai witness. Persetujuan ini adalah pemeriksaan engineering bersyarat. Human review tetap pending dan hasil yang diizinkan peneliti tetap exploratory.

## Apa yang tidak dapat dibuktikan desain ini

Tiga puluh soal bukan sampel acak seluruh kasus Text-to-SQL nyata. Satu model terkuantisasi tidak mengidentifikasi penyebab perbedaan antar-model, bahasa, atau quantization. S1–S3 mengubah informasi sekaligus panjang dan salience; pengaruh paket metadata tidak sama dengan efek murni panjang token. Diagnostik terpisah membantu memeriksa redundansi/repetisi/posisi, tetapi tidak menjadikan padding inert atau memberi bukti tunggal suatu mekanisme. Lima repetitions meningkatkan deskripsi kestabilan, bukan menambah jumlah pertanyaan independen menjadi 600.

Hasil EX yang sama pada satu database tetap dapat terjadi untuk SQL salah. Auxiliary fixtures memberi bukti pembeda tambahan dan dilaporkan terpisah dari EX utama; delapan variasi tidak membuktikan ekuivalensi universal. Peningkatan metadata adalah hipotesis yang dapat ditolak. Tidak ada syarat bahwa S3 harus menjadi kondisi dengan skor tertinggi.
