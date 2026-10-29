# Local model capability pilot after revision03

The completed revision03 main run remains intact. The researcher requested a local model replacement after seeing those results; this is a disclosed extension, not retroactive model selection or a relabelled pilot. The thesis question remains the metadata effect within one fixed model. No model is chosen to obtain a particular p-value.

## Fixed engineering design

Twelve new P301–P312 tasks × four frozen metadata conditions × two independent requests =96 trials per candidate. Question text differs from the30main tasks; some domain tasks are derivative reports over the same three Sakila definitions, not independent new policies. Public questions never contain SQL recipes or gold. Technical schema, snapshot payloads, common prompt and v3result comparator remain unchanged.

Candidate order was pinned before generation: official Qwen3-8B GGUF Q4_K_M, then Unsloth's Qwen3.5-4B GGUF Q4_K_M only if the first is infeasible or fails the predeclared engineering criteria. The second quantization's publisher, upstream model, file revision and SHA are disclosed. At most two candidates are considered, and only one can be selected by the first-passing rule. This does not expand the thesis into a primary multi-model leaderboard.

Generation uses the verified digest-pinned llama.cpp b11206 server on loopback18082, one slot and no prompt cache/context shifting/continuous batching. Reasoning is on with budget2048 and server extraction into reasoning_content; final message.content alone is evaluated as SQL. Full raw responses remain in the ledger. Maximum output4096, context16384, temperature0.6, top-p0.95, top-k20, min-p0 and repeat penalty1 are fixed across S0–S3. This is a different model/serving package from the old run; cross-run differences must not be described as a pure model-size effect.

## Predeclared admission criteria

All96 assigned outcomes and48complete contexts must be verified, with no unresolved infrastructure incident. S3 must obtain at least18/24correct total, at least6/12correct domain trials, at least one correct trial in each of the three domain families, and at least23/24successful SQL executions. These are practical engineering thresholds frozen before requests, not statistical rejection thresholds or promises for main EX. S0–S3 differences and p-values do not select a candidate. Passing a small AI-reference pilot does not grant main review approval.

## References and provenance

Independent B was written from public questions, common instructions, installed technical schema and full S3, without opening A, contracts or model outputs. The auditor had earlier project context; complete historical amnesia is not claimed. Its interpretations and references were hashed before comparison against old public questions. New-pilot human review remains pending; no reviewer identity or approval is invented.

Pre-generation SQL checks found two B unsigned-arithmetic errors and an unstable MySQL plan for A on P309. Original references and every correction/check attempt are retained. B corrected signed subtraction without changing intent. A execution optimization happened after B was visible and is explicitly not claimed as new blind authoring. The executed P309A materializes qualifying customer IDs then sums monthly payment events; B independently sums per-customer qualifying totals. Structural labels remain anchored to the original supported canonical A, which is separately hash-bound. No question, numerical convention, timeout or model output was repaired to obtain agreement.

Final reference checks require agreement on primary plus nine isolated variants and successful distinguishing witnesses for all33predeclared semantic mutants. Additional pilot fixtures exercise August strict thresholds, inactive eligible customers, last-day payments, calendar/elapsed-day differences, cutoff, NULL return and competing ranked film totals. Only the allowlisted clone on13311can be changed; the primary is read-only. All input/proof/source/model/prompt hashes are frozen before generation.

## Execution and reporting

`research/model-pilot-01/run_candidate.py` runs only the96trial engineering pilot and emits separate manifests/ledger/completion, sampler proof, descriptive EX and capability decision. It cannot dispatch600main trials. Responses are durable before evaluation; completed/model-failure trials are not regenerated. The existing main/smoke review gates remain in place.

Commands after verified download/backend/input preparation:

```sh
.venv/bin/python research/model-pilot-01/run_candidate.py --dry-run
.venv/bin/python research/model-pilot-01/run_candidate.py
```

The research CLI's existing pinned-model downloader and runtime verifier are reused. Model specs: configs/models/. Inference config: configs/qwen3-8b-pilot.toml. Deployment: infra/inference/compose.qwen3-8b.yaml. Dataset/protocol: data/benchmarks/model-pilot-01/. Results stay under runs/model-selection/ and remain local. Any subsequent main replication requires its own explicit amendment, matching engineering smoke, source/model/config freeze and preserved prior results.
