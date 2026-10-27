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

## Verified observations

- Pop!_OS 24.04; Python 3.12.3; i9-12900H; approximately 16 GiB RAM.
- GPU is RTX 3060 **Laptop**, 6144 MiB, driver 580.159.03.
- Existing mysql-dev is MySQL 8.4.11; Sakila was absent on inspection.
- Existing llama-server image is build b11206, revision 2b129ccfa03aea330d2d9ac4650a10de393dbe3a.
- DataHub MCP 0.8.0 defaults to 120-character field descriptions and annotation-dependent field priority ordering. Full retrieval and independent canonical sorting are required.
- Metadata runtime compatibility verified for server 0.8.0, FastMCP 3.2.0, MCP SDK 1.30.0, ingestion SDK 1.7.0.17, Core v1.8.0. MCP serverInfo.version=3.2.0 identifies the FastMCP framework; it must not be confused with the server package version.

