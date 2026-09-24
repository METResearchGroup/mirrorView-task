# Study Phase 2 Parts 2 and 3 combined

The full linked-fate dataset is the union of the June collection (Part 2) and the September 2026 collection (Part 3). Load it through `shared.data.dataloader.load_dataset`.

| Name | What it returns |
| --- | --- |
| `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` | Part 2 then Part 3 session rows. 168,871 rows and 5,051 Prolific accounts. Part 3-only columns (`attention_check_passed`, `attention_check_selected`) are empty on Part 2 rows. |
| `STUDY_PHASE_2_PART_2_AND_3_STIMULI` | Unique posts from both catalogs. 20,000 rows. Overlapping keys keep the Part 2 row. |

These names have no single CSV. The loader stacks the Part 2 and Part 3 tables. Part 1 is not included.

```bash
PYTHONPATH=. uv run python -c "from shared.data.dataloader import load_dataset; from shared.data.registry import STUDY_PHASE_2_PART_2_AND_3_STIMULI, STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL; stimuli = load_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI); results = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False); print(len(stimuli), len(results), results['prolific_id'].nunique())"
```

Expected: `20000 168871 5051`.
