# Sakila Metadata Experiment

**A controlled Indonesian Text-to-SQL research instrument.**

Investigate how metadata annotation changes the execution accuracy of one fixed local LLM on the official MySQL Sakila database. DataHub and MCP prepare auditable metadata snapshots; Python runs independent inference requests, safe SQL execution, result comparison and question-paired analysis.

> **Research status:** benchmark and metadata are drafts awaiting independent annotation. Preliminary evaluation is explicitly supported and labelled provisional. Actual model predictions, EX scores and statistical outputs remain local until review. Richer metadata is not assumed to improve accuracy.

![Two-phase experimental architecture](docs/figures/architecture.svg)

**Thesis title — unchanged:** *Analisis Pengaruh Metadata terhadap Execution Accuracy pada Sistem Text-to-SQL Berbasis Large Language Model (Studi Kasus: Basis Data Sakila)*

[BAB IV](docs/bab-iv.md) · [Runbook](docs/runbook.md) · [Annotator guide](annotations/round-01/GUIDE.md) · [AI handoff](docs/ai-handoff.md) · [Decisions](docs/decisions.md)

## Experimental design

| Condition | Metadata received by the model | Coverage |
|---|---|---|
| S0 | Technical schema, native types, PK/FK and relationships | 16 base tables, 90 columns |
| S1 | S0 + short descriptions | All 106 table/column elements |
| S2 | S0 + detailed descriptions | Exactly the same 106 elements |
| S3 | S2 unchanged + business context | Seven grounded glossary terms and bindings |

The planned benchmark has **30 Indonesian questions × 4 conditions × 5 repetitions = 600 trials**. Each condition has 150 trials. Ten questions belong to each structural complexity group. Nine separate pilot questions are excluded from the main benchmark.

Database, schema scope, questions, prompt template, model, inference settings and evaluation rules remain fixed. Only annotations vary. Full context is checked with the actual backend chat template/tokenizer and never silently truncated. Input tokens are recorded as a possible mechanism behind metadata effects.

![Treatment conditions and shared controls](docs/figures/metadata-controls.svg)

## Pipeline capabilities

- Ingest official schema into DataHub; manage table/column descriptions and glossary bindings there.
- Retrieve metadata through **MCP during preparation**, preserving raw receipts and two-export stability checks. No API fallback is represented as MCP retrieval.
- Freeze deterministic JSON snapshots with SHA-256 provenance and cross-condition validation.
- Send one stateless request per trial to local llama.cpp. No tools, database, gold SQL or previous results reach the model.
- Validate MySQL ASTs; execute through a SELECT-only account with timeouts and result bounds.
- Compare typed execution results, preserving duplicates, NULL, column position and explicit ordering contracts.
- Persist responses before evaluation; resume without silently regenerating completed model failures.
- Audit complete logs before descriptive EX and question-paired permutation/Holm/bootstrap analysis.

## Quick start

Requires Python **3.12**, [uv](https://docs.astral.sh/uv/), Docker Engine and Compose. DataHub and GPU inference are optional for unit tests. Dependency versions and container digests are pinned.

```bash
git clone https://github.com/RedEye1605/sakila-metadata-experiment.git
cd sakila-metadata-experiment
uv sync --frozen --group analysis
uv run --frozen --group analysis pytest -q

# Isolated research database; generates private local credentials.
uv run --frozen sakila-experiment database bootstrap
uv run --frozen sakila-experiment database inspect --output runs/database/baseline.json
uv run --frozen --group analysis pytest -q --run-integration

# No model-generation requests.
uv run --frozen sakila-experiment doctor --offline
uv run --frozen sakila-experiment schedule --questions data/public/main.questions.jsonl --output runs/plan.json
```

MySQL binds to **127.0.0.1:13306**, DataHub GMS/UI to **18080/19002**, and inference to **18081**. Credentials, downloads and experiment logs are Git-ignored. `.env.example` documents configuration; never commit an actual `.env`.

Public candidate payloads in `snapshots/distribution-v1` are byte-identical to the local candidates. Distribution manifests use relative provenance paths and preserve original manifest hashes. Raw MCP exports/runtime receipts remain local; replay requires their archive or fresh documented DataHub/MCP preparation. Public payloads alone do not establish fresh ingestion.

## Running an experiment

Follow the [runbook](docs/runbook.md). Complete database/snapshot/reference checks, backend context verification, a separate pilot and sampler verification before freezing 600 trials.

Selected preliminary configuration: **Qwen2.5-Coder-7B-Instruct Q4_K_M**, llama.cpp b11206, context 16,384, 24 GPU layers, temperature 0.2, top-p 0.95, top-k 40, output limit 1,024. [Model revision/hash](models/qwen25-coder-7b-q4km.json) are pinned. This is an engineering choice, not a multi-model benchmark; no fine-tuning is performed.

The inspected machine has an **RTX 3060 Laptop GPU with 6 GiB VRAM**, i9-12900H and 16 GB RAM. These are observed resources, not universal minimums. Recheck available resources on another host. DataHub and inference use separate operational phases.

`freeze-main`/`run-main` require artifact-specific human review. The explicit draft route is `run-preliminary --allow-unreviewed`, followed by a separately frozen benchmark plan. It never marks a reference approved. Preliminary scores/statistics remain conditional on draft correctness.

## Repository map

```text
src/sakila_experiment/
  db/             # Connection policy, audit, bounded execution, typed values
  metadata/       # Ingestion fidelity, MCP receipts, snapshot invariants
  generation/     # Prompt, model assets, backend proof, stateless LLM client
  evaluation/     # AST policy, gold validation, comparator, reference reevaluation
  experiment/     # Scheduling, append-only ledger, readiness, runner
  analysis/       # Log audit, descriptives, paired statistics, figures
  annotations.py  # Independent templates and validated consolidation
configs/          # Non-secret configuration
data/             # Draft questions, isolated gold, annotation specification
snapshots/        # Portable candidate distribution
annotations/      # A01/A02 templates; actual submissions remain private
infra/            # Pinned deployments, reproduction and publication checks
tests/            # Synthetic unit cases and isolated MySQL integration
docs/             # Protocols, decisions, BAB IV, handoff, editable figures
```

`data/private` means isolated from generation, **not confidential storage**: draft gold is available for scientific inspection. Actual model outputs and human submissions are private by default.

## Evaluation and reproducibility

EX compares execution results, not SQL text. Unordered results use multisets; ordered questions use sequences. Aliases are ignored; column count/position are fixed. Integer/decimal values remain exact; floating tolerances must be declared. Model SQL errors/rejections receive EX=0. Unrelated infrastructure/evaluator failures remain separate from completed trials.

The question is the paired block. Five repetitions are aggregated per question–condition; 600 trials are not 600 independent questions. See [EX rules](docs/evaluation-protocol.md), [analysis plan](docs/analysis-plan.md), [verification matrix](docs/evidence-matrix.md) and [publication policy](docs/publication.md).

Tests cover duplicate/NULL/type/order cases, unsafe SQL, timeouts, corrupted artifacts, deployment drift, outages, ambiguous crashes and safe resume. An earlier clean environment reproduced database and snapshot payloads from archived MCP exports. This is distinct from fresh DataHub ingestion or guaranteed identical stochastic outputs.

## Review and reuse

Each independent annotator receives **152 items**: 39 questions, 106 descriptions and seven terms. Distribute only their designated CSV folder, shared schema/reference material and [guide](annotations/round-01/GUIDE.md), without model predictions/scores. Consolidation creates pending adjudication; software never creates human approval.

After review, **gold SQL/result-contract-only corrections** can rescore stored predictions under a hash-bound adjudication record without new inference. Changes to questions, snapshots, prompt, model or sampling require new generation. Original ledgers remain intact.

Original code is [MIT licensed](LICENSE). Dependencies and Oracle-derived materials retain their licenses: [third-party notices](THIRD_PARTY_NOTICES.md). Weights and credentials are not distributed. [CITATION.cff](CITATION.cff) describes research software; no publication or DOI is claimed.
