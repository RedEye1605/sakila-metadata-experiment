# BAB V — HASIL DAN PEMBAHASAN

## 5.1 Kelengkapan dan integritas eksperimen

Bab ini disusun dari hasil aktual `qwen35-9b-main-01`,bukan simulasi atau hasil versi terdahulu. Seluruh600 assigned trials mempunyai terminal EX biner,150per kondisi, 200per complexity,30 pertanyaan dan 5 repetitions. Audit ledger/export, assignments, prompt/result hashes, request settings, model/source/snapshot identity serta fingerprint database berhasil. Primary database tidak berubah. Waktu outcome pertama `2026-10-29T15:23:27.674428+00:00` dan terakhir `2026-10-29T22:02:40.643890+00:00` memakai timestamp UTC.

Terdapat600 dispatch attempts dan0 infrastructure incidents pada benchmark. Incident tidak otomatis masuk EX nol. Jenis incident: `{}`. Tidak ada request pilot atau smoke tambahan; seluruh generation yang dijadwalkan adalah600trial utama. Review completion dilaporkan oleh peneliti; nama/tanggal reviewer masih perlu dilengkapi sesuai BAB IV. Tidak mengklaim dokumen review independen yang belum tersedia.

## 5.2 Execution Accuracy menurut kondisi metadata

| Kondisi | Benar | Trial | EX (%) | Selisih terhadap S0 (pp) |
|---|---|---|---|---|
| S0 | 98 | 150 | 65.33 | 0.00 |
| S1 | 111 | 150 | 74.00 | 8.67 |
| S2 | 109 | 150 | 72.67 | 7.33 |
| S3 | 121 | 150 | 80.67 | 15.33 |

Nilai EX tertinggi dalam benchmark tetap ini diperoleh S3, sebesar80.67%. Ini peringkat deskriptif dan tidak otomatis merupakan perbedaan signifikan. Penambahan anotasi dapat membantu, tidak mengubah hasil, atau mengganggu pilihan SQL. Kesimpulan tidak mensyaratkan S3 menjadi yang terbaik.

## 5.3 Hasil menurut kompleksitas

| Kondisi | Kompleksitas | Benar | Trial | EX (%) |
|---|---|---|---|---|
| S0 | complex | 19 | 50 | 38.00 |
| S0 | medium | 34 | 50 | 68.00 |
| S0 | simple | 45 | 50 | 90.00 |
| S1 | complex | 22 | 50 | 44.00 |
| S1 | medium | 40 | 50 | 80.00 |
| S1 | simple | 49 | 50 | 98.00 |
| S2 | complex | 19 | 50 | 38.00 |
| S2 | medium | 40 | 50 | 80.00 |
| S2 | simple | 50 | 50 | 100.00 |
| S3 | complex | 25 | 50 | 50.00 |
| S3 | medium | 46 | 50 | 92.00 |
| S3 | simple | 50 | 50 | 100.00 |

Setiap condition/complexity cell memuat10 pertanyaan×5 repetitions=50 trial. Label complexity merupakan profil canonical reference. Perbandingan ini deskriptif; pertanyaan kompleks tidak identik dengan kebutuhan domain, dan domain tasks tidak tersebar merata pada semua complexity levels.

## 5.4 Perbandingan berpasangan dan ukuran efek

Omnibus paired permutation menghasilkan p=0.00101999,dengan analysis seed2026102802. Hasil omnibus melewati ambang0,05 dalam model pengujian yang ditetapkan; penentuan pasangan tetap mengikuti enam kontras berkoreksi Holm.

| Kontras | Selisih EX (pp) | p exact | p Holm | 95% pointwise CI (pp) |
|---|---|---|---|---|
| S1 - S0 | 8.67 | 0.0625 | 0.25 | [1.33; 17.33] |
| S2 - S0 | 7.33 | 0.121094 | 0.328125 | [0.00; 15.33] |
| S3 - S0 | 15.33 | 0.00390625 | 0.0234375 | [6.67; 24.67] |
| S2 - S1 | -1.33 | 0.8125 | 0.8125 | [-6.67; 4.00] |
| S3 - S1 | 6.67 | 0.109375 | 0.328125 | [0.00; 14.00] |
| S3 - S2 | 8.00 | 0.03125 | 0.15625 | [2.67; 14.00] |

Enam kontras sudah ditetapkan sebelum main outcomes. Semua30 question blocks, termasuk tied/zero-difference blocks, dipertahankan. Tidak memilih uji berdasarkan p yang lebih kecil. Interval bersifat pointwise, bukan simultaneous confidence set dan bukan inversi exact tests. Bootstrap menunjukkan sensitivitas terhadap komposisi fixed benchmark di bawah resampling model; tidak menjadikan30 soal purposive sebagai sampel acak seluruh kebutuhan bisnis.

## 5.5 Konsistensi lima pengulangan

| Kondisi | Pertanyaan5/5benar | Pertanyaan0/5benar | Pertanyaan campuran |
|---|---|---|---|
| S0 | 16 | 7 | 7 |
| S1 | 20 | 5 | 5 |
| S2 | 20 | 6 | 4 |
| S3 | 20 | 2 | 8 |

Setiap baris merangkum30 pertanyaan. Konsistensi outcome berbeda dari identitas teks SQL: query berbeda dapat menghasilkan EX yang sama. Lima requests dapat menghasilkan SQL identik meskipun temperature positif. Kestabilan tidak diperlakukan sebagai tambahan jumlah pertanyaan independen.

## 5.6 Kebutuhan informasi dan aturan domain

| Kondisi | Profil | Pertanyaan | Trial | EX (%) |
|---|---|---|---|---|
| S0 | domain_integration | 6 | 30 | 6.67 |
| S0 | local_semantics | 14 | 70 | 74.29 |
| S0 | schema_mapping | 10 | 50 | 88.00 |
| S1 | domain_integration | 6 | 30 | 6.67 |
| S1 | local_semantics | 14 | 70 | 91.43 |
| S1 | schema_mapping | 10 | 50 | 90.00 |
| S2 | domain_integration | 6 | 30 | 10.00 |
| S2 | local_semantics | 14 | 70 | 90.00 |
| S2 | schema_mapping | 10 | 50 | 86.00 |
| S3 | domain_integration | 6 | 30 | 43.33 |
| S3 | local_semantics | 14 | 70 | 91.43 |
| S3 | schema_mapping | 10 | 50 | 88.00 |

Profil terdiri10 schema mapping,14 local semantics dan6 domain integration. Enam domain tasks berasal dari tiga keluarga aturan Sakila, bukan enam kebijakan independen. Profil berkaitan dengan complexity dan selection constraints; tidak digunakan untuk menambahkan significance tests baru. Efek paket metadata menggabungkan ketersediaan informasi, panjang, framing dan salience. Tidak mengklaim efek murni jumlah token atau kemampuan model-family tertentu.

## 5.7 Latency dan token

| Kondisi | Rerata inference (ms) | Median inference (ms) | Rerata SQL (ms) | Rerata input tokens | Rerata output tokens |
|---|---|---|---|---|---|
| S0 | 35034.28 | 27384.89 | 13.25 | 2652.20 | 609.03 |
| S1 | 37882.78 | 29221.23 | 13.61 | 4078.20 | 594.43 |
| S2 | 42598.20 | 29882.93 | 12.61 | 4567.20 | 656.86 |
| S3 | 43752.23 | 30933.09 | 12.17 | 4997.20 | 660.39 |

Inference latency dan SQL execution latency diukur terpisah. Ukuran ini mendukung pembahasan dan bukan target optimisasi utama. Missing values, bila ada, tercatat sebagai unavailable pada measurements.csv dan tidak diganti angka buatan. Peningkatan biaya token tidak dengan sendirinya membuktikan penyebab perbedaan EX. Load/thermal/system state pada satu mesin juga membatasi tafsir latency.

## 5.8 Kegagalan keluaran dan eksekusi SQL

| Kondisi | Error type | MySQL code | Jumlah |
|---|---|---|---|
| S0 | sql_model_error | 1054 | 2 |
| S1 | sql_model_error | 1052 | 1 |
| S1 | sql_model_error | 1054 | 3 |
| S1 | sql_model_error | 1066 | 1 |
| S2 | sql_model_error | 1052 | 1 |
| S2 | sql_model_error | 1054 | 4 |
| S2 | sql_model_error | 1066 | 1 |
| S3 | sql_model_error | 1052 | 1 |
| S3 | sql_model_error | 1054 | 5 |
| S3 | sql_model_error | 1064 | 1 |
| S3 | sql_model_error | 1690 | 3 |
| S3 | sql_model_error | None | 1 |

Query yang berhasil dieksekusi tetapi hasilnya berbeda tetap salah; syntax/execution success bukan correctness. Jumlah success-but-wrong:137trial. Validasi SQL menolak statement yang tidak diizinkan; kegagalan model adalah outcome terminal dan tidak direpair. Pengelompokan kode error bersifat deskriptif. Penjelasan mekanisme berdasarkan contoh SQL adalah analisis kualitatif pascahasil dan tidak dipakai mengganti soal/metadata/model. Ledger menyimpan raw output dan extracted SQL agar contoh dapat diperiksa ulang.

## 5.9 Pemeriksaan pada delapan variasi data

Semua600 SQL tersimpan diuji pada8 cases,termasuk SQL yang gagal di primary. Tidak ada generation atau semantic repair baru. Tabel berikut menghitung kelulusan pada primary **dan** seluruh8 auxiliary cases, bukan mengganti primary EX dengan metrik lain.

| Kondisi | Trial | Lulus seluruh9cases | Persentase | Primary benar tetapi gagal auxiliary |
|---|---|---|---|---|
| S0 | 150 | 89 | 59.33 | 9 |
| S1 | 150 | 105 | 70.00 | 6 |
| S2 | 150 | 98 | 65.33 | 11 |
| S3 | 150 | 108 | 72.00 | 13 |

Wrong variants yang dideklarasikan sebelum generation membantu memastikan cases dapat membedakan unit/grain, role, NULL/zero, kalender, numeric boundary, ranking dan tie-breaking. Finite cases tetap tidak membuktikan ekuivalensi universal. Query dengan hasil kosong atau nilai yang kebetulan sama pada satu instance tetap berpotensi memperoleh primary EX1; hasil auxiliary memberi bukti pembeda tambahan.

## 5.10 Pembahasan dan batas generalisasi

Temuan utama harus dibaca sebagai pengaruh empat paket anotasi terhadap satu local model terkuantisasi, satu database Sakila beku dan30 pertanyaan terkurasi berbahasa Indonesia. Penelitian tidak mengisolasi efek bahasa, model size, quantization atau panjang token secara tersendiri. S1/S2 memiliki coverage yang sama dan sebagian descriptions identik; detail tambahan tidak tersebar merata pada seluruh elements. Efek rata-rata dapat menyembunyikan perbedaan antarpertanyaan.

Hasil eksplorasi/diagnostik versi lama tetap menjadi sejarah engineering; prompt, soal dan comparator berubah pada revision03. Selisih skor versi lama-versi baru tidak dapat diperlakukan sebagai efek metadata saja. Studi ini bukan preregistration retrospektif. Analisis main memakai rencana yang dikunci sebelum600 outcomes; seluruh kondisi, contrasts dan non-significant findings tetap dilaporkan.

Statistical nonsignificance bukan bukti tidak ada efek; significance juga tidak menjamin manfaat praktis atau generalisasi workload. Identitas/tanggal reviewer perlu ditambahkan peneliti, tanpa mengubah tanggal pencatatan atau mengklaim signed-review evidence yang belum ada. Koreksi stimulus sesudah hasil membutuhkan versi/generation baru; gold-only correction setelah adjudication harus dilaporkan sebagai turunan dan tidak menimpa original evidence.

## 5.11 Jejak audit dan bahan penulisan

Sumber tabel: `analysis/report.json`,CSV pendamping,benchmark manifest/ledger dan `auxiliary/outcomes.jsonl`. Question/gold/prompt/snapshot hashes berada dalam manifest. Lampiran pertanyaan dan gold disertakan terpisah untuk peneliti; gold tidak pernah masuk model prompt. Semua angka pada bab ini berasal dari artifacts lengkap yang lolos integrity audit. Reviewer tidak boleh mengganti angka dengan ilustrasi atau menyebut hasil model lain sebagai hasil run ini.
