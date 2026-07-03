# How to train the language models

This contains a compilation of some thoughts I have around training language models to predict the keep/remove decisions.

We've already trained logistic regression and XGBoost-based models, across a few ablations. Now I'd like to see how language models would fare.

Some variants I'm thinking of include:

- One-shot prompting:
  - With a small model
  - With a large model
- Few-shot prompting:
  - With a small model
  - With a large model
- ModernBERT
- LoRA fine-tuning

I'll also do the prompting ones across two sets of inputs:

- Just the original post
- Original post + mirrored post

We showed users both the original post and the mirrored post as part of the linked fate procedure, and we saw a significant difference in keep/remove decisions based on whether users were in the linked fate condition or if they only saw the original post. However, when we trained our predictive models, we saw that including only the original post was just as predictive as showing both the original and mirrored posts, suggesting that it was the mere presence of the mirrored post that affected whether users chose to keep or remove. We also observed that users in our training condition (where they saw the linked fate procedure for the first half of the study, and only the original posts in the second half of the study) also matched the performance of users in the linked-fate-only condition, censoring outgroup posts less and ingroup posts more as compared to users in the control condition (i.e., only saw the original posts). All of this suggests that the key driver is the mere presence or awareness of the linked fate procedure (i.e., seeing the mirrored posts).

For completeness, we can do some initial experiments that include both the original post and the original post plus the mirrored post. However, I expect those to have non-significant results due to our previous findings suggesting that the mere presence of the mirror, rather than anything about the substance of the mirrored post itself, drove performance. If we replicate that, then we'll continue on training the ModernBERT and LoRA-tuned models with just the original text.

## Experiment 1: Prompting

For the prompting experiments, we'll do them in models/llm_api/{one_shot/few_shot}/{original/original_plus_mirror}/{small/large}/

Each will have a prompt.py and a train.py, for consistency with the other approaches.

For the models, we'll use:

- small: gpt-5.4 nano
- large: gpt-5.5

We'll run these and report the results as a table here, with columns:

- type: one-shot/few-shot
- ablation: original, original plus mirror
- model size: small, large
- model name
- split: train/test
- accuracy, other metrics...

### Prompting results (Experiment 1)
<!-- BEGIN LLM_PROMPTING_RESULTS_TABLE -->
| type     | ablation             | model_size   | model_name   | split   |   accuracy |   precision |   recall |       f1 |   roc_auc |   pr_auc |
|:---------|:---------------------|:-------------|:-------------|:--------|-----------:|------------:|---------:|---------:|----------:|---------:|
| few-shot | original plus mirror | large        | gpt-5.5      | test    |      0.5   |         0.2 |        1 | 0.333333 | 0.571429  | 0.25     |
| few-shot | original plus mirror | large        | gpt-5.5      | train   |      0.625 |         0   |        0 | 0        | 0.0714286 | 0.125    |
| one-shot | original             | small        | gpt-5.4-nano | test    |      0.75  |         0   |        0 | 0        | 0.714286  | 0.333333 |
| one-shot | original             | small        | gpt-5.4-nano | train   |      1     |         1   |        1 | 1        | 1         | 1        |
<!-- END LLM_PROMPTING_RESULTS_TABLE -->

## Experiment 2: ModernBERT

We also want to use ModernBERT to develop a fine-tuned classifier for our task. ModernBERT is an improvement over the original BERT model, with additions like RoPE, FlashAttention, and other techniques from language model research. The 8,192-token context window is a big practical improvement over classic BERT’s usual 512-token limit.

HuggingFace natively supports ModernBERT. In addition, we can use AWS Sagemaker as our trainer in order to avoid having to do local computation. We'll use the base model of ModernBERT, not the large one.

We'd like to use the following:

- Weights and Biases for ML training logging.
- HuggingFace for the interface.
- AWS Sagemaker for the compute.

We'll use the same training data that we used for our other ML models (where each row is 1 post and label). We'll use only the original text, rather than the original text plus the mirrored text.

We'll collect the following metrics:

- Accuracy
- Precision
- Recall
- F1

We'll use cross-entropy loss with 2 labels. Because of our class imbalance, we'll use weighted loss, where we multiply the loss by the class weight. We want to upweight the minority class (`remove=1`) so we prioritize getting those correct. We'll double the loss for `remove=1`. This also lets us improve recall for `remove` labels, but we'll want to be careful as we also don't want many false positives (which worsens our precision).

Our prediction task is "predict remove", so we need to transform the training data to create a binary label.

We'll develop in the following order:

1. Do zero-shot labeling, using the base ModernBERT model and collecting metrics. Here, we'll do a frozen encoder baseline.
2. Fine-tune ModernBERT on the training data and evaluate training curves. We'll evaluate the training curves to review for overfitting.
3. Evaluate calibration curves varying the thresholds from p=0.1 to p=0.9, in increments of 0.1.

We'll store all the work in experiments/predict_keep_remove_2026_07_01/models/modernbert/

We'll use the following file structure:

```markdown
experiments/
  predict_keep_remove_2026_07_01/
    dataloader.py                  # existing raw dataframe loader

    models/
      modernbert/
        README.md
        dataloader.py              # wraps parent dataloader, converts labels
        train.py                   # local/SageMaker-compatible training entrypoint
        evaluate.py                # optional test-set evaluation
        predict.py                 # optional inference helper
        launch_sagemaker.py        # submits remote SageMaker job
        requirements.txt
        configs/
          modernbert_base.yaml
        artifacts/
          .gitkeep                 # local outputs ignored by git
```

For packages, add to requirements.txt and then also add to the root pyproject.toml as optional dependencies titled "modernbert-training".

## Experiment 3: LoRA-tuned models

...
