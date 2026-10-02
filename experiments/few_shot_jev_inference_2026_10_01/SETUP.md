# Data requirements

The source input is the verified zero-shot Jev prepared Study 2 package:

`s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/`

That package has 13,992 rows, 4,051 unanimous rows, and 9,941 split rows. This experiment copies those record bytes and stores its own manifest at:

`s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/`

The prompt has ten demonstrations. Five of them are exact matches to prepared rows, two labeled remove and three labeled keep, and all five rows are unanimous. Model metrics exclude these post IDs. The other five demonstrations do not match a prepared row.

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

Runs are stored under:

`s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/runs/`

Analysis bundles are stored under:

`s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/analysis/`
