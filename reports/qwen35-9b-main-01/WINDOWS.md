# Membuka paket dan melanjutkan penulisan di Windows

## Membaca dan menulis tanpa menjalankan pipeline

Unduh repository melalui GitHub **Code → Download ZIP**, lalu extract dengan File Explorer. Alternatif jika Git sudah terpasang, jalankan pada PowerShell:

```powershell
git clone https://github.com/RedEye1605/sakila-metadata-experiment.git
Set-Location sakila-metadata-experiment
```

Buka `docs/ai-handoff.md`, kemudian `reports/qwen35-9b-main-01/AGENT_BRIEF.md`. Berikan folder repository ini kepada agent baru, dengan instruksi: **lanjutkan penulisan dari evidence yang sudah selesai, tanpa generation/eksperimen baru**.

Untuk satu file konteks besar, gunakan `thesis/NASKAH_BAB_IV_V_LENGKAP.md`. Untuk penyuntingan terpisah, gunakan `thesis/BAB_IV.md` dan `thesis/BAB_V.md`. JSON/CSV hasil berada di `analysis/`. PNG dapat dibuka di Windows dan PDF dapat dimasukkan ke naskah sesuai pedoman kampus.

Tidak diperlukan Python, GPU, Docker, MySQL, DataHub, atau model file untuk membaca paket dan menulis bab. Jangan menjalankan script `run_experiment.py` untuk tugas penulisan.

Repository memakai `.gitattributes` agar bytes paket tidak berubah akibat automatic line-ending conversion saat checkout di Windows. Simpan hasil penyuntingan naskah sebagai salinan editorial; mengubah file evidence terindeks akan membuat pemeriksaan hash gagal. Jika mengekstrak arsip bukti, gunakan folder singkat seperti `C:\Research\audit` agar path tidak terlalu panjang. Arsip ZIP sekitar 40 MB, dengan isi sekitar 319 MB sebelum extract; lihat ukuran tepat pada manifest.

## Pemeriksaan checksum opsional

Jika Python 3.12 sudah tersedia, dari root repository:

```powershell
python .\reports\qwen35-9b-main-01\verify_bundle.py
```

Script ini menggunakan standard library, memeriksa hash semua file paket dan angka tabel utama; tidak memanggil model atau database. Untuk juga memeriksa setiap entry di dalam arsip bukti:

```powershell
python .\reports\qwen35-9b-main-01\verify_bundle.py --archives
```

Implementasinya diperiksa pada Linux; command PowerShell ini adalah panduan portabel, bukan klaim bahwa GPU backend/seluruh layanan penelitian sudah diuji pada Windows.

## Arsip bukti mentah

`evidence/frozen-run-evidence.zip` menyimpan original prompt/response/result/sampler/ledger, auxiliary outcomes, reference checks dan metadata receipts yang dikurasi. Ukuran sesudah extract jauh lebih besar daripada ZIP; sediakan ruang kosong sesuai `PACKAGE_MANIFEST.json`.

Struktur di dalam ZIP memakai path relatif repository. Buka pada folder kerja terpisah untuk audit; jangan menimpa versi editorial atau meluncurkan ulang eksperimen. Beberapa nilai path absolut `/home/rhendy/...` dalam JSON adalah rekaman lingkungan asli. Gunakan mapping/arsip atau dokumen paket; jangan mengganti bytes manifest beku agar path terlihat seperti Windows.

Ledger SQLite merupakan backup konsisten dari WAL melalui SQLite backup API. Semua event/outcome logical dibandingkan dengan export asli. File WAL/SHM asli, password, token, model weights dan volume MySQL tidak disertakan.

Apabila ingin menghitung ulang analisis offline dengan dependency project, gunakan script `research/publication/verify_windows_handoff.py --deep` dari repository setelah environment Python yang dipin disiapkan. Proses tersebut membaca archive dan menjalankan pemeriksaan/analisis atas hasil tersimpan; tidak menghasilkan SQL baru atau mengakses MySQL. Pembacaan naskah tidak memerlukan tahap ini.

## Checklist untuk agent penulis

- Pertahankan judul dan delapan tahap metodologi.
- Gunakan Qwen3.5-9B main 600 trial sebagai run saat ini, tanpa mencampur pilot/model lama.
- Gunakan p Holm dan confidence interval dengan batas interpretasi yang dijelaskan dalam brief.
- Cantumkan disclosure pemilihan model setelah hasil terdahulu dan waiver pilot/smoke.
- Lengkapi nama/tanggal reviewer hanya dari peneliti; sesuaikan format kampus/BAB I–III yang diberikan.
- Perlakukan naskah sebagai bahan teknis untuk disunting; jangan mengarang hasil atau mengubah evidence untuk mendukung cerita.

Paket ini dipublikasikan atas permintaan peneliti untuk perpindahan perangkat. Menghapus folder nanti tidak menghapusnya dari riwayat Git. Jangan menaruh credentials pada paket, chat agent, atau commit.

## Pesan yang dapat diberikan ke agent baru

> Baca AGENTS.md, docs/ai-handoff.md, lalu reports/qwen35-9b-main-01/AGENT_BRIEF.md. Bantu saya menyunting BAB IV Perancangan dan Implementasi serta BAB V Hasil dan Pembahasan berdasarkan run Qwen3.5-9B 600 trial yang sudah selesai. Naskah lengkap, angka aktual, gambar, metode, soal/gold, metadata dan bukti audit ada dalam paket tersebut. Pertahankan judul dan delapan tahap metodologi. Jangan menjalankan eksperimen baru, mengubah evidence, mengarang reviewer, atau menyembunyikan hasil tidak signifikan/riwayat pemilihan model. Saya akan memberikan pedoman kampus, BAB I–III serta identitas/tanggal reviewer yang sebenarnya.
