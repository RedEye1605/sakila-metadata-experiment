# Panduan anotator independen

Tujuan: menilai kebenaran dan kejelasan benchmark serta anotasi metadata. Ini bukan penilaian apakah model berhasil menjawab. Hasil model berada dalam embargo selama review.

1. A01 dan A02 mengerjakan salinan folder masing-masing secara independen. Jangan melihat isian anotator lain, SQL prediksi, EX, atau laporan error model sebelum submit.
2. Baca schema.json, pertanyaan, draft gold, kontrak hasil dan sumber metadata. reference/review-guide.md memuat cuplikan hasil referensi bertipe. Keberhasilan SQL dieksekusi tidak otomatis membuat maknanya benar.
3. Isi setiap criterion dengan yes, no, atau uncertain. Isi decision dengan accepted, revise, rejected, atau uncertain. Pending berarti belum dikerjakan. Accepted mensyaratkan seluruh criterion yes tanpa usulan perubahan.
4. Tulis usulan pada proposed_*; jangan mengganti teks sumber, ID, kontrak atau hash. Tulis alasan di notes, terutama untuk keputusan selain accepted. Isi annotated_at_utc dengan ISO 8601 bertimezone, misalnya 2026-10-27T12:00:00Z (gunakan tanggal sebenarnya).
5. Soal: periksa makna Indonesia, answerability, JOIN/aggregation grain, NULL, duplikat, kolom, ordering/ties, gold SQL, complexity dan paraphrase overlap antara pilot/utama. Simple tanpa JOIN/group/subquery; medium memakai JOIN/group/HAVING tanpa struktur complex; complex memakai subquery/CTE/window/set operation atau sedikitnya tiga JOIN.
6. Metadata: short dan detailed dinilai terpisah. Periksa fakta, unit, nullability, peran FK, sumber dan tidak adanya SQL solusi/petunjuk khusus soal. Banyaknya deskripsi tidak otomatis berarti kualitas lebih baik. Istilah bisnis harus grounded dan bindings relevan.
7. Setelah kedua submission selesai, peneliti/adjudikator membahas konflik. Jangan mengubah soal atau anotasi untuk meningkatkan skor model. Koreksi harus berdasarkan makna dan sumber.

Kirim CSV melalui kanal yang ditetapkan peneliti. Simpan identitas asli di luar paket public; gunakan A01/A02 pada isian. Program konsolidasi tidak membuat persetujuan final dan tidak mengubah gold/snapshot.
