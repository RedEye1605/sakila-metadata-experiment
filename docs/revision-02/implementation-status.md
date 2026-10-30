# Status implementasi revisi — 28 Oktober 2026

Input revisi sudah dibekukan dan dry-run controller lulus. **Belum ada laporan EX revision-02 pada checkpoint pra-generation ini.** Hasil preliminary-01, sumber aslinya, dataset lama dan metadata lama tetap dipertahankan. Eksekusi berikutnya harus mengikuti [runbook](runbook.md), tanpa mengubah input berdasarkan hasil.

## Bukti yang sudah tersedia

| Komponen | Status dan bukti lokal |
|---|---|
| Rubric SQL | Adapter MySQL terhadap pinned Spider source; 19 oracle cases dan boundary tests |
| Metadata utama | `runs/revision-02/metadata/preparation-03`: 4 kondisi, 2 ekspor MCP per kondisi, technical schema/coverage/additivity lulus |
| Deskripsi | 106 elemen; 74 short/detailed sama; tiga kartu domain executable-source-based |
| Pool pertanyaan | 60 kandidat; 54 telah memiliki independent reference B; 6 filter tambahan menunggu follow-up |
| Reference/fixtures | `runs/revision-02/reference-checks-05`: baseline + 8 variations untuk versi 54 kandidat/fixture v4; defects dan exclusions dipertahankan |
| Proposal benchmark | `runs/revision-02/selection-proposal-02`: 30 soal, 10–10–10; raw 10/10/5/5; conditional, belum eligible |
| Pilot | 12 soal; 11 reference lama tetap, P101 diubah untuk mengatasi word-boundary ambiguity dan perlu follow-up |
| Diagnostik metadata | `runs/revision-02/diagnostic-renderings-01`: A/B/C dari MCP, dua rotasi B tercatat |
| Kecocokan token | Annotation A 2.846, B 6.358, C 6.377; B/C berbeda sekitar 0,30% |
| Kelayakan context | `runs/revision-02/context-preflight-01.json`: 240 candidate prompts + 60 diagnostic prompts, maksimum 8.911 input tokens; tanpa generation/truncation |
| Runner | Mode diagnostic, freeze, manifest binding, resolved request logging, safe resume dan complete-design audit diimplementasikan |
| Evaluasi | Kontrak DATE/numeric v2 dan auxiliary SQL replay diimplementasikan; primary EX lama tidak diganti |
| Analisis | Exact sign flips untuk enam primary contrasts; diagnostic paired descriptive bootstrap diimplementasikan |
| Verifikasi kode | Checkpoint 200 tests lulus termasuk integration MySQL; perubahan berikutnya harus diperiksa lagi sebelum freeze |
| Review manusia | Blank forms dan panduan pada `runs/revision-02/reviews/proposal-02`; seluruh keputusan belum diisi |

Token counts merupakan hasil tokenizer backend aktual, bukan perkiraan usage inference. Reference execution checks merupakan pengujian gold, bukan EX model. Pengujian 54 kandidat tidak diklaim mencakup versi 60 kandidat atau fixture v5.

## Penutupan gate sebelum generation

Independent reference follow-up menyelesaikan enam soal baru dan pilot pengganti. Fresh complete-input audit mencakup 60 soal dan 196 proposisi; targeted follow-up menahan tiga home-store population requests. Runtime audit mereproduksi empat gate defects, kemudian independent follow-up menutup keempatnya dengan positive/negative synthetic controls.

Freeze aktif: `data/benchmarks/revision-02/final-02`. Seluruh 30 soal terpilih dan 12 pilot mempunyai reference agreement, successful execution dan distinguishing witnesses pada primary + 8 fixture v6. Main allocation tetap 10–10–10, raw hardness 10/10/5/5; information profiles akhir 10 schema mapping, 14 local semantics, 6 domain integration. Blank review packet terbaru ada pada `annotations/round-02`.

Kebijakan `mysql-readonly-v2` dan locale `en_US` diuji sebelum generation; v1 tetap tersedia. Semua 228 tests termasuk MySQL integration lulus pada checkpoint terakhir (`runs/revision-02/checks/pre-generation-final.xml`). Perubahan policy baru tidak diklaim mendapat sign-off independen ketika reviewer mencapai batas penggunaan; dokumentasi/tes native ada pada [SQL policy](sql-policy-v2.md).

Offline driver memvalidasi 180 diagnostic assignments, 600 benchmark assignments dan 8 auxiliary cases tanpa generation. Runtime/model verification serta freeze prompt budgets dilaksanakan lagi oleh driver sebelum dispatch. Tidak ada accuracy threshold untuk memulai atau melanjutkan benchmark.

## Riwayat gate terdahulu

1. Independent reference B untuk Q155–Q160 dan pengganti pilot P101.
2. Independent complete-input follow-up terhadap cutoff/zero pada metadata preparation-03, enam kandidat tambahan dan prompt final. Audit sebelumnya terhenti pada batas penggunaan sebelum laporan/receipt akhir selesai; tidak dianggap complete approval.
3. Reference/witness validation versi 60 kandidat pada baseline + delapan fixture v5, termasuk nominal tepat 10.00.
4. Final eligibility, detailed semantic contracts, source/provenance recheck, dan benchmark/diagnostic manifests. Proposal belum boleh dipromosikan hanya karena jumlah soal sudah 30.
5. Fresh runtime verification dan freeze 180 diagnostic assignments; kemudian audited completion serta sampler proof sebelum freeze 600 exploratory trials.
6. Setelah generation: log integrity, primary EX/paired analysis dan auxiliary replay. Hasil tetap lokal dengan label provisional serta human review pending.

Tidak ada gate bahwa S3 harus menang, EX harus meningkat, atau p-value harus signifikan. Bila hasil berlawanan dengan hipotesis, hasil tetap dilaporkan.

Daftar di atas merekam gate yang terbuka pada checkpoint sebelumnya. Evidence penutupnya adalah manifests/validation pada `final-02`, `reference-checks-08`, `pilot-reference-checks-02`, `information-reconciled-02` dan independent runtime follow-up. Hasil inference/evaluasi aktual tetap menunggu completion run; human review belum tersedia.

## File untuk penulisan

- `docs/bab-iv.md` bagian 4.12 membedakan implementasi revisi dari pendahuluan lama.
- `docs/revision-02/dataset-methodology.md` menjelaskan sumber benchmark, kriteria kompleksitas, sampling dan keterbatasan.
- `protocol.md`, `evaluation-protocol.md`, `analysis-plan.md`, serta `amendments.md` mencatat aturan sebelum generation revisi.
- `docs/ai-handoff.md` menjelaskan sumber mana yang boleh dipakai untuk BAB IV/BAB V dan melarang hasil atau approval rekaan.

Main experiment yang berstatus reviewed tetap belum tersedia. Peneliti mengizinkan exploratory scoring terhadap draft; izin tersebut tidak menggantikan review semantik manusia.
