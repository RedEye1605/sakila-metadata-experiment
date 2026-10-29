# Project decision log

Thesis: **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**

| ID | Decision | Authority/status |
|---|---|---|
| D01 | MCP only during preparation; inference uses frozen snapshots | Approved design |
| D02 | All installed Sakila base tables and columns; exclude views/routines from model context | User confirmed |
| D03 | 30 questions, 10 per complexity, four conditions, five stochastic repetitions | User confirmed |
| D04 | Human review of gold semantics before main freeze | User confirmed |
| D05 | Official Sakila import into an isolated MySQL instance | User confirmed |
| D06 | Airflow workshop may be stopped temporarily; preserve volumes and restore prior running services | User confirmed |
| D07 | Positional output columns explicitly requested in questions; ignore aliases | User confirmed |
| D08 | S2 descriptions remain byte-identical in S3 | Approved design |
| D09 | Separate metadata tooling dependency environment from experiment runtime | Engineering default; avoids ingestion/parser conflicts |
| D10 | No generation retry for model errors; infrastructure attempts remain auditable | Approved design |
| D11 | Main experiment has no execution entrypoint until readiness gates are implemented and passed | Engineering safety gate |
| D12 | Candidate sampling values are pilot defaults, not frozen main configuration | Pending pilot verification |
| D13 | Paired permutation of per-question scores, six Holm-adjusted contrasts, question-level bootstrap | Proposed analysis protocol; freeze before main |
| D14 | Use DataHub environment DEV and platform_instance sakila-research | Installed ingestion SDK rejects the custom environment RESEARCH; verified via real configuration validation |
| D15 | Defer DataHub startup while user frees RAM; continue offline components | User confirmed; Airflow resource probe reached only 4.63 GiB available and restored all seven services |
| D16 | Reconcile native types in an audited ingestion intermediate before DataHub persistence | Real connector labeled address.location BLOB; installed MySQL reports geometry. Preserve raw output and correction receipt. Snapshots must still come from catalog through MCP |
| D17 | Keep all benchmark references draft until human review | User explicitly confirmed review is not yet complete |
| D18 | Resume DataHub feasibility after resource recovery | Environment recheck measured approximately 10.6 GiB available RAM; previous probe and restored Airflow state retained |
| D19 | DataHub Core v1.8.0 plus MCP server 0.8.0 is compatible for the required Sakila metadata | Live authenticated ingestion, MCP discovery, schema/descriptions/glossary definitions and bindings all verified; two independent exports per condition |
| D20 | Keep DataHub stopped while local inference runs | Preparation completed; preserved catalog volumes avoid RAM competition during inference |
| D21 | Qwen2.5-3B-Instruct Q4_K_M is the single feasibility candidate | Official revision/hash verified; actual GPU supports 16,384-token context; candidate remains unfrozen for main |
| D22 | Snapshot specification v2 corrects documentation URLs only | Archived v1; three official Sakila page paths preserve underscores. S1/S2 description wording unchanged |
| D23 | Analysis dependencies are an optional locked group | NumPy 2.5.4 and Matplotlib 3.11.2; descriptive pilot reporting does not run inferential tests |
| D24 | Main execution requires artifact-specific reviews and a separate freeze receipt | Supersedes D11's temporary absence of an entrypoint. Draft rejection verified before model preparation; approved main and pilot share runner/evaluator |
| D25 | Preserve preliminary feasibility evidence locally | Candidate checks are engineering activities; model selection never uses the 30 main questions or a favorable metadata effect |
| D26 | Test only one additional candidate, Qwen2.5-Coder-7B-Instruct Q4_K_M | User selected one bounded engineering check; all main conditions still use one final model |
| D27 | Semantic reviewers are the researcher with supervisor/peer | User confirmed; actual approvals remain pending |
| D28 | Near-term deliverable is pipeline plus BAB IV Markdown | User confirmed Markdown first; main 600 trials are a later milestone |
| D29 | Statistical protocol remains a proposal for supervision | User confirmed no supervisor decision yet; no invented approval |
| D30 | No new scored pilot or repetition requests while references remain draft | User explicitly reaffirmed pilot is not reviewed; hardware/context verification without generation is allowed |
| D31 | Four human review components; mechanical checks are automatic | Benchmark (including EX contracts/separation), metadata, generation and analysis; audit real pilot artifacts and selected-backend matches |
| D32 | Reproduction replays archived MCP exports on a fresh workspace/database | Fresh Python + official isolated MySQL import and identical snapshot payloads verified; not a claim of new DataHub ingestion |
| D33 | MySQL healthcheck must query the final TCP server | Cold-start found a temporary-socket readiness race; query SELECT 1 over TCP resolves it |
| D34 | Explicit provisional route supersedes D30 for the authorized preliminary run | User clarified reviews are incomplete and requested testing anyway; --allow-unreviewed never creates approval |
| D35 | Run one 36-trial 7B pilot, then a separately frozen 600-trial preliminary benchmark | Same fixed source/model/settings; complete pilot audit, backend-specific sampler proof and all 120 prompt budgets precede benchmark dispatch |
| D36 | A01/A02 review independently, followed by human adjudication | Each receives 152 items without predictions/scores; identities/dates not supplied and never fabricated |
| D37 | Keep public source/docs; embargo actual EX/predictions until review | Existing public repository authorized; keyring authentication used, exposed chat token not used or stored |
| D38 | Freeze paired permutation/Holm/bootstrap protocol before preliminary generation | User selected full EX and paired analysis; draft-reference statistics remain exploratory/conditional, not supervisor-approved final findings |
| D39 | Gold-only corrections may reuse stored prediction results | Require unchanged generation inputs/database and hash-bound complete adjudication; other treatment/question changes require new generation |
| D40 | Preserve exact local snapshots and publish explicit portable distribution views | Payload bytes/hashes unchanged; distribution manifest records original manifest hash and relative provenance paths |
| D41 | Generation and original analysis use frozen commit bb32938; review hardening merges only after completion | 600 responses/outcomes completed and audited before source changes; full data and model/snapshot hashes preserved |
| D42 | Bind rescore to exact adjudicated gold and frozen evaluation policy | Preserve six submission hashes, reject unrecorded corrections/complexity changes and database/comparator/protocol drift; no new inference |
| D43 | Compare integer sampler parameters exactly | Postrun inspection exposed float32 serialization differences; floats retain defined tolerance, large neighboring integer seeds must fail verification; actual final seed matched exactly |
| D44 | Latest reconstruction tests archived MCP replay in a new database/environment | publication-01 verified schema/data and all payload hashes with 144 tests; does not claim fresh catalog ingestion or regenerated model outputs |
| D45 | Preserve preliminary-01 and create a separate exploratory revision | User requested independent audit and redesigned questions/metadata; outcomes must not be selected for richer metadata to win |
| D46 | Use pinned Spider component rules and a separate information-need profile | Canonical structure gives 10/10/5/5 raw levels; source-feasible domain coverage is 0/2/4 across simple/medium/complex |
| D47 | Ground three S3 rule cards in executable official Sakila semantics | Stock, rewards and late component have global definitions; local field meanings remain in S1/S2; full customer balance is excluded |
| D48 | Exclude unresolved public targets and require independent reference witnesses | Final 30 and 12 pilot references agree on primary plus 8 fixture cases; home-store population ambiguities remain excluded rather than hidden in private gold |
| D49 | Complete 180 diagnostic trials before the fixed 600-trial exploratory benchmark | Five controlled metadata renderings, three repetitions, no score-based tuning or extra generation probes |
| D50 | Bind run evidence to selected model/database/source and use versioned SQL policy | Four independent gate findings closed; v2 native-function alternatives tested before generation; v1 and old scores preserved |
| D51 | Fix source/Git commit for both revised runs and keep results local | Append-only logs, explicit resume, exact paired contrasts and auxiliary replay; human review remains pending |

## Verified observations

- Pop!_OS 24.04; Python 3.12.3; i9-12900H; approximately 16 GiB RAM.
- GPU is RTX 3060 **Laptop**, 6144 MiB, driver 580.159.03.
- Existing mysql-dev is MySQL 8.4.11; Sakila was absent on inspection.
- Existing llama-server image is build b11206, revision 2b129ccfa03aea330d2d9ac4650a10de393dbe3a.
- DataHub MCP 0.8.0 defaults to 120-character field descriptions and annotation-dependent field priority ordering. Full retrieval and independent canonical sorting are required.
- Metadata runtime compatibility verified for server 0.8.0, FastMCP 3.2.0, MCP SDK 1.30.0, ingestion SDK 1.7.0.17, Core v1.8.0. MCP serverInfo.version=3.2.0 identifies the FastMCP framework; it must not be confused with the server package version.



### D52 — Pertanyaan alami revision03

Atas instruksi peneliti, hilangkan footer kolom teknis dan gunakan permintaan bisnis berbahasa Indonesia. Definisi domain tetap pada metadata. Tetap30soal/10–10–10 dan enam tugas source-rule. Tambahkan tiga ordered tasks termasuk dua top-k berdasarkan celah cakupan, bukan model EX. Blind review Q154 menghasilkan klarifikasi relasi yang diminta tanpa SQL recipe.

### D53 — Kesetaraan kolom global

Revision03 memilih permutation policy eksplisit: satu bijeksi kolom berlaku untuk seluruh hasil, aliases bebas, whole-row duplicates dan requested row order dipertahankan. Numeric/date contracts memakai koordinat gold. Fixed policy v1/v2 tetap tersedia. Tidak ada regrading atau relabelling hasil lama secara diam-diam.

### D54 — Source correction dan batas run baru

Perbaiki lookup question_attributes dari Question objects ke question_id string dengan regression test. Pertahankan source equality gate. Source/prompt/questions/comparator berubah, sehingga approval/pilot versi lama tidak dianggap bukti untuk request versi baru. Tidak ada generation baru selama perubahan instrumen ini.

### D55 — Reference dan witness revision03

Gold B ditulis independen tanpa gold A/prediksi dan dikunci sebelum eksekusi. Seluruh30pasangan agree pada baseline+8variations; semua critical mutants distinguished. Fixtures revision03 menambah ranking/tie boundaries pada clone terisolasi, tanpa mengubah Sakila utama. Human review tetap pending; agreement AI dan finite witnesses bukan proof semantik universal.


### D56 — Pernyataan review peneliti dan run utama

Peneliti secara eksplisit menyatakan input telah direview serta meminta600trial dan BABIV/V. Catat `user_attested_complete` dengan reviewer identity/date belum diberikan; tidak mengarang submission atau signed review. Execution manifest terpisah mengikat scope yang sama, tanpa mengubah input asli.

### D57 — Smoke teknis sebelum600trial

Pakai3pertanyaan terpisah×4snapshot=12request untuk memastikan jalur source/model/API/safety/evaluator/sampler yang sama bekerja. References/mutants diperiksa independen pada9database cases. Tidak ada score threshold; diagnostic180lama tetap arsip dan tidak diulang. Manuscript builder hanya menerima600primary+4800auxiliary outcomes lengkap.


### D58 — Bounded local model capability extension

After revision03 main results were shown, the researcher authorized a new local-model pilot. Preserve the completed600trial run and its manuscripts as a completed main experiment, not a retrospectively relabelled pilot. Test at most two pre-pinned candidates in declared order on12separate P301–P312 tasks ×4conditions ×2requests. Selection never uses the main30questions, significance or the largest condition gap. Any later main replication requires a disclosed amendment and existing main/smoke freezes.

### D59 — Capability admission and reasoning budget

Freeze engineering thresholds before candidate generation: S3≥18/24correct, domain≥6/12correct, at least one correct trial in each of3families and S3SQLsuccess≥23/24, plus complete context/infrastructure/sampler/source checks. First passing candidate is preferred; neither candidate is guaranteed to pass. Reasoning on, server-separated reasoning_content, thinking budget2048 and total output4096 remain identical across conditions. Raw reasoning/final response is stored, final SQL alone evaluated, without DB feedback or semantic repair. Pilot evidence cannot impersonate human review or authorize main execution.

### D60 — Independent interpretations and reference execution optimization

Original A/B inputs and blind B receipt are retained. B signed arithmetic was corrected after pre-generation MySQL1690. P309A planner timeouts were resolved by materializing eligible customer IDs before monthly event summation; this optimization occurred after B was visible and is not claimed as fresh blind authorship. The original canonical A remains the explicit structural-profile source. All12pairs then agree on primary+9isolated variations and all33declared mutants have successful semantic witnesses. Some new domain targets are derivative reports over the same3rules. New-pilot human review remains pending; no identity/approval is fabricated.

### D61 — Researcher locks Qwen3.5-9B and explicitly waives further pilot generation

After the earlier main and Qwen3-8B capability results were disclosed, the researcher selected Qwen3.5-9B, requested600main trials directly and asked to monitor the job personally. Bind the exact statement to the unchanged reviewed30question stimulus, selected model/config/Compose and preserved prior history. The unexecuted4Bfallback is superseded, not silently treated as evaluated. Record a disclosed researcher-selected replication; do not claim prospective capability admission, retrospective preregistration or guaranteed statistical significance.

### D62 — Zero-generation preflight and sampler observations from actual main responses

The explicit amendment waives capability pilot and generation smoke, while retaining model-byte/backend/source/context/database/reference/safety/evaluator checks. Revalidate all30reference pairs and56mutants on primary+8variants under current code. Check all120main contexts without generation. Observe actual sampler/seed/cache after each durable main response using GET only; bind every proof to the frozen manifest and outcome. Preserve terminal outcomes if post-completion observation fails. The fixed600trial controller retains append-only logging, stop-on-infrastructure behavior and no automatic repair/retry. Run through a locked systemd user service with sleep inhibition; no Codex monitor loop after launch. Reports/statistics/BABIV/V are generated after complete evidence and remain local.
