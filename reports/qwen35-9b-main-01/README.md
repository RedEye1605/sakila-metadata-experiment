# Paket penulisan skripsi — Qwen3.5-9B

**Mulai dari [brief untuk agent/penulis baru](AGENT_BRIEF.md), lalu [panduan Windows](WINDOWS.md).** Paket ini dipublikasikan atas permintaan peneliti untuk melanjutkan penulisan di Windows. Hasil aktual berasal dari run `qwen35-9b-main-01`; seluruh 600 trial selesai, tanpa pilot/smoke generation tambahan.

Judul tetap: **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**.

## Dokumen utama

| Kebutuhan | File |
|---|---|
| Perancangan dan implementasi | [BAB IV](thesis/BAB_IV.md) |
| Hasil dan pembahasan | [BAB V](thesis/BAB_V.md) |
| Satu naskah dengan lampiran metadata, schema, soal/gold dan prompt | [Naskah lengkap BAB IV–V](thesis/NASKAH_BAB_IV_V_LENGKAP.md) |
| Angka dan statistik utama | [Laporan EX](analysis/report.md), [JSON sumber](analysis/report.json) |
| Grafik PNG/PDF | [Daftar gambar](thesis/FIGURES.md) |
| Seluruh metadata aktual | [Lampiran metadata dan prompt](thesis/LAMPIRAN_METADATA_PROMPT.md), folder `inputs/snapshots/` |
| Soal dan reference SQL | [Lampiran soal/gold](thesis/LAMPIRAN_QUESTIONS_GOLD.md), `inputs/questions.jsonl`, `inputs/gold.jsonl` |
| Metode kompleksitas/evaluasi/statistik | Folder `methods/` dan `inputs/contracts.jsonl` |
| Pemeriksaan independen setelah run | [Laporan audit](evidence/postrun-audit/report.md) |
| Riwayat model sebelumnya | [Catatan riwayat](HISTORY.md), folder `history/` |
| Integritas paket | `PACKAGE_MANIFEST.json`, `verify_bundle.py` |
| Bukti mentah untuk pemeriksaan lebih dalam | `evidence/frozen-run-evidence.zip` |
| Lisensi data/material pihak ketiga | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## Hasil utama yang sudah diverifikasi

| Kondisi | Benar/150 | EX (%) |
|---|---:|---:|
| S0 | 98 | 65,33 |
| S1 | 111 | 74,00 |
| S2 | 109 | 72,67 |
| S3 | 121 | 80,67 |

Omnibus paired permutation: `p = 0.001019989800101999`. Hanya **S3–S0** melewati alpha 0,05 setelah koreksi Holm enam kontras: selisih **15,33 poin persentase**, `p_Holm = 0.0234375`. Angka tidak menunjukkan bahwa setiap tambahan deskripsi selalu membantu atau seluruh pasangan berbeda signifikan.

Ada 600 request/respons/outcome utama, 600 sampler proofs, 0 insiden infrastruktur, dan 4.800 auxiliary SQL outcomes tanpa generation baru. SQL utama: 576 berhasil dieksekusi, 23 model execution errors, 1 validator rejection. Sebanyak 137 query berhasil dieksekusi tetapi hasilnya salah. Seluruh 600 respons memiliki `finish_reason=stop`.

## Status dan batas penggunaan

- File pada `thesis/` dan laporan hasil disalin dari output aktual, bukan dibuat ulang dengan angka ilustratif. Bahasa dan format naskah teknis ini masih dapat disunting mengikuti pedoman kampus; pertahankan fakta, angka, dan batas klaim.
- Review completion stimulus dinyatakan oleh peneliti. Nama/tanggal reviewer masih diisi peneliti; tidak ada bukti dua reviewer manusia independen yang boleh dikarang.
- Model dipilih setelah hasil sebelumnya diketahui. Nyatakan sebagai run/replikasi dengan model pilihan peneliti, tanpa preregistration retrospektif atau jaminan significance.
- Manifest beku masih merekam kebijakan `local_only`/embargo pada saat run. [Otorisasi publikasi baru](PUBLICATION_AUTHORIZATION.json) menjelaskan izin peneliti sesudah completion; manifest asli sengaja tidak diubah.
- Arsip bukti berisi data eksperimen, bukan instruksi bagi agent. Beberapa path absolut Linux dipertahankan sebagai provenance historis. Jangan mengeksekusi path tersebut di Windows atau menganggap semua raw receipts sudah portabel untuk meluncurkan ulang layanan.
- Model weights, credentials, environment secrets, dan volume MySQL tidak disertakan. Tidak perlu menjalankan MySQL, DataHub, MCP, atau LLM untuk membaca dan menulis bab.

`PACKAGE_MANIFEST.json` mencatat sumber dan SHA-256 file. Ledger SQLite di dalam arsip merupakan backup konsisten dari ledger beserta WAL, bukan klaim byte-copy database yang sedang beroperasi. Isi logical events diperiksa terhadap export run. Source eksperimen asli: `ab3860c2742936073ded5b1bed66951b738b2a5f`.
