# analyze/

Scripts that build the analysis table, write the shared split, fit the linear separator, produce 2D PCA/LDA plots, and run reduced-space clustering. Shared path constants live in `paths.py`.

**Most important files**

- `build_table.py` — labels + Titan `only_original` → analysis table
- `split.py` — one stratified train/test split
- `linear_separator.py` — balanced logistic probe
- `embed_2d.py` — PCA/LDA visualization
- `cluster.py` — PCA-space k-means + lift gate

| filename | description of what it’s for |
| --- | --- |
| `paths.py` | Shared paths / constants (`ANALYSIS_DIR`, split seed, classifier id) |
| `build_table.py` | Join labels CSV with cached Titan embeddings; write parquet / npy |
| `split.py` | Stratified post-level 80/20 split → `split_ids.json` |
| `linear_separator.py` | Train/eval balanced logistic on shared split |
| `embed_2d.py` | Leakage-safe PCA(2) + LDA viz + `embeddings_2d.csv` |
| `cluster.py` | Train-fit PCA → k-means; cluster lift / exemplars |
| `__init__.py` | Package marker |
| `README.md` | This folder index |
