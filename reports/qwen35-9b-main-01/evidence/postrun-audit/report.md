# Audit post-run independen Qwen3.5-9B

**Hasil: LULUS pemeriksaan yang ditugaskan**. Audit ini unblinded dan read-only; tidak ada inference, SQL, monitor loop, perubahan source/service/input/hasil, atau pengujian statistik baru.

Source frozen dan HEAD: `ab3860c2742936073ded5b1bed66951b738b2a5f`. Manifest SHA256: `c067be50240912f23d625a8c0080bbd497a8d1f4ba7509a2c3c4b17520543d1d`.

| Kondisi | Benar/150 | EX | Primary + seluruh8 auxiliary (strict9) |
|---|---:|---:|---:|
| S0 | 98 | 65.33% | 89/150 (59.33%) |
| S1 | 111 | 74.00% | 105/150 (70.00%) |
| S2 | 109 | 72.67% | 98/150 (65.33%) |
| S3 | 121 | 80.67% | 108/150 (72.00%) |

Independent omnibus: 101 inclusive exceedances /100000 draws, PCG64DXSM seed2026102802, plus-one p=0.001019989800102; integer statistic4268. Cocok laporan.

| Kontras | Selisih pp | Exact numerator /2^30 | p exact | p Holm |
|---|---:|---:|---:|---:|
| S1 - S0 | 8.666667 | 67108864/1073741824 | 0.0625 | 0.25 |
| S2 - S0 | 7.333333 | 130023424/1073741824 | 0.12109375 | 0.328125 |
| S3 - S0 | 15.333333 | 4194304/1073741824 | 0.00390625 | 0.0234375 |
| S2 - S1 | -1.333333 | 872415232/1073741824 | 0.8125 | 0.8125 |
| S3 - S1 | 6.666667 | 117440512/1073741824 | 0.109375 | 0.328125 |
| S3 - S2 | 8.000000 | 33554432/1073741824 | 0.03125 | 0.15625 |

Seluruh30 question blocks, termasuk zeros/ties, dipertahankan; exact whole-question sign flips, inclusive two-sided tail dan family Holm enam contrasts. Bootstrap10000 stratified question draws mengikuti substream seed2; seluruh pointwise CIs cocok report dalam1e-12. **Hanya S3−S0 lolos Holm alpha0.05**; omnibus<0.01. Tidak memilih ulang tes atau mengubah skor.

Ledger dan export:1800 events,600 request_started,600 response_received,600 unique terminal outcomes; attempt1 seluruhnya,0 infrastructure/retry/recovery events;600 response IDs unik. audit_run lulus. Ada600 sampler proofs yang mengikat actual outcome/model/backend/seed/settings;600 distinct slot task IDs. Per-request exact integer seed dan cache0 terverifikasi. Semua600 finish_reason=stop; token/cache usage konsisten.

SQL status: `{'success': 576, 'model_error': 23, 'rejected': 1}`; error codes `{'1064': 1, '1690': 3, '1054': 14, '1052': 3, '1066': 2}`; validator `{'accepted': 599, 'parse_error': 1}`. Ada23 model SQL errors dan1 validator rejection, bukan24 infrastructure failures. Detail lengkap pada receipt.json. Tidak dilakukan SQL ulang atau human correctness review.

Seluruh144 source files cocok manifest, current bytes, dan frozen git commit. Amendment scope/config/model/prompt/questions/gold/contracts/metadata hashes cocok; semua120 prompts direkonstruksi identik. Physical GGUF5,680,522,464 bytes di-hash ulang dan cocok model03b74727…52b7e8. Frozen model/source identities stabil. Database baseline schema/data hashes cocok manifest serta main/aux completion unchanged receipts; **tidak ada fresh DB query** untuk mengulang fingerprint.

Auxiliary:4800 unique trial×case outcomes lengkap untuk600 SQL×8 cases; per-file hashes/index, gold/results, original SQL/gold hashes, fixture specification/data hashes, source manifest/trials/source version bindings cocok. By-case dan scenario report totals cocok. All8-only counts `{'S0': 89, 'S1': 105, 'S2': 98, 'S3': 108}` kebetulan sama dengan independent primary+8 strict9 `{'S0': 89, 'S1': 105, 'S2': 98, 'S3': 108}`; tidak ada primary-fail yang lolos semua8. Primary pass yang gugur di strict9: `{'S0': 9, 'S1': 6, 'S2': 11, 'S3': 13}`. Primary EX tetap tidak diganti.

Thesis index:17/17 file hashes cocok, termasuk combined manuscript dan lampiran metadata, serta10 PDF/PNG figures. Index terikat main manifest/source yang benar. Ini byte-integrity check, bukan visual-layout atau editorial acceptance review.

Pemilihan Qwen3.5-9B setelah hasil main lama dan candidate pilot tercatat dalam amendment/manifest/BABIV dan report; bukan seleksi prospektif sebelum seluruh hasil sebelumnya. User secara eksplisit meniadakan pilot/smoke tambahan, jadi tidak ada alasan menjalankannya sekarang. Hash-bound prior main600 dan candidate pilot96 history tetap tersedia. Review completion adalah user attestation; identitas/tanggal reviewer masih pending dan tidak dinaikkan menjadi signed independent human review.

Batas kesimpulan: fixed30 purposively selected questions, repeated measures, asumsi label exchangeability/paired-swap invariance, pointwise bootstrap composition sensitivity, finite8 constructed witnesses. Model/inference package dipilih setelah hasil terdahulu; hasil ini tidak membuktikan pure model-size effect, universal semantic equivalence, ataupun generalisasi bisnis lintas database. Audit ini hanya memeriksa integritas bukti dan perhitungan yang sudah ditetapkan.

Seluruh actual checks, error details, hashes, statistik independen dan batas verifikasi tersimpan pada receipt.json.
