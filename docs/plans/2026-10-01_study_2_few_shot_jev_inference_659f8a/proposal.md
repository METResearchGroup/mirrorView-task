# Proposal: Few-shot Jev inference on the Study 2 dataset

Scope: [issue 345](https://github.com/METResearchGroup/mirrorView-task/issues/345). The proposal covers the few-shot Jev experiment, its exact prompt, its S3 artifacts, and its analysis. It reuses the completed zero-shot Jev implementation from [issue 330](https://github.com/METResearchGroup/mirrorView-task/issues/330) and [PR 341](https://github.com/METResearchGroup/mirrorView-task/pull/341). It copies the prompt and demonstration-overlap policy from [issue 329](https://github.com/METResearchGroup/mirrorView-task/issues/329). The issue 345 implementation does not depend on the separate issue 329 implementation.

## Overview

The new experiment will run Jev 1.13.0 on the same 13,992 five-labeler Study 2 pairs used by the zero-shot Jev experiment. Each Jev request will contain issue 329's ten labeled demonstrations, the current pair in classifier state, and one yes-or-no removal question. The experiment will store one remove probability and one label per pair, then report F1, accuracy, recall, and precision for the all, unanimous, and split datasets.

The implementation will reuse the root Jev client and the zero-shot Jev experiment's setup, resume, storage, and analysis code. The few-shot package will contain the exact prompt, one experiment configuration, one request adapter, and three thin entry points.

## Cross-cutting concerns

### Reuse boundary

The root package `shared/models/jev/` already contains the parts that are independent of an experiment. Issue 345 will reuse `build_jev_scorer`, `JevScorer`, `JevResult`, and `RequestStartLimiter` without changing that package or `langchain-typesafe==0.0.1a3`.

The reusable experiment runners remain under `experiments/zero_shot_jev_inference_2026_10_01/`. The new few-shot package imports those runners. The zero-shot package never imports from the few-shot package, and root `shared/` never imports from `experiments/`.

Issue 345 is the second Jev keep-or-remove experiment, so the existing runners now have a concrete second configuration. The change adds one frozen configuration model and one request-builder argument while keeping one copy of the inference and analysis code.

| Existing code | Symbols reused by issue 345 |
| --- | --- |
| `shared/models/jev/client.py` | `get_jev_api_key`, `build_jev_classifier` |
| `shared/models/jev/scorer.py` | `JevScorer`, `build_jev_scorer`, `parse_response` |
| `shared/models/jev/schemas.py` | `JevResult` |
| `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py` | `build_remove_instructions`, `build_remove_request`, `to_prediction_record` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py` | `prepare_input`, `_reject_invalid_input` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py` | `run_inference`, resume checks, concurrent batches, immutable writes |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py` | `run_analysis`, `build_analysis_tables`, `build_usage_row` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py` | `render_results_fragment` |

### Prompt contract

`BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` will preserve issue 329's text, example order, labels, placeholders, spacing, punctuation, and line breaks. The template has no final newline after `Allow Or Remove?`. Its UTF-8 SHA-256 is `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`.

Jev accepts classifier state and `Noul` instructions instead of a rendered chat message. The zero-shot `build_remove_instructions` helper cannot transform the few-shot prompt because it requires the dynamic pair block at the end. The few-shot adapter will therefore define `build_few_shot_remove_instructions`. The helper will require one dynamic `Post 1` and `Post 2` placeholder block before the demonstrations and one terminal `Allow Or Remove?`. It will remove only that placeholder block, preserve all ten demonstrations, and replace the terminal question with the existing `REMOVE_QUESTION`, which refers to `state["post_1"]` and `state["post_2"]`.

The transformed instructions are 6,000 UTF-8 bytes with SHA-256 `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac`. The run manifest will store the source prompt digest and this transformed-instructions digest. The analysis manifest already points to the final run manifest, so it will not copy those fields.

The readable copy below marks each of the source prompt's two otherwise invisible trailing U+0020 bytes as `⟦SPACE⟧`. The implementation will replace each marker with one literal space before checking the byte count and digest.

```markdown
We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.


The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.


Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

Post 1: {post_1_text}

Post 2: {post_2_text}

Here are examples of pairs of posts that human annotators remove:

1. Post 1: Conservative Christians are on the side of the capitalist class or billionaires and should be physically fought. #communism #socialism Post 2: Radical leftists are on the side of the globalist elites and government tyrants and should be physically fought. #MAGA #freedom

2. Post 1: Fuck this smug DNC-groomed hypocrite. The day he actually fights for the Second Amendment will be the first day, since he's been kissing up to nothing but coastal elites and radical activists who want to strip law-abiding citizens of their rights entirely (see AOC and her defund-the-police crowd). Post 2: Fuck this entitled GOP raised asshole. The day he's a force in the fight for gun control will be the first day since he kisses up to nothing but entitled white men who have no issue with guns at all (see Bernie and the Nazi).

⟦SPACE⟧
3. Post 1: Woke, DEI, social justice, critical race theory, politically correct, civil rights, restorative justice, reparations... Just use the hard R, this is taking forever Post 2: MAGA, Christian nationalism, originalism, states' rights, traditional values, heritage, America First, constitutional conservatism... Just say white supremacy, this is taking forever

4. Post 1: And why there are far fewer soy-brained libtard town hall meetings to 'splain why Biden's corruption and cognitive decline is good for them . . they don't want to be held accountable, the spineless cowards .. Post 2: And why there are far fewer cuckservative Rethuglicunt town hall meetings to 'splain why #Trump 's fuckery and criminal behavior is good for them . . they don't want to be yelled at, the spineless cowards ..

5. Post 1: Democrats will never be an honest decent party with integrity, generosity, and warmth – it's all about grasping for power and quite a bit about exploiting the vulnerable! Post 2: Republicans will never be an honest decent party with integrity generosity and warmth – it's all about cold hard cash and quite a bit about raping children!


Here are examples of pairs of posts that human annotators keep:

1. Post 1: If everyone who says something to the effect of "gun rights are important for hunters" understood how stupid the average Wisconsinite hunter is - and how drunk they get by 7am with guns in hand - we would not have gun ownership in this country Post 2: If everyone who says something to the effect of "we need stricter gun control" understood how absolutely clueless the average coastal liberal is about firearms - and how they've never touched a gun in their life yet lecture everyone about them - we would not take gun grabbers seriously in this

2. Post 1: For decades the US left told us we shouldn't impose American values on other⟦SPACE⟧
countries — sovereignty matters, they said. But now they're falling all over themselves to copy Europe's socialist failures: crushing taxes, open borders, and state-controlled speech. Post 2: For decades we were told by the US rightwing that we shouldn't look to other countries in how to run things (healthcare, gun safety, and consumer regulations were proposed) but the rightwing is all in in emulating Hungary under Orban. To paraphrase Clinton: "it's the authoritarianism, stupid."

3. Post 1: always under siege Second Amendment. Lloyd Smucker has my Complete and Total Endorsement for Re-Election. Election Day is Tuesday, May 19th. GET OUT AND VOTE FOR LLOYD — HE WILL NEVER LET YOU DOWN! Post 2: They never stop coming for your right to choose. Planned Parenthood PAC has my Complete and Total Endorsement for every candidate fighting to protect reproductive freedom. Election Day is Tuesday, November 5th. GET OUT AND VOTE FOR CHOICE — THESE CANDIDATES WILL NEVER LET YOU DOWN!

4. Post 1: The Secretary of State should be charged with voter suppression by making it harder for working people to cast their ballots in person. Expand mail voting now. Post 2: The Postmaster General of the US should be charged with violation of law by breaking down the mail ballot system. Go vote in person

5. Post 1: I take exception to some of how the definition of "assault weapon" is formed. New York, where I grew up, made significant regulations based on cosmetic attributes. Post 2: I take exception to how the right keeps pretending 'assault weapon' is impossible to define. These weapons are designed to kill people efficiently — acting like it's all just cosmetics is a bad-faith dodge to block any regulation at all.


Allow Or Remove?
```

### Demonstration overlap

The issue 329 prompt audit found five normalized exact matches between the ten demonstrations and the 13,992 prepared input rows. The matches contain two remove examples and three keep examples. All five are in the unanimous dataset. Issue 345 will predict every row so that its stored output remains comparable with the zero-shot run, but its model metrics will exclude these five post IDs:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

The metric partitions will therefore contain 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows. Human label counts and split-vote counts will continue to describe all 13,992 rows.

### Data and S3 isolation

The setup entry point will read the verified input from the zero-shot Jev experiment and copy `records.jsonl` byte for byte into the few-shot Jev prefix. A new input manifest will point to the copied records. It will retain the source digest, dataset names, counts, and first and last post IDs. The setup step will not query the registered datasets again.

All new artifacts will live under `s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/`. The implementation will not change the zero-shot Jev artifacts or the issue 329 experiment artifacts.

### Model and response contract

The experiment will use Jev 1.13.0 through `TypeSafeClassifier`. Each request will ask one `Noul` question with explicit allow and remove criteria. `p_remove` is the returned probability of yes, and `is_remove` is true when `p_remove >= 0.5`.

The experiment will keep the zero-shot Jev limits of 8 workers, batches of 500, and at most 1,000 request starts per minute. Each request will have three retries for transient errors. Predictions, failures, run manifests, and analysis artifacts remain immutable and resumable.

## File structure

### Repository

```text
docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/
  proposal.md                                      this proposal

experiments/zero_shot_jev_inference_2026_10_01/
  shared/
    config.py                                      new JevInferenceVariant and ZERO_SHOT_VARIANT
    constants.py                                   route zero-shot paths through ZERO_SHOT_VARIANT
    jev.py                                         accept compiled instructions at the request boundary
    schemas.py                                     add stored experiment and prompt identity to run manifests
    storage.py                                     build keys from the active variant
  src/
    step1_setup/prepare.py                         expose the reusable input-copy runner
    step2_inference/run.py                         accept a variant and RemoveRequestBuilder
    step3_analysis/analyze.py                      accept a variant and metric exclusions

experiments/few_shot_jev_inference_2026_10_01/
  README.md                                        links to SETUP.md and RESULTS.md
  SETUP.md                                         required data and artifact locations
  RESULTS.md                                       generated result tables and run identity
  __init__.py
  shared/
    __init__.py
    config.py                                      FEW_SHOT_VARIANT and five metric exclusions
    prompts.py                                     exact issue 329 prompt
    jev.py                                         dedicated few-shot transformation and request adapter
  src/
    __init__.py
    step1_setup/
      __init__.py
      main.py                                      copy and verify prepared input
    step2_inference/
      __init__.py
      main.py                                      run resumable few-shot Jev inference
    step3_analysis/
      __init__.py
      main.py                                      analyze one complete few-shot run
```

`shared/models/jev/`, `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`, and `experiments/zero_shot_llm_inference_2026_09_30/` remain unchanged.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/
  inputs/
    study_2_five_labeler/
      records.jsonl                                byte copy of zero-shot Jev input
      manifest.json                                few-shot key, source digest and counts
  runs/
    RUN_ID/
      jev_1_13_0/
        predictions/batch-000000.jsonl ...
        failures/batch-000000.jsonl ...
        manifests/manifest-000000.json ...
  analysis/
    RUN_ID/
      label_counts.csv
      split_remove_vote_counts.csv
      model_metrics.csv
      usage.csv
      results_fragment.md
      analysis_manifest.json
```

## Schema and key interfaces

| Model or interface | Lives in | Status and role |
| --- | --- | --- |
| `JevInferenceVariant` | `experiments/zero_shot_jev_inference_2026_10_01/shared/config.py` | New frozen dataclass. Fields are `experiment_name`, `s3_bucket`, `s3_prefix`, `input_records_key`, `input_manifest_key`, `run_manifest_schema_version`, `prompt_name`, `prompt_sha256`, `instructions_sha256`, and `metric_exclusion_post_ids`. It stays in memory. |
| `RemoveRequestBuilder` | `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py` | New callable type from `Study2InputRecord` to `ClassifierRequest`. It stays in memory. |
| `JevResult` | `shared/models/jev/schemas.py` | Reused without field changes. It stays in memory until the adapter creates a prediction row. |
| `Study2InputRecord`, `InputManifest`, `PredictionRecord`, `FailureRecord`, `RemovePrediction`, `TokenUsage` | `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py` | Reused without field changes. Input, prediction, and failure rows remain stored as JSONL. |
| `JevRunManifest` | `experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py` | Extended with `experiment_name`, `prompt_name`, `prompt_sha256`, and `instructions_sha256`. Older zero-shot manifests load with zero-shot defaults. |
| `JevAnalysisManifest` | `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py` | Extended with `metric_exclusion_post_ids`. Its existing `final_run_manifest_key` points to the stored experiment and prompt identity. |

The reusable boundaries will have these signatures:

```python
copy_prepared_input(
    store: CampaignObjectStore,
    source: JevInferenceVariant,
    target: JevInferenceVariant,
) -> InputManifest

run_inference(
    store: CampaignObjectStore,
    scorer: JevScorer,
    variant: JevInferenceVariant,
    request_builder: RemoveRequestBuilder,
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> JevRunManifest

run_analysis(
    store: CampaignObjectStore,
    variant: JevInferenceVariant,
    run_id: str,
) -> str
```

## Steps

### Step 1: Parameterize the completed zero-shot Jev runners

Add `JevInferenceVariant` and pass it through the existing setup, storage, inference, and analysis boundaries. Pass a request builder into `run_inference`. Keep the current zero-shot entry points as wrappers around `ZERO_SHOT_VARIANT`, so the completed zero-shot commands and stored manifests remain readable.

### Step 2: Add the few-shot prompt and request adapter

Create the exact issue 329 prompt, compile it through `build_few_shot_remove_instructions`, and define `FEW_SHOT_VARIANT`. The adapter will put the current post texts in classifier state and use the compiled prompt as the one removal question's instructions. The transformation will reject missing or duplicate placeholder blocks, a missing terminal question, and any text after the terminal question.

### Step 3: Prepare an identical input package

Read the zero-shot Jev input records and manifest, verify their digest and counts, and write the same record bytes under the few-shot Jev prefix. Write a few-shot manifest that points to the copied records.

### Step 4: Run few-shot Jev inference

Run a bounded smoke sample before the full process so `RESULTS.md` can replace the proposal's token, cost, and runtime estimates with measurements. The full process will score all 13,992 pairs and will resume from valid stored predictions after an interruption.

### Step 5: Analyze and report the run

Reuse the zero-shot Jev label counts, split-vote counts, classification metrics, usage totals, and Markdown renderer. Exclude the five exact demonstration matches only from model metrics, store those IDs in the analysis manifest, and write the final tables to `RESULTS.md`.

## Expected results

A complete run will store 13,992 valid predictions under `jev_1_13_0/` with no unresolved failures. The analysis will write six human label rows, four split-vote rows, three model metric rows, one usage row, and six immutable analysis artifacts.

The zero-shot Jev production run measured 10,162,373 input tokens for 13,992 requests, or 726 input tokens per request. It cost $0.426820. The exact few-shot template is 5,953 UTF-8 bytes, compared with 1,454 bytes for the zero-shot template. A rough estimate adds one token per four added bytes to the measured zero-shot average. The range is 20 percent because Jev's tokenizer and request wrapper are not exposed.

| Estimate | Input tokens per request | Total input tokens | Cost at $0.042 per million input tokens |
| --- | ---: | ---: | ---: |
| Low | 1,481 | 20.7M | $0.87 |
| Median | 1,851 | 25.9M | $1.09 |
| High | 2,221 | 31.1M | $1.31 |

The configured rate limit gives an estimated lower runtime bound of 14 minutes for 13,992 requests. The proposal does not assign an upper runtime estimate because the repository has no measured few-shot Jev latency. The five-row smoke run will provide the measured token, cost, and runtime estimate before the full run.

The metric tables will use 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows if decision 2 is confirmed. Metric values cannot be estimated before inference.

## Confirmed decisions

1. **Confirmed: Parameterize the zero-shot Jev runners instead of copying them.** Add `JevInferenceVariant` and a request-builder argument because issue 345 is the second concrete Jev keep-or-remove experiment.
2. **Confirmed: Exclude the five exact demonstration matches from model metrics.** Predict all 13,992 pairs but score 13,987, which matches the approved issue 329 policy and avoids evaluating Jev on prompt examples.
3. **Confirmed: Copy the prepared input into the few-shot Jev S3 prefix.** Copy `records.jsonl` byte for byte and write a target manifest with the same digest and counts.
4. **Confirmed: Store both prompt digests in the run manifest.** Store the issue 329 template digest `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3` and the transformed Jev-instructions digest `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac`. The analysis manifest will refer to the final run manifest instead of copying both fields.
5. **Confirmed: Add no unit test files.** Use executable smoke checks for contracts, imports, failure cases, S3 isolation, bounded live inference, resume behavior, and analysis output.
