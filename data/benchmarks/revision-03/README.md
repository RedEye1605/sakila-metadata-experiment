# Input revision03

Entrypoint tervalidasi: `final-02/manifest.json`. Soal dan gold aktif masing-masing30baris pada `final-02/questions.jsonl` dan `final-02/gold.jsonl`. Versi baca manusia: `final-02/questions.md`. Kontrak private runtime ada di `final-02/contracts.jsonl`; tidak masuk prompt.

File root/candidates mempertahankan input authoring dan predeclared mutants; authoring cards memiliki catatan provenance tambahan dan bukan runtime contract. Manifest final mengikat independent interpretation, reference/fixture checks, source-based metadata dan protokol evaluasi. Human review tetap pending. Tidak ada hasil model/EX di directory ini.

Perubahan utama: tanpa footer output teknis, exact business output sets dalam prose, tiga ordered tasks termasuk dua top-k, dan column-order invariant EX. Lihat `docs/revision-03/README.md`, `prompts/generation-v3.txt` serta paket reviewer `annotations/round-03`.

Checkpoint `final-01` sebelum penguatan pengikatan witness evidence disimpan lokal dan tidak didistribusikan. Inputs semantik sama; source/evidence aktif menggunakan `final-02`.
