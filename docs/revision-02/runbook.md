# Menjalankan instrumen revision-02

Input akhir ada pada `data/benchmarks/revision-02/final-02`. Evidence MCP dan independent reviews tetap terikat hash pada workspace lokal `runs/revision-02`. Manifest ini bukan self-contained public result archive; menyalin source repository saja tidak menghasilkan receipt review atau ingestion baru. Regenerasi evidence harus memakai proses yang didokumentasikan, bukan membuat status approval.

Periksa tanpa menyalakan layanan atau mengirim generation:

```bash
rtk proxy .venv/bin/python research/revision-02/run_experiment.py --dry-run --directory runs/revision-02/experiment-01
```

Driver memvalidasi seluruh artifact paths/hashes, source/runtime locks, metadata provenance, reference/fixture proofs, pilot review dan controlled renderings. Ia tidak memperbaiki soal atau SQL.

Jalankan hanya pada source/Git commit yang sudah dikunci:

```bash
rtk proxy .venv/bin/python -u research/revision-02/run_experiment.py --directory runs/revision-02/experiment-01 --allow-unreviewed
```

Flag tersebut secara eksplisit mengakui hasil exploratory terhadap draft. Human review tetap pending. Driver menolak DataHub yang masih berjalan, menghentikan clone fixture sebelum inference, memverifikasi backend/model/context, membekukan dan menjalankan 180 diagnostic trials, mengaudit completion/sampler, lalu membekukan dan menjalankan 600 benchmark trials. Hasil diagnostik tidak dipakai untuk memilih input atau menghentikan run berdasarkan accuracy. Semua parameter tetap.

Sesudah 600 outcomes lengkap, driver membuat primary EX/paired analysis dan diagnostic descriptive analysis. Inference dihentikan sebelum menjalankan delapan auxiliary cases atas SQL tersimpan; tidak ada generation tambahan untuk robustness. Semua outputs berada lokal:

| Path relatif terhadap directory run | Isi |
|---|---|
| `driver-events.jsonl` | Stage dan progress, tanpa score-based gating |
| `backend/verification.json` | Model, image, template dan actual runtime evidence |
| `diagnostic/` | 180 assignments, freezes, ledger, responses dan results |
| `benchmark/` | 600 assignments dan bukti yang sama |
| `analysis/benchmark/report.md` | Laporan EX utama, paired comparisons dan profile descriptives |
| `analysis/diagnostic/report.md` | Empat planned descriptive contrasts |
| `auxiliary/report.json` | Robustness terpisah pada delapan cases |
| `pipeline-completion.json` | Ada hanya jika seluruh pipeline selesai |

Pada gangguan, driver berhenti dan tidak mengubah infrastructure failures menjadi EX nol. Resume dilakukan dengan perintah eksplisit yang sama dan source/inputs identik. Stored responses dipakai kembali; model failures yang sudah terminal tidak digenerate ulang. Ambiguous dispatch memerlukan incident recovery yang tercatat. Jangan mengedit source, melakukan commit baru, mengganti model, atau mengubah analysis protocol di antara diagnostic dan benchmark; manifest akan menolak perbedaan source.

Read-only SQL policy, locale, timeouts dan result bounds sama pada primary serta auxiliary. Semua kelas complexity dan information need merupakan label sebelum generation. Domain tasks tidak diperlakukan sebagai enam keluarga independen: hanya tiga keluarga aturan resmi. Analisis masih conditional pada 30 soal, satu model dan reference draft.
