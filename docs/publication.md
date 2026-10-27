# Kebijakan publikasi dan embargo

Source, protokol, dokumentasi, diagram, pertanyaan/gold **draft**, spesifikasi metadata dan template anotator boleh dipublikasikan. Label draft harus dipertahankan. Persetujuan visibilitas public tidak dianggap sebagai persetujuan ilmiah.

Prediksi model, respons mentah, skor EX aktual, p-values, grafik hasil, log runtime, credentials dan submission anotator tetap lokal sebelum review. Jangan menempelkan hasil aktual ke issue, Actions artifact, README, commit message atau gambar repository. CI memakai fixture sintetis dan database resmi, tanpa generation LLM.

`runs/`, `secrets/`, `downloads/`, `reports/local/`, `docs/private/`, `annotations/submissions/` dan `annotations/identities/` diabaikan Git. Review staged diff dan jalankan `python infra/publication.py` sebelum commit. Audit menampilkan nama aturan/path tanpa mencetak secret yang cocok. Audit otomatis tidak menggantikan pemeriksaan isi naskah.

Snapshot distribusi mempertahankan bytes/hash payload asli. Path provenance dijadikan relatif; manifest view mencatat `distribution_view=true` dan hash manifest lokal asli. View bukan bukti retrieval baru. Bukti MCP asli tetap disimpan untuk audit/replay terkontrol. Jangan mengubah artifact eksperimen beku demi merapikan repository.

Submission A01/A02 dibuat tanpa melihat keluaran model. Identitas asli disimpan privat. Setelah keduanya lengkap, adjudikasi dicatat dengan tanggal, alasan, versi sumber dan hash. Fixture sintetis pada tests bukan bukti review manusia.

Publikasi hasil memerlukan audit setelah review: provenance, lisensi, identitas, koreksi gold, generation inputs yang tetap/berubah, serta label pendahuluan/final. Hasil tidak otomatis menjadi konfirmatori setelah review karena hasil pendahuluan telah dilihat. Ungkapkan urutan kegiatan dan setiap perubahan post hoc.

Token yang pernah dikirim melalui percakapan tidak dipakai untuk repository ini. Autentikasi memakai credential manager yang sudah tersedia; jangan memasukkan token ke URL remote atau source. Rotasi token yang terpapar dilakukan melalui pengaturan akun pemilik.
