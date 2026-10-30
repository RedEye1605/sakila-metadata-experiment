# Eksekusi utama revision03

Peneliti menyatakan seluruh input telah direview dan meminta eksekusi end-to-end. Pernyataan dicatat sebagai `user_attested_complete`, terikat hash soal/gold/kontrak/anotasi/facts/protokol/prompt/snapshots. Nama reviewer dan tanggal review belum diberikan dan tidak diisi otomatis. Label draft pada file authoring lama dipertahankan sebagai sejarah; completion review yang dilaporkan dicatat terpisah dalam execution manifest dan outcomes.

Input eksekusi: `data/benchmarks/revision-03/execution-01/manifest.json`, config `configs/revision03-main.toml`. Schema/data, empat snapshot MCP, 30 soal, gold, prompt v3, comparator, decoder dan rencana analisis tidak berubah dari paket yang dinyatakan direview.

## Urutan yang dikunci sebelum generation

1. Validasi scope review dan semua input/source/reference/witness hashes; cek fingerprint Sakila.
2. Verifikasi model file/image/options/backend aktual dan12smoke contexts; periksa seluruh120main contexts dengan tokenizer sebenarnya. Tidak ada generation pada pemeriksaan ini.
3. Freeze dan jalankan3pertanyaan P201–203×4snapshot=12requests engineering. Ketiganya terpisah dari30soal utama; GoldB ditulis independen dan seluruh pasangan/mutants diperiksa pada baseline+8variations. Tidak ada EX threshold atau pemilihan model/soal berdasarkan score smoke.
4. Audit completion smoke, source/model/prompt/database/policy/snapshot identity dan actual sampler/seed/cache. Freeze semua main prompts/gold results dan manifest.
5. Jalankan30×4×5=600trial utama. Tiap assignment hanya satu kesempatan generation. Model failures terminal EX0; tidak ada repair, feedback error atau auto-retry. Infrastructure interruption dicatat terpisah; respons tersimpan dipakai kembali pada resume eksplisit.
6. Audit600outcomes dan jalankan analisis yang sudah ditetapkan (30question blocks,100k omnibus permutations,6exact contrasts+Holm,10kquestion bootstrap). Diagnostic180versi lama tidak diulang atau digabung sebagai main data.
7. Hentikan inference, replay seluruh600SQL tersimpan pada8fixture cases terisolasi. Primary EX tidak diubah dan tidak ada generation baru.
8. Buat BAB_IV.md, BAB_V.md, lampiran soal/gold/schema, figures dan input/output hashes dari hasil aktual yang lengkap. BABV ditolak jika600outcomes/4800auxiliary outcomes belum lengkap atau tidak cocok dengan manifest.

## Menjalankan

```bash
rtk proxy .venv/bin/python research/revision-03/run_experiment.py --directory runs/revision-03/main-01 --dry-run
rtk proxy .venv/bin/python -u research/revision-03/run_experiment.py --directory runs/revision-03/main-01
```

Source harus sudah committed dan working tree bersih sebelum freeze. Source/model/input yang sama digunakan smoke dan main; perubahan source setelah salah satu fase memerlukan versi/revalidasi yang tercatat, bukan melewati gate. Driver berhenti pada exception dan menulis incident stage. Completed trials tidak dihapus atau digenerate ulang. Raw response dan gold tidak pernah dimasukkan kembali sebagai prompt.

Hasil aktual dan naskah tetap lokal di directory run. Publication source tidak memuat model outputs/EX secara diam-diam. Setelah `pipeline-completion.json` terbit, seluruh tahap otomatis selesai. Identitas reviewer ditambahkan peneliti pada naskah/supplement terpisah tanpa mengubah artifact yang dipakai saat generation.
