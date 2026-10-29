# Qwen3.5-9B: researcher-selected main replication

The researcher explicitly selected **Qwen3.5-9B** and requested600main trials without another capability pilot or generation smoke. This amendment supersedes the unexecuted Qwen3.5-4B fallback. The earlier600trial main and96trial Qwen3-8B pilot remain preserved under their original identities. Selection occurred after their results were known; it is not described as preregistration, a passed capability gate, or evidence that significance will improve.

The final thesis title remains **Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)**.

## Frozen instrument and model

-30existing revision03 main questions,10simple/10medium/10complex;4frozen S0–S3 snapshots;5independent requests per pair;600assigned main trials.
- Unchanged question/gold/contract/annotation/prompt/evaluator/database and paired-analysis artifacts. Column permutation uses one global bijection; whole-row multiplicities and requested ordering remain checked.
- Upstream model: `Qwen/Qwen3.5-9B`. GGUF publisher: `unsloth/Qwen3.5-9B-GGUF`.
- Revision: `3885219b6810b007914f3a7950a8d1b469d598a5`.
- File: `Qwen3.5-9B-Q4_K_M.gguf`,5,680,522,464bytes.
- SHA-256: `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`.
- llama.cpp image remains digest-pinned;24GPU layers,6CPU threads, one slot, context16384, output4096, thinking budget2048, temperature0.6, top-p0.95, top-k20, min-p0, repeat penalty1. HTTP timeout1200seconds; SQL timeout remains10000milliseconds.
- No prompt cache, conversation history, context shift, continuous batching, DB/MCP access by the model, repair or model-error retries. Reasoning is stored separately from final SQL.

Full configuration: [TOML](../configs/qwen35-9b-main.toml), [model spec](../configs/models/qwen35-9b-q4km.json), [Compose](../infra/inference/compose.qwen35-9b.yaml), [amendment](../data/amendments/qwen35-9b-direct-main-01.json).

## Engineering checks retained

Zero-generation preflight verifies model bytes/backend/actual command, all120complete main contexts, reviewed stimulus hashes, current reference execution and witnesses on the primary plus8isolated database variants, SQL safety, database fingerprint and source identity. The shared instrument supports exactly one original smoke path or an explicit hash-bound amendment; the normal smoke gate remains intact for unamended runs.

Every completed main response receives a separate sampler/seed/cache observation using `GET /slots`, bound to its durable ledger outcome. This adds no generation. A failure stops the driver, preserves existing responses/outcomes and requires explicit recovery. `Restart=no`; no automatic restart or semantic retry. Snapshot/source/input changes are rejected on resume.

Only600generation requests are planned. Reference SQL checks, tokenization and later4800auxiliary SQL outcomes do not add LLM generation. Pipeline postprocessing uses the previously fixed paired permutation, exact pairwise/Holm and question-block bootstrap plan. No result is guaranteed significant.

## Execution and researcher monitoring

Research driver: `research/qwen35-9b/run_experiment.py`. Run workspace: `runs/qwen35-9b/main-01`. A user systemd unit, exclusive process lock and sleep inhibitor keep the job independent of this chat. Codex does not keep a monitor loop after launch.

```sh
rtk proxy tail -n 12 -f runs/qwen35-9b/main-01/service.log
rtk proxy systemctl --user status sakila-qwen35-9b-main-01.service --no-pager -l
rtk proxy .venv/bin/python research/qwen35-9b/status.py
```

`Ctrl+C` closes the log viewer only. Log milestones occur every10new completed trials. The status command reads counts without opening predictions or interpreting partial EX.

On `primary_analysis_complete`,600outcomes and the primary EX/statistical report are ready. The driver then stops this model server, replays stored SQL on8isolated variants without new generation, and writes updated BABIV/V. `pipeline_complete` marks the complete result/report/manuscript pipeline. `pipeline_interrupted` reports an actual interruption; do not blindly restart or create a new run.

Outputs: `analysis/report.md`, `analysis/report.json`, CSVs and scientific figures; `auxiliary/`; `thesis/BAB_IV.md`, `thesis/BAB_V.md`, `thesis/NASKAH_BAB_IV_V_LENGKAP.md`; and hash-bound completion receipts. Actual results remain local. Reviewer identities/dates remain for the researcher to enter; no new human approval is invented.

## Interpretation limits

The new model is a researcher-selected replication on a known benchmark. It does not erase earlier findings. Cross-run differences include model, reasoning and inference settings, so they cannot isolate parameter count alone. Bounded output/reasoning settings differ from publisher leaderboard conditions. Within the new run, only metadata varies across S0–S3. EX on one primary database is reported separately from auxiliary robustness; neither establishes universal semantic equivalence.
