# Review instrumen revision03

Paket memuat30pertanyaan/gold,106deskripsi dan3aturan domain. Seluruh keputusan dan identitas reviewer masih kosong. Tidak ada prediksi model atau skor EX.

1. Berikan questions-blind.csv dan generation-instruction.txt terlebih dahulu. Reviewer menulis interpretasi sendiri sebelum melihat reference. Baca technical schema dan definisi metadata yang relevan; bedakan pengetahuan yang hanya tersedia pada S3 dari maksud yang masih ambigu sesudah S3 lengkap. Simpan submission tahap pertama dengan hash/tanggal sebenarnya.
2. Berikan questions-reference.csv setelah tahap pertama dikunci. Periksa output bisnis, populasi/grain, filtering, waktu, duplikat, NULL dan rules. Output columns merupakan himpunan yang diminta dalam prose, bukan posisi teknis. Alternatif projection order dan aliases diperbolehkan. Urutan baris diperiksa hanya bila diminta. Baca konvensi ties/top-k pada prompt bersama.
3. Periksa annotations.csv dan business-terms.csv terhadap sumber resmi/executable source. Definisi harus membantu memahami domain secara umum, bukan memuat SQL recipe, gold atau jawaban per soal. Jangan mengganti metadata/soal karena model gagal atau suatu skenario menang.
4. Isi decision dengan accept/revise/reject/uncertain dan berikan alasan. Kolom kosong belum direview. Jika memungkinkan gunakan dua reviewer independen dan adjudication terdokumentasi. Jangan mengarang identitas, tanggal atau approval. Review sesudah generation dicatat sebagai post-run, bukan approval sebelumnya.

Nomor, nama, metrik dan filter yang diminta merupakan maksud laporan, bukan petunjuk SQL. Pertanyaan sengaja tidak memiliki footer schema identifiers. Gold dan kontrak private tidak dikirim ke LLM. Perubahan wording/prompt/metadata memerlukan versi dan generation baru. Gold-only correction setelah review harus menjadi laporan turunan yang dapat diaudit; approval tidak terjadi otomatis karena query berhasil dieksekusi.
