# Panduan review instrumen Sakila revision02

Paket ini memuat proposal30soal dan12pilot,106elemen anotasi, serta3aturan domain. Status seluruh keputusan masih kosong. Paket tidak mengandung prediksi LLM, EX, statistik perlakuan atau identitas reviewer yang dibuat otomatis. Input exploratory telah dibekukan sesudah independent AI review dan reference/fixture checks; persetujuan manusia belum tersedia. Periksa versi/hash paket ini saat mengirim submission.

Gunakan dua reviewer yang bekerja sendiri. Berikan salinan kosong tersendiri kepada tiap reviewer. Kode reviewer dapat dipakai pada CSV; simpan pemetaan nama dan tanggal asli terpisah. Jangan mengubah ID atau menimpa kolom sumber. Catat perubahan di proposed_correction dan alasan di reason. Isi decision dengan accept, revise, reject, atau uncertain. Biarkan kosong untuk item yang belum diperiksa; kosong bukan accept dan bukan nol.

## Tahap1: interpretasi independen

Buka questions-blind.csv sebelum questions-reference.csv. Baca soal, schema Sakila dan definisi global resmi yang relevan. Tulis independent_interpretation, independent_sql dan ambiguities. Bedakan kebutuhan pengetahuan yang memang tersedia dalam metadata dari maksud permintaan yang tetap ambigu meskipun S3 lengkap. Jangan menebak hasil eksperimen. Simpan dan hitung SHA-256 file tahap1 sebelum melihat reference usulan. Catat waktu penyerahan tahap1.

## Tahap2: reference dan struktur SQL

Buka questions-reference.csv. Periksa populasi, grain, unit, waktu, peran entitas, NULL/zero, duplikat, urutan kolom, threshold dan ties. Pastikan query menjawab maksud soal, bukan sekadar berhasil dieksekusi. Tulis SQL alternatif bila berbeda. Bandingkan pada Sakila dan kasus pembeda yang telah ditetapkan, termasuk entitas tanpa transaksi dan nilai tepat pada batas. Klasifikasi kompleksitas mengikuti canonical SQL dan adapter Spider yang didokumentasikan; bukan persepsi reviewer tentang sulit/mudah dan bukan hasil LLM. Catat alternative structure bila solusi wajar lebih sederhana.

## Tahap3: metadata dan aturan

Pada annotations.csv, bandingkan short/detailed dengan sumber resmi. Tambahan panjang tanpa proposisi baru tidak wajib. Elemen trivial boleh sama. Periksa kekeliruan fakta, repetisi yang tidak membantu, definisi yang saling bertentangan dan bocoran jawaban. Pada business-terms.csv, periksa executable source dan dokumentasi, bukan asumsi bisnis DVD rental secara umum. Aturan rewards memakai payment events dan dua batas strict. Stock memakai keadaan rental pada snapshot. Komponen keterlambatan bukan full customer balance; cutoff inclusive DATETIME, date-only midnight dan nol untuk pelanggan tanpa rental relevan harus konsisten dengan sumber. Jangan memasukkan gold SQL, recipe join atau threshold benchmark ke metadata global.

## Tahap4: pilot dan konsolidasi

Pilot12soal adalah diagnostik terpisah, bukan tambahan sampel utama. Periksa pilot-reference.csv dengan standar semantik yang sama. Konsolidasikan dua submission sesudah keduanya dikunci hash. Catat setiap ketidaksepakatan dan keputusan adjudikasi. Jangan mengisi approval massal secara otomatis. Jika review dilakukan sesudah generation, tulis tanggal sebenarnya dan sebut post-run review. Gold-only correction dapat dinilai ulang sebagai laporan turunan; perubahan wording/metadata/prompt memerlukan versi instrumen dan generation baru. Tidak boleh mengubah input demi memperoleh EX lebih tinggi atau p-value signifikan.

## Konvensi umum yang harus dibaca bersama soal

Urutan kolom mengikuti keluaran yang diminta; aliases diabaikan. Urutan baris bebas kecuali permintaan ordering/ranking. Duplikat dipertahankan sesuai grain. Komponen tanggal tersimpan memakai UTC tanpa konversi tersirat. Rerata/rasio ditampilkan empat desimal dan threshold dibandingkan sebelum pembulatan. Groups NULL dipertahankan; SUM tanpa observasi numeric tetap NULL, kecuali definisi domain eksplisit menetapkan nol. Setiap entitas yang diminta dalam laporan dipertahankan dengan count nol bila tidak memiliki relasi yang memenuhi. Baca prompts/generation-v2.txt dan protokol revision02 untuk teks sebenarnya.

Keterbatasan: hasil pada database tetap tidak membuktikan ekuivalensi semantik universal. AI-assisted review bukan review manusia. Jumlah30 dan pembagian10–10–10 adalah constrained study design, bukan klaim mencakup seluruh SQL atau workload operasional.
