# Kebijakan publikasi dan otorisasi paket penulisan

## Otorisasi terbaru — paket Windows

Peneliti secara eksplisit meminta BAB IV–V, laporan aktual, dan bahan yang berguna untuk agent penulis berikutnya di-commit dan di-push untuk perpindahan ke Windows. Otorisasi ini berlaku untuk curated export di [`reports/qwen35-9b-main-01`](../reports/qwen35-9b-main-01/README.md), termasuk CSV/JSON EX/statistik, grafik, stimulus, metode, audit dan arsip bukti yang telah dipindai. Pernyataan dan cakupannya dicatat dalam [authorization receipt](../reports/qwen35-9b-main-01/PUBLICATION_AUTHORIZATION.json).

Manifest asli yang merekam `local_only`/embargo tidak diubah; izin yang lebih baru mengatur publikasi salinannya. Paket tidak mengklaim review manusia baru. Review completion tetap researcher-attested; reviewer identity/date belum diberikan. Riwayat pemilihan model sesudah hasil terdahulu diketahui dan hasil nonsignifikan tetap diungkapkan. Menghapus file di kemudian hari tidak menghapusnya dari riwayat Git.

Export tidak menyertakan credentials, `.env`, model weights, volume MySQL atau submission/identitas reviewer privat. Scanner memeriksa isi plaintext dan setiap entry ZIP sebelum publikasi. Portable verifier memeriksa hash dan hitungan hasil; deep verifier membaca ledger backup konsisten dan menghitung ulang analisis offline, tanpa generation atau database access. `.gitignore` tetap melindungi raw `runs/` dan folder privat.

## Kebijakan default untuk artifact lain dan riwayat sebelum otorisasi

Source, protokol, dokumentasi, diagram, pertanyaan/gold **draft**, spesifikasi metadata dan template anotator boleh dipublikasikan. Label draft harus dipertahankan. Persetujuan visibilitas public tidak dianggap sebagai persetujuan ilmiah.

Sebelum otorisasi terbaru, prediksi model, respons mentah, skor EX aktual, p-values, grafik hasil dan log runtime ditahan lokal. Artifact yang tidak termasuk curated export tetap mengikuti kebijakan default tersebut. Credentials dan submission anotator privat selalu dikecualikan. CI memakai fixture sintetis dan database resmi, tanpa generation LLM.

`runs/`, `secrets/`, `downloads/`, `reports/local/`, `docs/private/`, `annotations/submissions/` dan `annotations/identities/` diabaikan Git. Review staged diff dan jalankan `python infra/publication.py` sebelum commit. Audit menampilkan nama aturan/path tanpa mencetak secret yang cocok. Audit otomatis tidak menggantikan pemeriksaan isi naskah.

Snapshot distribusi mempertahankan bytes/hash payload asli. Path provenance dijadikan relatif; manifest view mencatat `distribution_view=true` dan hash manifest lokal asli. View bukan bukti retrieval baru. Bukti MCP asli tetap disimpan untuk audit/replay terkontrol. Jangan mengubah artifact eksperimen beku demi merapikan repository.

Submission A01/A02 dibuat tanpa melihat keluaran model. Identitas asli disimpan privat. Setelah keduanya lengkap, adjudikasi dicatat dengan tanggal, alasan, versi sumber dan hash. Fixture sintetis pada tests bukan bukti review manusia.

Publikasi hasil memerlukan audit setelah review: provenance, lisensi, identitas, koreksi gold, generation inputs yang tetap/berubah, serta label pendahuluan/final. Hasil tidak otomatis menjadi konfirmatori setelah review karena hasil pendahuluan telah dilihat. Ungkapkan urutan kegiatan dan setiap perubahan post hoc.

Token yang pernah dikirim melalui percakapan tidak dipakai untuk repository ini. Autentikasi memakai credential manager yang sudah tersedia; jangan memasukkan token ke URL remote atau source. Rotasi token yang terpapar dilakukan melalui pengaturan akun pemilik.
