# Revision-03: pertanyaan alami dan column-order invariant EX

Perubahan ini memenuhi koreksi peneliti tentang pertanyaan yang terlalu mengarahkan projection, cakupan ordering/top-k dan kesetaraan hasil dengan posisi kolom berbeda. Judul skripsi serta delapan tahap metodologi tetap.

## Instrumen

- 30 pertanyaan Indonesia, 10 simple/10 medium/10 complex; canonical Spider levels 10 easy/10 medium/5 hard/5 extra.
- Tidak ada footer `Keluaran`, daftar identifier teknis, nama `table.column`, atau instruksi clause SQL pada soal. Output bisnis diminta dalam kalimat alami agar tugas tetap dapat dinilai secara jelas. Parameter filter, tanggal, ambang dan peringkat merupakan maksud tugas, bukan bocoran solusi.
- Definisi domain tetap dalam frozen metadata yang sama. Istilah `home store` dipertahankan karena sudah didefinisikan di metadata; tidak diganti dengan parafrasa yang mengubah makna menjadi lokasi transaksi atau pendaftaran.
- Q128 meminta daftar tarif berurutan, Q141 top1 staf menurut pembayaran lintas pemroses, Q152 top10 pelanggan menurut keragaman kategori lalu judul. Pemilihan tiga perubahan scope ini berdasarkan celah cakupan, bukan hasil EX.
- Q154 diperjelas menjadi kategori film yang pernah dibintangi pemeran sesudah blind reviewer menemukan kemungkinan penafsiran Cartesian product. Hubungan bisnis diminta dalam bahasa alami, tanpa memberitahu join path.
- Enam soal domain dan tiga keluarga aturan Sakila dipertahankan. Profil kebutuhan: 10 schema mapping, 14 local semantics, 6 domain integration.
- Technical schema, 106 annotation targets, empat snapshot DataHub/MCP, database, satu model dan decoder tetap menjadi kontrol bersama. Tidak ada gold, kontrak private, ID soal atau label complexity pada request model.

Instrumen aktif ada pada `data/benchmarks/revision-03/`, prompt `prompts/generation-v3.txt`, config `configs/revision03.toml`. Dataset/gold revision-02, prompt v2, snapshots dan hasil lama tetap diarsipkan. Perubahan wording/prompt/comparator memerlukan run baru; hasil lama tidak dianggap hasil revision-03.

## Evaluator

Urutan dan alias kolom tidak memengaruhi EX jika ada satu global bijective mapping yang menyamakan seluruh hasil. Duplikasi dan pasangan nilai antar kolom tetap dijaga. Urutan baris diperiksa untuk soal ordering/ranking; tidak dipaksakan untuk soal lain. Detail ada di [protokol evaluasi](evaluation-protocol.md).

`GoldReference.column_order` default `fixed` menjaga kompatibilitas v1/v2. Semua gold v3 memilih `permutation` secara eksplisit; manifest, runner dan auxiliary replay memeriksa kesamaan policy. Mapping tercatat per trial, dan integrity audit menolak correct v3 outcomes tanpa bijeksi lengkap. Jalur adjudication legacy tidak boleh dipakai untuk mengganti policy hasil lama.

Bug pembuatan `question_attributes` diperbaiki: loader menghasilkan objek Question, sedangkan lookup private memakai string question_id. Regression test menggunakan bentuk data yang sebenarnya. Source-version equality gate tidak dilewati.

## Verifikasi yang telah dilakukan

30 reference A dan 30 reference B ditulis terpisah. B mengunci interpretasi question-only sebelum membaca metadata, tidak melihat gold A atau prediksi model, lalu mengunci references sebelum eksekusi. Kedua reference berhasil dan sepakat pada baseline plus delapan fixture cases. Seluruh 30 soal mempunyai observed witnesses untuk seluruh predeclared critical mutants, termasuk ranking/ties. Primary database tidak berubah.

Audit comparator independen memakai 16.896 exact cases, 256 mixed tolerant cases, named adversarial checks dan legacy comparisons. Unit tests juga meliputi swapped name/revenue, association corruption, global versus per-row mapping, duplicates, NULL, DATE, tolerance gold coordinates, top-k row ordering dan budget incidents. Bukti rinci lokal ada di `runs/revision-03/`; source publik tidak menyertakan prediksi/EX yang belum direview.

Human review masih pending. Belum ada generation revision-03 atau EX revision-03. Sebelum 600 requests, periksa ulang full prompt budgets dengan tokenizer aktual, siapkan pilot yang sesuai versi, freeze source/model/input manifests, serta verifikasi backend/sampler. Diagnostic lama bukan approval atas prompt baru. Tidak ada tambahan inference atau automatic rerun pada langkah perbaikan ini.

## Reproduksi pemeriksaan input

```bash
rtk proxy .venv/bin/python research/revision-03/prepare_manifest.py
rtk proxy .venv/bin/sakila-experiment instrument validate --config configs/revision03.toml --manifest data/benchmarks/revision-03/final-02/manifest.json --output runs/revision-03/offline-validation.json
rtk proxy .venv/bin/pytest tests/unit
```

Manifest mengikat evidence lokal yang asli; source repository saja tidak menggantikan independent review atau ingestion provenance. Untuk membangun ulang reference checks gunakan `research/revision-02/validate_references.py --data-directory data/benchmarks/revision-03 --mutations data/benchmarks/revision-03/mutations.json --fixture-definition research/revision-03/fixture_cases.json` dengan reference B, config dan output directory baru secara eksplisit. Jangan membuat receipt sukses tanpa pengujian.

Paket review manusia terbaru: [panduan](../../annotations/round-03/review-guide.md), stage-1-blind.zip dan stage-2-reference.zip. Keputusan reviewer tetap kosong; metadata S3 dan instruksi bersama disertakan untuk menilai makna tanpa melihat gold pada tahap pertama.
