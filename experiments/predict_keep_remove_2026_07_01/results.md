# Results

## Study 1: Feasibility of Predicting Keep/Remove Decisions

### Motivation

...

### Formulating the task

...

### Dataset

Prolific participants (n=1,321) reviewed pairs of original and mirrored posts (n=959 pairs), resulting in a final dataset of n=13,250 rows, with each row representing a human keep/remove decision for the pair of posts. In these "linked fate" trials, the users saw both the original post and its mirrored equivalent, randomly ordered, and were asked to make a keep/remove decision for the pair. In this dataset, 66.2% of post pairs were kept (and 33.8% removed). We create training labels for each post by taking the modal label across all raters (average n=13.8 labels per post).

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

Caption: Model performance for predicting keep/remove decisions. Precision, recall, F1, and ROC-AUC are computed with the remove decision as the positive class ($y=1$).

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

## Study 2

In Study 2, ...

(initial results from Study 2)

### Model performance

(model performance)

#### Scaling curves
