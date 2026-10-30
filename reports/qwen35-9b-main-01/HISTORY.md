# Riwayat engineering dan batas pemakaian hasil

**Hasil utama untuk penulisan saat ini: `qwen35-9b-main-01`.** Folder `history/` disertakan untuk transparansi. Jangan menjumlahkan denominator antar-run, mengganti identitas model, atau menyalin tabel run lama sebagai hasil Qwen3.5-9B.

| Run | Model | Desain | Status pemakaian |
|---|---|---|---|
| revision03-main-01 | Qwen2.5-Coder-7B-Instruct Q4_K_M | 30 soal utama × 4 × 5 = 600 | Main sebelumnya, tetap diarsipkan |
| qwen3-8b-capability-01 | Qwen3-8B Q4_K_M | 12 soal baru × 4 × 2 = 96 | Engineering capability pilot, AI-assisted references, review manusia pilot baru pending |
| qwen35-9b-main-01 | Qwen3.5-9B Q4_K_M | 30 soal utama yang sama × 4 × 5 = 600 | Model kemudian dipilih langsung oleh peneliti; tanpa pilot/smoke generation tambahan |

Main Qwen2.5-Coder memperoleh S0/S1/S2/S3 = 83/97/95/92 dari 150; omnibus p sekitar 0,2592, seluruh p Holm pasangan = 1. Pilot Qwen3-8B memperoleh 10/12/12/13 dari 24 per kondisi dan tidak memenuhi engineering admission criteria. Dua hasil tersebut tidak dihapus atau dilabel ulang sebagai pilot bagi run baru.

Sesudah melihat hasil terdahulu, peneliti meminta pemeriksaan model lain. Kandidat kecil semula mencakup Qwen3.5-4B sebagai fallback sumber daya. Setelah membahas model card, benchmark eksternal, dan GPU 6 GiB, peneliti memilih Qwen3.5-9B, secara eksplisit meniadakan pilot/smoke generation tambahan, dan meminta 600 main trials. Qwen3.5-4B tidak dijalankan dan tidak boleh dilaporkan sebagai model yang sudah dievaluasi.

Amendment dan pernyataan peneliti tersedia pada `inputs/execution-amendment.json`. Pemilihan ini dilakukan setelah hasil sebelumnya diketahui, sehingga tidak diklaim sebagai model-selection protocol yang ditetapkan sebelum seluruh hasil terdahulu. Budget reasoning/output dan inference package berbeda dari main lama. Perbandingan antar-run tidak mengisolasi parameter count, model family, atau metadata saja.

Instrumen awal/preliminary dan diagnostik revision02 memakai versi pertanyaan/prompt/evaluator atau renderings berbeda. Angka 9 pilot, 12 pilot, 180 diagnostic, 96 capability pilot, dan 600 main merujuk desain berbeda. Untuk run Qwen3.5-9B ini, jumlah generation tetap tepat 600 dan hasil utama memakai 30 pertanyaan. Histori input/reference/source tetap dapat dilihat pada commit repository dan source locks.

Disclosure ini perlu tetap muncul pada uraian implementasi/limitations. Hasil baru dapat dilaporkan apa adanya dengan interpretasi bersyarat; jangan menyebutnya preregistration retrospektif atau membuang hasil lama karena tidak signifikan.
