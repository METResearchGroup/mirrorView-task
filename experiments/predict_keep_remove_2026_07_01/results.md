---
header-includes:
  - \usepackage[margin=0.5in]{geometry}
  - \usepackage{lmodern}
  - \usepackage[T1]{fontenc}
---

# Results

## Study 1: Feasibility of Predicting Keep/Remove Decisions

### Motivation

We asked users to evaluate whether, if shown a social media post and its mirrored version (which preserves topic and intensity but flips the political stance), users would choose to keep both posts or remove both posts from a hypothetical social media platform. We then trained ML models to see if we could predict, given a post and its mirrored counterpart, whether participants would, on average, choose to keep or remove the pair.

### Dataset

Prolific participants (n=1,321) reviewed pairs of original and mirrored posts (n=959 pairs), resulting in a final dataset of n=13,250 rows, with each row representing a human keep/remove decision for the pair of posts. In these "linked fate" trials, the users saw both the original post and its mirrored equivalent, randomly ordered, and were asked to make a keep/remove decision for the pair. In this dataset, 66.2% of post pairs were kept and 33.8% were removed. We create training labels for each post by taking the modal label across all raters (average n=13.8 labels per post).

### Training an initial set of models with explainable text features

We first generated a set of explainable text features:

- Does the text involve intergroup discussion?
- Does the text have PRIME content?
- Does the text have a positive valence?
- Does the text have toxic content?
- What is the political stance of the text?
- What is the number of characters in the text?
- What is the average sentence length?
- What is the Flesch-Kincaid reading score?

We then trained two models on these features: a logistic regression model and an XGBoost model. We report those results in a table

We report the model performance for predicting keep/remove decisions. Precision, recall, F1, and ROC-AUC are computed with the remove decision as the positive class ($y=1$).

$$
\begin{array}{llrrrrr}
\hline
\text{Model} & \text{Split} & \text{Accuracy} & \text{Precision} & \text{Recall} & \text{F1} & \text{ROC-AUC} \\
\hline
\text{Baseline (always predict keep)} & \text{Test} & 0.649 & 0.000 & 0.000 & 0.000 & 0.500 \\
\text{Logistic regression} & \text{Train} & 0.699 & 0.572 & 0.407 & 0.475 & 0.675 \\
\text{Logistic regression} & \text{Test} & 0.695 & 0.597 & 0.402 & 0.480 & 0.678 \\
\text{XGBoost} & \text{Train} & 0.737 & 0.667 & 0.430 & 0.523 & 0.777 \\
\text{XGBoost} & \text{Test} & 0.693 & 0.603 & 0.367 & 0.457 & 0.702 \\
\hline
\end{array}
$$

We notice a slight lift in the logistic regression and XGBoost models as compared to a naive baseline, driven by improvements in recall of remove decisions. We also observe likely overfitting on the XGBoost model given the sparsity of our n=959 dataset.

#### Scaling curves

We also generated scaling curves by varying the proportion of the n=959 posts used in the training vs. test sets.
![XGBoost scaling curves](experiments/predict_keep_remove_2026_05_07/outputs/scaling_curves/2026_07_02-14:33:42/results.png)

From our scaling curves, we don't see much improvement in recall and we only see slight gains in precision and overall accuracy. We have a small dataset size overall so it's unlikely that we have the sample size to learn sufficient signal.

### Training models based on the text embeddings (Study 2)

#### Dataset (embedding models)

We also trained additional predictive models based on text embeddings. We used Amazon Bedrock's Titan Text Embeddings (`amazon.titan-embed-text-v2:0`), with `d=256` dimensions. The embeddings were also L2-normalized.

We generated the following vectors:

- The original embedding vector, with shape `(256,)`.
- The mirrored post's embedding vector, with shape `(256, )`.
- The elementwise absolute difference between the original and mirrored post's vectors, with shape `(256, )`.
- The Hadamard elementwise product between the original and mirrored post embedding vectors, with shape `(256, )`.
- The scalar cosine similarity between the original and mirrored posts, with shape `(1,)`.
- One-hot vector of the original post's political stance (left vs. right), with shape `(2,)`.
- One-hot vector of the original post's toxicity category (low, middle, high), with shape `(3,)`.

We then stack these vectors into a single feature vector with shape `(1030,)`, creating a dataset with shape `(959, 1030)` for our posts.

#### Results (embedding models)

We show the model performance for predicting keep/remove decisions using Bedrock text embeddings. Precision, recall, F1, and ROC-AUC are computed with the remove decision as the positive class ($y=1$).

$$
\begin{array}{llrrrrr}
\hline
\text{Model} & \text{Split} & \text{Accuracy} & \text{Precision} & \text{Recall} & \text{F1} & \text{ROC-AUC} \\
\hline
\text{Baseline (always predict keep)} & \text{Test} & 0.649 & 0.000 & 0.000 & 0.000 & 0.500 \\
\text{Logistic regression} & \text{Train} & 0.897 & 0.686 & 0.944 & 0.795 & 0.966 \\
\text{Logistic regression} & \text{Test} & 0.849 & 0.620 & 0.756 & 0.681 & 0.879 \\
\text{XGBoost} & \text{Train} & 1.000 & 1.000 & 1.000 & 1.000 & 1.000 \\
\text{XGBoost} & \text{Test} & 0.859 & 0.750 & 0.512 & 0.609 & 0.860 \\
\hline
\end{array}
$$

We observe that logistic regression generalizes better on the test set in terms of F1 and recall. XGBoost overfits more strongly, which we believe to be a symptom of the relatively small sample size. However, overall, training on the text embeddings themselves was much more performant than training on the hand-crafted text features.

We compare the results of the logistic regression and XGBoost models trained on the hand-crafted features versus the text embeddings in the following graph:

![Test-set metric line graph](experiments/predict_keep_remove_2026_07_01/outputs/test_metrics_linegraph/2026_07_02-17:46:52/results.png)

## Study 2

In Study 2, we expanded on the work from Study 1.

### Dataset

Prolific participants (n=1,176) reviewed pairs of original and mirrored posts (n=8,791 pairs), resulting in a final dataset of n=23,560 rows, with each row representing a human keep/remove decision for the pair of posts. In these "linked fate" trials, the users saw both the original post and its mirrored equivalent, randomly ordered, and were asked to make a keep/remove decision for the pair. In this dataset, 68% of post pairs were kept and 32% were removed. We create training labels for each post by taking the modal label across all raters (average n=2.68 labels per post).

### Training models based on the text embeddings

We chose to focus on using text embeddings as features for our predictive models based on their vastly superior performance as compared to the hand-crafted features.

#### Training logistic regression and XGBoost models

##### Ablation 1: Concatenating the original post and mirrored post's embedding vectors

We trained a series of logistic and XGBoost models. We first trained a series of models using feature vectors generated by concatenating the original post's embedding vector and the mirrored post's embedding vectors:

- The original post's embedding vector, with shape `(256,)`.
- The mirrored post's embedding vector, with shape `(256, )`.

We then stack these vectors into a single feature vector with shape `(512,)`, creating a dataset with shape `(8,791, 512)` for our posts.

$$
\begin{array}{llrrrrr}
\hline
\text{Model} & \text{Split} & \text{Accuracy} & \text{Precision} & \text{Recall} & \text{F1} & \text{ROC-AUC} \\
\hline
\text{Logistic regression} & \text{Train} & 0.719 & 0.548 & 0.689 & 0.611 & 0.777 \\
\text{Logistic regression} & \text{Test} & 0.671 & 0.490 & 0.623 & 0.548 & 0.716 \\
\text{XGBoost} & \text{Train} & 0.999 & 0.997 & 1.000 & 0.998 & 1.000 \\
\text{XGBoost} & \text{Test} & 0.720 & 0.583 & 0.435 & 0.498 & 0.718 \\
\hline
\end{array}
$$

### Baseline results (original + mirrored post embeddings)

We first trained a series of models using feature vectors generated by concatenating the original post's embedding vector and the mirrored post's embedding vectors:

- The original post's embedding vector, with shape `(256,)`.
- The mirrored post's embedding vector, with shape `(256, )`.
- The cosine similarity of the two embeddings, as a float value with shape `(1,)`.

We then stack these vectors into a single feature vector with shape `(513,)`, creating a dataset with shape `(8,791, 513)` for our posts.

$$
\begin{array}{llrrrrr}
\hline
\text{Model} & \text{Split} & \text{Accuracy} & \text{Precision} & \text{Recall} & \text{F1} & \text{ROC-AUC} \\
\hline
\text{Logistic regression} & \text{Train} & 0.719 & 0.548 & 0.689 & 0.611 & 0.777 \\
\text{Logistic regression} & \text{Test} & 0.671 & 0.490 & 0.623 & 0.548 & 0.716 \\
\text{XGBoost} & \text{Train} & 0.999 & 0.997 & 1.000 & 0.998 & 1.000 \\
\text{XGBoost} & \text{Test} & 0.720 & 0.583 & 0.435 & 0.498 & 0.718 \\
\hline
\end{array}
$$

### Ablations for training the logistic and XGBoost models

We also defined a series of ablations for the data used for training:

| Name | Description (1 sentence) | Relevant train python files |
| --- | --- | --- |
| `Original post + mirrored post embeddings` | Train on concatenated original and mirrored embeddings plus a cosine similarity feature. | `models/logistic_regression/train.py`, `models/xgboost/train.py` |
| `difference_embedding (orig_emb - mirror_emb)` | Train on the elementwise embedding difference (orig_emb - mirror_emb) only (no mirror embedding, no cosine). | `models/logistic_regression/train_difference_embedding.py`, `models/xgboost/train_difference_embedding.py` |
| `only_original_post_embedding` | Train on the original post embedding vector only (no mirror embedding, no cosine). | `models/logistic_regression/train_only_original_post_embedding.py`, `models/xgboost/train_only_original_post_embedding.py` |

#### Ablation results

$$
\begin{array}{llrrrrr}
\hline
\text{Model} & \text{Split} & \text{Accuracy} & \text{Precision} & \text{Recall} & \text{F1} & \text{ROC-AUC} \\
\hline
\text{Logistic regression (Original post + mirrored post embeddings)} & \text{Train} & 0.719 & 0.548 & 0.689 & 0.611 & 0.777 \\
\text{Logistic regression (Original post + mirrored post embeddings)} & \text{Test} & 0.671 & 0.490 & 0.623 & 0.548 & 0.716 \\
\text{Logistic regression (difference embedding)} & \text{Train} & 0.620 & 0.433 & 0.612 & 0.507 & 0.663 \\
\text{Logistic regression (difference embedding)} & \text{Test} & 0.588 & 0.398 & 0.565 & 0.467 & 0.607 \\
\text{Logistic regression (only original)} & \text{Train} & 0.692 & 0.515 & 0.659 & 0.578 & 0.748 \\
\text{Logistic regression (only original)} & \text{Test} & 0.673 & 0.491 & 0.623 & 0.549 & 0.710 \\
\hline
\text{XGBoost (Original post + mirrored post embeddings)} & \text{Train} & 0.999 & 0.997 & 1.000 & 0.998 & 1.000 \\
\text{XGBoost (Original post + mirrored post embeddings)} & \text{Test} & 0.720 & 0.583 & 0.435 & 0.498 & 0.718 \\
\text{XGBoost (difference embedding)} & \text{Train} & 0.997 & 0.992 & 0.998 & 0.995 & 1.000 \\
\text{XGBoost (difference embedding)} & \text{Test} & 0.660 & 0.446 & 0.258 & 0.327 & 0.607 \\
\text{XGBoost (only original)} & \text{Train} & 0.993 & 0.983 & 0.996 & 0.990 & 1.000 \\
\text{XGBoost (only original)} & \text{Test} & 0.708 & 0.553 & 0.460 & 0.502 & 0.704 \\
\hline
\end{array}
$$

![Ablation test-set metric bar graph](experiments/predict_keep_remove_2026_07_01/outputs/study_2_ablations_test_metrics_bargraph/2026_07_03-14:49:54/results.png)

#### Fine-tuning a language model

(LoRA tuning?)

#### Scaling curves (Study 2)

(put scaling curves here)

### Explainability

(explainability work)

#### Developing hand-crafted explainable features

We compiled a taxonomy with the following features:

- (foo bar)

(Exploratory analyses of the explainable features and if we see any trends).

#### Training a model using the explainable features

(we can train on both (1) just the top N explainable features and (2) text embeddings + top N explainable features).

### Calibration

(calibration work)
