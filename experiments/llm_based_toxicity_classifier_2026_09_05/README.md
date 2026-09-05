# LLM toxicity classifier live test (2026-09-05)

The experiment script builds 50 made-up posts with the Faker library, and it adds toxic language to some of those posts at random. It then sends all 50 posts to OpenAI in one Batch job. A Batch job is OpenAI's API for labeling many texts in one request. Each post is labeled as low, medium, or high toxicity.

The run's elapsed time, estimated cost, and counts of low, medium, and high labels are in [`RESULTS.md`](./RESULTS.md).

## Run

From the repository root:

```bash
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

The script needs `OPENAI_API_KEY` in the `.env` file at the repo root, or in the environment.
