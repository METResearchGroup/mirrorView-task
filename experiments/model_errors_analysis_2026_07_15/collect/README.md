# collect/

Builds the labels CSV from the existing Bedrock Qwen3 Next 80B `predictions.csv` (no Bedrock calls). Writes `outputs/run_manifest.json` and `outputs/base_model_llm_labels.csv`.

**Most important files**

- `build_long_csv.py` — end-to-end labels CSV builder
- `manifest.py` — run manifest / primary run spec
- `load_predictions.py` — normalize prediction CSV columns

| filename | description of what it’s for |
| --- | --- |
| `manifest.py` | Enumerate the primary Bedrock run and write `run_manifest.json` |
| `load_predictions.py` | Load / normalize `predictions.csv` into a common frame |
| `build_long_csv.py` | Join study texts + predictions → `base_model_llm_labels.csv` |
| `__init__.py` | Package marker |
| `README.md` | This folder index |
