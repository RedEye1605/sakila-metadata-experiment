# Research and writing handoff

Read [docs/ai-handoff.md](docs/ai-handoff.md), then [the current writing brief](reports/qwen35-9b-main-01/AGENT_BRIEF.md) before editing thesis material.

- Communicate and write thesis prose in Indonesian. Preserve the exact thesis title and eight research stages in the brief.
- Current completed main run: `qwen35-9b-main-01`, 600 trials, Qwen3.5-9B. Use the published bundle's actual reports, inputs, figures and audit receipts. Older main/pilot/diagnostic runs remain historical evidence.
- Writing work does not authorize new inference, model selection, gold changes or changing frozen artifacts. Keep editorial revisions separate from original evidence.
- Only S3–S0 is significant after Holm correction of six paired contrasts. Use 30 question blocks; never treat 600 trials as independent questions. Preserve nonsignificant findings and disclosed post-result model selection.
- Human review completion is researcher-attested; reviewer identity/date and campus formatting remain to be supplied by the researcher. Never invent them or equate AI agreement with human review.
- The researcher explicitly authorized publication of `reports/qwen35-9b-main-01` for Windows transfer. Historical embargo flags remain unchanged in original manifests. Credentials, actual `.env`, model weights, database volumes and unrelated private submissions remain excluded.
- Run `infra/publication.py` on staged files before committing. Do not weaken `.gitignore` to publish raw `runs/`.
- Use Context7 current official documentation when answering library/API/SDK/CLI setup or usage questions; verify installed behavior rather than assuming tools or fields exist. This is unnecessary for editing prose or checking stored research arithmetic.
