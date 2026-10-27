# Implementation status

Updated 2026-10-27. The user explicitly keeps the main benchmark draft. No main generation trial has been run.

## Closure milestone

- BAB IV Markdown, evidence matrix and reviewer guide are available in `docs/bab-iv.md`, `docs/evidence-matrix.md` and `docs/review-guide.md`. Markdown links checked; no broken document links found.
- Review package `runs/reviews/closure-02` contains 39 questions, 106 descriptions and seven business terms. All decisions remain pending. The user reaffirmed that pilot review is not yet complete.
- Readiness now separates mechanical checks from four human components: benchmark, metadata, generation and analysis. Pilot ledgers/results and selected-backend/input/source/database matches are audited rather than trusting a completion flag.
- New scored pilot and repetition requests stop on draft references before backend access. No 7B SQL-generation/scoring/probe requests have been made.
- Official Qwen2.5-Coder-7B-Instruct Q4_K_M downloaded and SHA-256 verified. It loads at 24 GPU layers, context 16,384; all 36 pilot prompt budgets fit with maximum 7,411 input tokens. Evidence: `runs/inference/coder7b/backend-final-24/verification.json`. The earlier `backend-24` record is retained as historical evidence.
- Runtime verification records actual container/image/command/memory/model mount. Main/pilot preflight rejects changed deployment settings even when model alias/context properties still match. Sampler proof must be generated for the selected backend after an audited reviewed pilot; 3B proof is not reused for 7B.
- Parameterized CLI covers model download, backend verification/sampler/probe, metadata reconciliation/snapshot building/validation, review export, and explicit crash recovery. Legacy inference scripts delegate to these commands.
- Fresh workspace + locked environment + separate official MySQL import on port 13309 reproduced the database schema/DDL/data and all four snapshot payloads. `runs/reproduction/closure-final/report.json` records success, zero model-generation requests and preserved volumes. Replays archived actual MCP exports; does not claim a fresh DataHub ingestion.
- Cold-start initially exposed a temporary-server socket healthcheck race. TCP `SELECT 1` fixes readiness; failed `closure-01` evidence is retained. Later reproduction runs succeeded without modifying the research instance.
- **133 tests passed both locally and in the final fresh reproduction environment.** Tests include 600 synthetic assignments, outage, unresolved crash, explicit operator recovery, no response regeneration, model corruption rejection, stale review-result detection and deployment-drift rejection.
- Current blockers: reviewed pilot/main gold, annotation review, model/prompt decision, selected-backend scored pilot/sampler proof and analysis agreement. These depend on review; code does not manufacture approval. The model remains a candidate.

## Implemented and verified

- Locked Python environments, strict secret-free configuration, artifact/source hashes and read-only doctor.
- Official unchanged Sakila in isolated MySQL 8.4.11: 16 InnoDB base tables, 90 columns, 22 FKs, 47,268 rows. SELECT-only accounts, persistent global read-only flags and repeated schema/DDL/content fingerprints.
- MySQL AST safety, single-statement enforcement, verified grants, bounded streaming and actual server query timeout. Infrastructure errors remain separate from model errors.
- EX preserves positional columns, duplicates, NULL/type semantics, ordering contracts and exact numbers. Optional approximate matching is one-to-one.
- Healthy authenticated DataHub Core v1.8.0 deployment, catalog ingestion and annotation administration verified. Native geometry reflection loss reconciled with original diagnostic and fidelity receipt retained before ingestion.
- Live MCP SDK 1.30.0/server 0.8.0 verified, including actual tool schemas, pagination, complete descriptions and glossary definitions/bindings. Direct SDK calls administer metadata; snapshot retrieval is MCP-only.
- Four immutable candidates in `snapshots/candidates-v2`, each stable across two independent exports. Identical installed technical schema, 106 S1/S2 annotation elements, unchanged S2 text in S3, seven S3 business terms. No silent truncation or fallback enrichment.
- Official Qwen2.5-3B-Instruct Q4_K_M candidate hash verified and loaded on llama.cpp b11206. Effective context 16,384; all 36 pilot prompts fit, maximum 7,411 input tokens plus 1,024 output and 256 margin.
- Actual sampler, seed, token usage and zero prompt cache verified. Five independent P007/S3 requests produced four unique raw outputs; stochastic requests need not produce different SQL each time.
- Stable prompt without tools/history/gold; complete context checked before requests; no semantic repair, generation retry or execution-feedback loop.
- Append-only ledger, immutable manifests/plans, deterministic balanced 600-assignment plan with paired seeds. Actual four-trial smoke and 36-trial pilot completed. Live resume created zero server tasks and zero ledger events.
- Integrity audit verifies manifest, plan, SQLite/events, JSONL, prompts and result hashes. Pilot reporting is descriptive only.
- `readiness`, `freeze-main`, `run-main` have artifact-specific review gates. Live draft rejection produced no server task or main directory. Approved freeze will check all 120 main prompt budgets and reference execution; no approved main freeze exists yet.
- Paired permutation, six Holm-adjusted contrasts, stratified paired question bootstrap and PNG/PDF export tested with synthetic data.
- Initial milestone had 116 pytest checks; closure now has 133 including real MySQL integration. Token lifecycle additionally verified with mock HTTP; real token rotation not performed.
- Secret scan passed for 523 source/evidence files. No main ledger exists.

## Pending review and freeze

- Independent semantic review of 30 main questions/gold SQL and pilot/main paraphrase overlap. All references remain draft as requested.
- Semantic review of descriptions/business rules. Literal gold/question leakage scan passed; this cannot establish absence of semantic hints.
- Preliminary model checks remain local during independent review. Do not inspect main-question outcomes to select a model or favorable metadata effect.
- Agreement on EX/analysis protocols and approval of exact artifact hashes. Passing tests never creates human approval.
- Main freeze, full main prompt checks, 600 actual trials and research analysis remain unexecuted.

## Evidence

- `runs/database/import-manifest.json`, `runs/database/baseline.json`
- `runs/metadata/catalog-ingestion.json`, `runtime-images.json`, `mcp-tool-inventory.json`
- `runs/metadata/exports/S0-a` through `S3-b`, `scenario-validation-v2.json`
- `runs/gold/main-draft-01/review.md`, `runs/gold/pilot-draft-01/review.md`
- `docs/annotation-review.md`, archived v1 and current v2 annotation specifications
- `runs/inference/backend-01/verification.json`, `smoke-runtime-verification.json`, `repetition-probe-01/report.json`
- `runs/pilot/smoke-02`, `runs/pilot/pilot-01`, `runs/pilot/pilot-01/review.md`
- `runs/analysis/pilot-01/report.json` — engineering descriptive report
- `runs/verification/live-resume-pilot-01.json`, `live-main-draft-gate.json`, `source-and-secret-audit-02.json`
- `runs/readiness/main-review-01.json` — pending reviews and artifact hashes
- `runs/readiness/closure-final.json` — final four-component review policy and current blockers
- `runs/reproduction/closure-final/report.json`, `command-08.log` — fresh environment/database and 133 checks
- `runs/verification/synthetic-figures` — synthetic only, never research results

DataHub is stopped with volumes preserved. Local inference can be stopped to release GPU memory; see the runbook. Existing mysql-dev data was not changed. No main EX or research p-values have been produced.

