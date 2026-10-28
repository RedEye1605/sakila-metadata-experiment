# Kebijakan SQL untuk instrumen revisi

`mysql-readonly-v2` dipakai tetap pada seluruh kondisi revisi. Default lama `mysql-readonly-v1` dipertahankan. Hasil preliminary-01 tidak dinilai ulang dengan kebijakan baru.

Pemeriksaan gold pilot menemukan bahwa v1 menolak `HOUR` dan `FIND_IN_SET`, meskipun query native berhasil melalui reader MySQL. Fungsi yang sah tidak boleh ditolak hanya karena alternatif implementasinya belum tercakup oleh validator. Sebelum inference revisi, v2 menambah katalog terbatas fungsi native yang relevan: `HOUR`, `MINUTE`, `SECOND`, `DAYNAME`, `FIND_IN_SET`, `STR_POSITION` (normalisasi parser untuk `LOCATE`/`INSTR`), `REGEXP_LIKE`, `STR_TO_DATE`, dan `LAST_DAY`.

Nama tersebut diperiksa terhadap SQLGlot yang terpasang dan dokumentasi [string functions MySQL 8.4](https://dev.mysql.com/doc/refman/8.4/en/string-functions.html), [date/time functions](https://dev.mysql.com/doc/refman/8.4/en/date-and-time-functions.html), serta [regular expressions](https://dev.mysql.com/doc/refman/8.4/en/regexp.html). `ALL`/`ANY` merupakan [quantified subquery comparisons](https://dev.mysql.com/doc/refman/8.4/en/all-subqueries.html), bukan scalar functions yang dibuka melalui wildcard.

Unknown functions, qualified functions, file/delay/locking functions, uncontrolled current-clock/random functions, unsafe statement types, lintas-database access, executable comments dan multiple statements tetap ditolak. Privilege SELECT pada tabel individual, server read-only, transaction read-only, timeout dan batas hasil tetap aktif. Ini katalog yang dideklarasikan untuk instrumen, bukan implementasi seluruh MySQL atau klaim bahwa parser saja menjamin keamanan.

Session menggunakan UTC dan `lc_time_names=en_US` yang ditetapkan serta diverifikasi pada reader revisi. Model/settings dan kebijakan eksekusi sama pada seluruh skenario. Clone auxiliary memakai kebijakan dan locale yang sama dengan primary evaluation; administrator clone hanya digunakan untuk trusted fixture setup.

Validation status dan error code disimpan terpisah dari execution result. Penolakan karena policy harus dilaporkan sebagai kategori tersendiri. Kebijakan ini membatasi ruang SQL yang diizinkan; perbandingan old/new EX tidak boleh dianggap perubahan metadata saja, karena instrumen dan kebijakan juga berubah.

Tests memeriksa fungsi native yang sebelumnya ditolak, `ALL`/`ANY`, pelestarian v1, penolakan fungsi berbahaya/tidak dikenal, locale, dan fingerprint database setelah eksekusi. Validasi reference utama dan pilot diulang menggunakan versi ini sebelum manifest run dibekukan. Review kode independen sebelumnya menutup empat gate defects; permintaan review khusus perubahan policy ini terhenti karena batas penggunaan, sehingga tidak diklaim telah memperoleh independent sign-off baru.
