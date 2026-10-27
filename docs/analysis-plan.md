# Paired analysis protocol v1 — preliminary freeze

Primary outcome: EX per assigned evaluable trial. Complete run: 150 trials per scenario, 200 per complexity, 600 total.

Aggregate each question–scenario pair to successes/5. The question remains the matched block; 600 trials are not independent question samples.

- Omnibus statistic: sum of squared deviations of four scenario means from their grand mean.
- Permute scenario labels within each of 30 question blocks; 100,000 Monte Carlo permutations; recorded RNG seed; plus-one correction.
- Six two-sided paired permutation contrasts; Holm-adjusted p-values; alpha=0.05.
- Effect sizes: paired mean EX differences in percentage points.
- Confidence intervals: 10,000 paired question-level bootstrap resamples, stratified by complexity.
- Preserve all-tied questions; no-difference cases give statistic zero/p=1.
- Complexity, repeat consistency, latency, tokens, and structural SQL variation are supporting analyses. Do not choose tests based on significance.

Assumptions/limitations: label exchangeability under the null must be discussed; trial-order randomization alone does not prove it. Questions are a fixed selected Sakila benchmark, not a random sample of all Text-to-SQL tasks. Nonsignificance does not establish equivalence. Token length is part of the treatment package and is not automatically controlled away by regression.

Implementation: `analysis/statistics.py`; verified with synthetic fixtures, including all-tied scores, missing/duplicate observations, Holm adjustment and preservation of whole paired questions during bootstrap. Monte Carlo comparisons use an integer-scaled statistic equivalent to the specified statistic, avoiding floating-point boundary artifacts. RNG is explicitly PCG64DXSM with independent seed substreams. Bootstrap intervals are percentile intervals (NumPy linear quantile), pointwise rather than simultaneous.

The researcher selected this analysis before the 600-trial preliminary run. This document is hashed into the experiment manifest before generation. External methodological review remains pending; the frozen protocol is not represented as supervisor approval. A preliminary run uses draft references and all statistics are conditional/exploratory. Pilot reports contain descriptive engineering measurements only. Later changes to the analysis must be versioned, justified and identified as post hoc; the original outputs remain preserved.

