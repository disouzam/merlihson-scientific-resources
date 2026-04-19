Review 603: The Comeback of Time Series in Foundational Models
Hadar and Mike's Daily Paper Review: 18.04.26, Review 603
Chronos-2: From Univariate to Universal Forecasting

Progress in foundational models for time series is accelerating. In a short period, we have moved from narrow-scope models to systems much closer to what is expected from modern sequence models: multivariate forecasting, known future covariates, uncertainty estimates (with quantiles), and long-context handling. Chronos-2 (from AWS) is an excellent example of this: less because of the branding, and more because the paper is packed with reusable engineering ideas.

Diagram: Chronos-2 Architecture

Let's talk about input, architecture, training, and inference.

Input Chronos-2 treats the input in two parts:

Context window: Historical targets plus covariates (what was observed).

Forecast window: Future covariates known in advance, where future targets are explicitly missing.

Normalization is calculated from the context window itself, for each target dimension, and stored for later de-normalization. This makes scaling robust even when the training set is not homogeneous. The input is enriched with two meta-features:

Masking, which indicates observed versus missing values (future targets and any missing covariate).

Relative time index, so the model knows where each point is located relative to "now" and relative to the forecast horizon.

Architecture: As for input embeddings, Chronos takes the input and generates patches from it. Instead of processing each time point as a token, the authors decided to split each series into non-overlapping patches and encode each patch into a latent representation (using res-blocks). This is primarily intended for scalability (long context) and stability (more structured inputs). This is the equivalent of "tokenization" from the world of language models, adapted for time series, but without converting the values into a discrete vocabulary, and it has been widely used in recent years.

The main innovation, in my opinion, is two attention mechanisms:

Time Attention: Standard self-attention over the patches across time (with positional encoding adapted to the sequence order). This captures temporal dependencies.

Group Attention: Attention across series within a defined group (e.g., related series, multivariate targets, or covariates related to the target). Groups are defined using group IDs, and attention is masked so that tokens only attend to others in the same group.

Note how this breaks the usual convention where items in a batch are independent. Here, the batch dimension is used to share information – group IDs are effectively slices of the batch.

Output and Training: Finally, outputs are produced using quantile regression with more than 20 quantiles, which yields a full set of quantile forecasts for each target along the horizon, optimized with quantile loss.

Training involves many task "shapes" (different numbers of targets/quantiles/forecast horizons) instead of early specialization. A notable choice is the emphasis on synthetic data (including completely synthetic multivariate training data) created to cover a wide range of dynamics and dependencies. This was a decisive decision, as Bernie Wang, one of the lead ML scientists who worked on this model, shared with me in a cohort we participated in together.

The paper looks strong on paper and its design is in-depth. The practical test remains as it was: messy covariates, drift, and operational constraints. Group attention is a unique idea, but it assumes that one can define "who needs to share information with whom" without creating leakage. Ultimately, I was not able to generate zero-shot forecasts on a real-world task at the level I had in mind, and until that happens – we will continue to read new papers.

https://arxiv.org/abs/2510.15821