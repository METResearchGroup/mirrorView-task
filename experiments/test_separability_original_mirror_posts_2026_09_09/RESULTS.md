# Separability results

## Commands

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
```

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai --smoke
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock --smoke
```

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine openai
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --engine bedrock
```

```bash
PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --score
```

## Catalog

The input catalog is `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` with SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`.

## Presentation

The shared presentation table is `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet` with SHA-256 `561611741b60157b7551ed2c5bf25395b488f17cdd61088979903405d5502fdc`.

## Models

Scoring used OpenAI model `gpt-5.4-nano` and Bedrock model `us.amazon.nova-micro-v1:0`.

## Overall

| engine | accuracy | precision | recall | F1 |
| ------ | --------: | ---------: | ------: | ---: |
| openai | 0.4750 | 0.4841 | 0.9417 | 0.6395 |
| bedrock | 0.4762 | 0.4808 | 0.7441 | 0.5841 |

n_scored openai=10000
n_scored bedrock=9983
n_failed openai=0
n_failed bedrock=17

## Cells openai

| metric | left+low | left+medium | left+high | right+low | right+medium | right+high |
| ------ | ----: | ----: | ----: | ----: | ----: | ----: |
| accuracy | 0.4936 | 0.4932 | 0.4808 | 0.4480 | 0.4520 | 0.4872 |
| recall | 0.9457 | 0.9710 | 0.9783 | 0.8635 | 0.9323 | 0.9415 |
| precision | 0.5046 | 0.4947 | 0.4800 | 0.4739 | 0.4640 | 0.4962 |
| f1 | 0.6580 | 0.6554 | 0.6440 | 0.6119 | 0.6197 | 0.6499 |

n_scored=10000
failed=0

## Cells bedrock

| metric | left+low | left+medium | left+high | right+low | right+medium | right+high |
| ------ | ----: | ----: | ----: | ----: | ----: | ----: |
| accuracy | 0.6064 | 0.5830 | 0.5803 | 0.3432 | 0.3681 | 0.3769 |
| recall | 0.8758 | 0.8855 | 0.8911 | 0.5524 | 0.6182 | 0.6220 |
| precision | 0.5779 | 0.5495 | 0.5374 | 0.3923 | 0.3974 | 0.4216 |
| f1 | 0.6963 | 0.6782 | 0.6704 | 0.4588 | 0.4838 | 0.5026 |

n_scored=9983
failed=17
