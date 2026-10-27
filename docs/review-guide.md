# Panduan review untuk peneliti dan dosen/rekan

Status seluruh referensi masih draft. Peneliti telah menyatakan pilot belum direview; tidak ada approval yang dibuat oleh program atau asisten.

Paket lengkap tersedia pada `runs/reviews/closure-02`. Buka `review-guide.md` dan salin CSV ke directory kerja reviewer. Paket memuat 30 soal utama, sembilan pilot, 106 elemen anotasi dan tujuh istilah bisnis. `manifest.json` mencatat hash bahan yang diperiksa. Hasil referensi hanya disertakan bila masih cocok dengan validation receipt dan hash result.

## Urutan review

1. Tinjau sembilan soal pilot sebelum pilot kandidat tambahan dinilai. Periksa teks pertanyaan, gold SQL, kolom, ordering, NULL/duplicates dan hasil referensi.
2. Tinjau 30 soal utama menggunakan kriteria sama; pastikan rubric kompleksitas dapat dijelaskan melalui SQL, bukan persepsi panjang kalimat.
3. Bandingkan pilot dan utama untuk kesamaan makna/parafrase. Kemiripan JOIN atau tabel tidak otomatis berarti kebocoran; soal dengan maksud sama dan hanya mengganti angka perlu ditinjau khusus.
4. Tinjau anotasi dan sumbernya. Pastikan S1 dan S2 membicarakan elemen sama, S3 menambah konsep yang bersifat umum, serta aturan tidak mengasumsikan kebijakan bisnis yang tidak didokumentasikan.
5. Diskusikan model/prompt/settings dan protokol EX/statistik. Jangan memilih model berdasarkan kondisi mana yang menghasilkan peningkatan metadata paling menarik.

## Isi catatan reviewer

CSV menyediakan `decision`, `rationale`, `reviewer`, dan `reviewed_at_utc`. Gunakan accepted, revise, atau rejected; timestamp UTC dalam ISO 8601. Jangan mengisi accepted hanya karena SQL dapat dieksekusi.

Alasan koreksi harus merujuk makna pertanyaan atau semantik database. Contoh: "pertanyaan meminta pembayaran individual, tetapi gold menjumlahkan pembayaran per pelanggan". Koreksi tidak boleh berbunyi "SQL model tidak bisa menjawab sehingga soal disederhanakan".

Program tidak mengimpor CSV sebagai approval otomatis. Setelah keputusan disepakati, perubahan dataset/specification harus diperiksa, dibuatkan versi, dan divalidasi ulang. Gold yang telah direview kemudian dapat diberi `review_status: approved` oleh proses revisi yang mencatat reviewer dan alasannya. Artifact lama dipertahankan.

## Empat keputusan manusia dan pemeriksaan otomatis

| Komponen review | Yang disepakati |
|---|---|
| benchmark | Makna soal/gold, kontrak hasil, rubric dan pemisahan pilot/utama |
| metadata | Deskripsi, business context, sumber, coverage dan tidak adanya petunjuk khusus soal |
| generation | Satu model final, prompt, sampling, context dan bukti pilot model tersebut |
| analysis | Protokol analisis, asumsi, unit berpasangan dan keterbatasan |

Integrity ledger, jumlah trial, hash hasil/prompt, kecocokan backend, snapshot, database dan runtime source diperiksa otomatis. Tidak diperlukan approval manusia tambahan hanya untuk mengulang pemeriksaan mekanis tersebut. Main freeze tetap memerlukan semua pemeriksaan dan keempat review sesuai hash final.

## Bahan bimbingan statistik

Rancangan pada `docs/analysis-plan.md` masih proposal: skor per question–scenario adalah successes/5; paired permutation sebagai omnibus; enam paired contrasts dengan Holm; paired question bootstrap berstrata kompleksitas untuk confidence intervals dan effect sizes dalam percentage points.

Hal yang perlu ditanyakan saat bimbingan: kelayakan exchangeability, interpretasi benchmark yang dipilih secara tetap, banyaknya tied/discrete scores, multiplicity, dan batas generalisasi. Ketidaksignifikanan tidak membuktikan ekuivalensi. Panjang metadata dicatat sebagai bagian paket treatment. Jangan mengganti metode setelah melihat hasil utama.

## Keluaran yang diperlukan dari reviewer

- CSV/catatan yang berisi keputusan dan alasan untuk item yang diperiksa.
- Identitas peneliti dan dosen/rekan yang mereview serta tanggal review.
- Daftar perubahan yang disepakati atau konfirmasi tidak ada perubahan.
- Keputusan model final dan hasil pembahasan protokol statistik, bila sudah dibahas.

Jika review belum selesai, status tetap pending. Pengujian offline, token budget dan dokumentasi dapat dilanjutkan tanpa memberi approval semu atau menjalankan main trial.
