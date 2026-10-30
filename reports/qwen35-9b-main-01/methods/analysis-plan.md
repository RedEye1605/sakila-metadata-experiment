# Paired analysis — revision 03 exploratory

Specified before revision-03 model outputs. Prior exploratory/diagnostic history is retained; this is not retrospective preregistration. Primary metric EX on unchanged official Sakila, 30 fixed selected questions ×4 metadata packages ×5 repeats. Scores conditional on draft references; human review remains pending. Information availability is part of the metadata-package treatment; do not claim a pure verbosity effect.

Question is the paired unit. Each question/scenario gives successes/5. Preserve all ties and all thirty blocks. Complete data requires exactly 600 assigned evaluable outcomes; infrastructure nulls do not become 0 and incomplete paired analysis is blocked. EX denominators/completeness are reported explicitly.

- Omnibus: squared deviations of four means;100,000 within-question label permutations, inclusive tail, plus-one correction. Integer statistic matches v1 definition.
- Six two-sided contrasts: exact whole-question sign-flip distribution of integer count differences; inclusive tail; retain zero blocks and exact numerator/denominator. Holm family of six, alpha .05.
- Effects: paired mean differences in percentage points.
- Intervals:10,000 whole-question percentile bootstrap samples stratified by structural complexity,95% pointwise; not simultaneous intervals or inversion of the exact tests.
- RNG PCG64DXSM; analysis seed 2026102802. Independent substreams retain v1 convention for omnibus/bootstrap. Monte Carlo contrasts from the same fixed computation may be retained as labelled sensitivity only; exact p-values are primary in v2.
- Stratification by information need, original hardness, semantic capability, correctness consistency, latency, input/output tokens and structural variation is descriptive. Auxiliary fixture robustness is separate from primary EX. Do not expand a family of significance tests after outcomes.

Assumptions: omnibus requires relevant label exchangeability; paired sign flips require swap invariance/symmetry under the null, not merely equal average EX. Randomized request order and common seeds do not establish these assumptions automatically. The selected fixed benchmark is not a probability sample of business SQL; bootstrap expresses composition sensitivity under the stated resampling model. Five repeats are not five independent questions. Nonsignificance does not establish equivalence.

Diagnostic 12×5×3 has four planned contrasts B−A,C−A,B-order 1−B,B-order 2−B; descriptive paired question scores, raw differences and uncertainty. Aggregate three repetitions per question/variant. Use 10,000 whole-question paired percentile bootstrap samples, unstratified across the 12 fixed pilots, PCG64DXSM with analysis seed 2026102802; reuse draws across the four contrasts. Intervals are pointwise composition sensitivity, not simultaneous inference. No significance tests for the diagnostic. With 12 items, do not infer absence of a mechanism from an interval spanning zero or claim pure context length isolation. No language/quantization/model-family causality claim. No minimum accuracy/significance stopping rule. Inputs and choices are fixed before diagnostics; no main item selection using diagnostic or benchmark model performance.

Original preliminary-01 protocol/results remain unchanged. Old/new EX differences are descriptive because multiple instrument components changed. Gold-only corrections after real adjudication produce separate reports; question/metadata changes require new generation inputs and experiment versions. A post-run review is never recorded as pre-run approval.

Revision03 uses global column-permutation equivalence and three ordered tasks including two top-k tasks. Neither the paired design nor test selection depends on revision03 outcomes. Original diagnostic outputs are not relabelled as outputs under the new prompt/comparator.
