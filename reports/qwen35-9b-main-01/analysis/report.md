# Laporan Execution Accuracy

Review completion declared by researcher; reviewer identities/date remain to be supplied. No independent signed-review claim. Researcher-selected Qwen3.5-9B replication after prior results; additional capability pilot and generation smoke explicitly waived. No retrospective preregistration or significant-result selection claim.

Experiment: qwen35-9b-main-01; evaluable trials: 600.

| Kondisi | Benar | Trial | EX (%) |
|---|---:|---:|---:|
| S0 | 98 | 150 | 65.33 |
| S1 | 111 | 150 | 74.00 |
| S2 | 109 | 150 | 72.67 |
| S3 | 121 | 150 | 80.67 |

| Kondisi | Kebutuhan informasi | Pertanyaan | Trial | EX (%) |
|---|---|---:|---:|---:|
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

Profil kebutuhan/keluarga berasal dari instrumen yang dibekukan. Subkelompok bersifat deskriptif, berkaitan dengan complexity, dan bukan tambahan pertanyaan independen.

Unit berpasangan adalah pertanyaan; lima pengulangan diagregasi per question–scenario.

Omnibus paired permutation p=0.00101999; seed=2026102802.

| Kontras | Selisih EX (pp) | p | p Holm | 95% paired CI (pp) |
|---|---:|---:|---:|---|
| S1 - S0 | 8.67 | 0.0625 | 0.25 | [1.3333333333333286, 17.33333333333333] |
| S2 - S0 | 7.33 | 0.121094 | 0.328125 | [0.0, 15.333333333333336] |
| S3 - S0 | 15.33 | 0.00390625 | 0.0234375 | [6.666666666666671, 24.66666666666668] |
| S2 - S1 | -1.33 | 0.8125 | 0.8125 | [-6.666666666666657, 3.999999999999986] |
| S3 - S1 | 6.67 | 0.109375 | 0.328125 | [0.0, 13.999999999999986] |
| S3 - S2 | 8.00 | 0.03125 | 0.15625 | [2.666666666666657, 14.0] |

Nonsignificance does not establish equivalence. Confidence intervals are pointwise. Draft-reference errors can change EX and all derived statistics.
