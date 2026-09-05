# LLM toxicity classifier smoke (2026-09-05)

Build 50 synthetic posts with Faker, inject toxic language into a random subset, and label them in one OpenAI Batch job.

Results: [`RESULTS.md`](./RESULTS.md)

## Run

From the repository root:

```bash
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

Requires `OPENAI_API_KEY` in the repo-root `.env`.
