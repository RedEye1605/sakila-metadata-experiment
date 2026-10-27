# Implementation roadmap and acceptance gates

This is research instrumentation, not a chatbot product. The eight approved research stages remain: literature, metadata annotation, test dataset, pipeline design, pipeline implementation, Text-to-SQL testing, analysis, conclusions.

| Phase | Deliverable | Gate |
|---|---|---|
| 0 | Environment, pinned topology, resource feasibility | Actual hardware and service compatibility verified |
| 1 | Repository, configuration, doctor, secret handling | Configuration and redaction tests pass |
| 2 | Official isolated Sakila, reader access, full fingerprints | Privileges, timeout, result bounds, unchanged data verified |
| 3 | DataHub ingestion and annotation management | All installed tables, columns, native types, PK/FK match database audit |
| 4 | MCP retrieval and four snapshots | Complete pagination, lossless descriptions, identical technical schema, S2 descriptions unchanged in S3 |
| 5 | 30 main questions, gold, nine separate pilots | Human semantic review, explicit complexity and comparison contracts |
| 6 | Local LLM client and fixed prompt | Full S3 fits including template/output reserve; pilot feasibility; fixed model hash/settings |
| 7 | EX evaluator | Duplicate, NULL, numeric, datetime, ordering, unsafe SQL, and outage cases tested |
| 8 | Scheduler, durable ledger, resume | 600 unique assignments; 150/scenario; 200/complexity; no model-error retries |
| 9 | Smoke test and main run | All artifacts reviewed/frozen and provenance checked |
| 10 | Paired analysis and figures | Analysis protocol fixed before main results; no pseudoreplication |

## Immutable experiment controls

Same database/data, base-table/column coverage, native types, PK/FK, technical ordering, serialization, prompt structure/language, questions, model/backend, sampling policy, and evaluator. S1/S2 annotate exactly the same elements. S3 preserves S2 descriptions verbatim and only adds approved business context. More metadata is not assumed to improve EX; token length is measured and discussed.

## Failure policy

One generation opportunity per evaluable assigned trial. Malformed, unsafe, incorrect, or timed-out model SQL is terminal EX=0. Unrelated infrastructure failure is EX=null and separately logged. Persist raw response before evaluation. Resume uses persisted response; no error feedback or semantic repair. An ambiguous dispatch after crash is not silently claimed to be exactly once. A change to generation inputs requires a new manifest/run.

## Human readiness gates

The latest user decision authorizes a **separate preliminary route with draft inputs**. It is not a bypass that marks these gates passed. Its 36-trial qualification pilot and frozen 600-trial run share source/model/settings; every resulting report remains provisional and locally embargoed. See D34–D40. The gates below still govern reviewed main execution.

- Questions and gold SQL require user/reviewer semantic approval.
- Annotations require schema/documentation-grounded review; no gold or answer-specific hints.
- No main run until model, snapshots, benchmark, prompt, comparison rules, source version, and analysis protocol are frozen.

