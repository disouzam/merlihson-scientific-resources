Review 580: LLMs as Operators on Measures: A Clean Mathematical Pipeline for Tokenization, Training, Attention, and Decoding
Mike's daily paper review: 18.02.26

LARGE LANGUAGE MODELS: A MATHEMATICAL FORMULATION

This paper’s novelty is not a new model class, but a disciplined re-expression of the entire modern LLM stack as a sequence of explicit mathematical objects and maps. It reads like an attempt to make LLM engineering “closed under definitions”: every informal block diagram element (tokenization, embedding, attention, learning, decoding) is turned into a precisely typed operator between well-specified spaces. The payoff is methodological clarity. The paper consistently asks: what are the domains and codomains, what is being approximated, what is the learning objective as a population quantity, and what is the deployed algorithm as a stochastic procedure.

Sequences as the primary state space, and tokenization as a measurable map.

The starting move is to treat text as a sequence in a discrete alphabet, then formalize tokenization as a map from raw strings to sequences over a finite vocabulary. The paper is unusually explicit about byte-pair encoding: it describes the iterative merge process as a deterministic construction of a vocabulary and a deterministic parsing of new strings into vocabulary elements. The key methodological point is that tokenization is not “preprocessing”; it is the first mathematical operator in the pipeline, and its properties (finite vocabulary, variable-length segmentation, induced frequency bias) are part of the model, not outside it.

“Making language Euclidean” as an explicit embedding of a discrete simplex into a vector space.

Next, the authors isolate the representational bottleneck that engineering folklore often hand-waves: the model ultimately computes in Euclidean space, but its inputs and outputs are discrete tokens. They formalize the embedding layer as a map from vocabulary indices to vectors, turning sequences of discrete symbols into sequences of vectors. Importantly, they emphasize that this step changes the geometry. Similarities between tokens are no longer about edit distance or co-occurrence directly, but about inner products and norms in the learned representation. This is presented as a deliberate mathematical choice: it creates a continuous stage on which smooth optimization and composition of layers become natural.

They also extend this “Euclideanization” to other modalities. The paper treats images and other non-text inputs as objects that must be encoded into the same kind of token sequence space or into compatible vector sequences, making multimodal processing a question of consistent mappings into a shared sequential representation.

Next-token prediction as an operator-valued approximation problem on distributions over sequences.

The central modeling object is the conditional distribution of the next token given a prefix. The paper frames an autoregressive LLM as a family of conditional probability distributions indexed by the observed prefix, and then makes two critical clarifications: Autoregressive factorization is not a modeling trick; it is the definition of the joint distribution induced by the model once those conditionals are specified. The neural network is an approximation device for a map whose output lives in the probability simplex over the vocabulary.

This is where the paper’s “maps on measures” viewpoint shows up most distinctly: the model takes in a prefix and returns a probability measure on the next token set. Stacking the model through time composes these measure-valued outputs into a full distribution over sequences.

Training is presented first as population risk, then as empirical risk, then as controlled perturbations of the empirical objective.

A major novelty of exposition is the clean hierarchy of objectives:

A population-level objective defined with respect to an underlying data-generating distribution over sequences.

An empirical objective obtained by replacing that distribution with a finite dataset, yielding the standard maximum-likelihood or cross-entropy style training criterion.

Fine-tuning as modifications to the empirical objective rather than an ad hoc “second stage”.

This fine-tuning discussion is method-first: instruction tuning is treated as reweighting or restricting the empirical distribution to a new task-conditioned dataset; preference alignment is treated as changing the target signal from observed next tokens to a learned preference proxy.

Reinforcement learning is integrated as a coherent objective class, not a bolt-on.

The paper’s RL section is careful about what is the “state” (the prefix or conversation history), what is the “action” (the next token or next chunk of tokens), and how rewards are assigned to generated sequences. Conceptually, it positions RLHF-style methods as optimizing a sequence-level functional defined on the rollout distribution induced by the current policy, with the policy being the LLM’s conditional distribution. The novelty here is the alignment of common practice with standard RL objects, making it easier to reason about stability, variance, credit assignment, and the mismatch between token-level decisions and sequence-level reward signals.

Optimization is described as minimizing these objectives under the compositional structure of the network.

Rather than dwelling on heuristics, the paper’s optimization section stresses the structural fact: the objective is a sum over tokens and examples, and gradients flow through a deep composition of maps. This makes stochastic gradient methods a natural computational strategy. The point is less “which optimizer wins” and more “why these objectives admit scalable stochastic approximation”.

Architecture is built from attention as a mathematically typed operator, then extended to Set Transformers and time structure.

The architecture chapter’s distinctive move is to treat attention not as a metaphor but as a specific operator that takes a collection of vectors and produces a new collection via weighted aggregation, where weights are themselves computed by a similarity map. This is essentially a learned, data-dependent averaging operator, and the paper keeps it grounded: queries, keys, and values are linear maps; weights live on a simplex; the output is a convex combination in the value space.

They then connect this to Set Transformers, making explicit a crucial conceptual split: vanilla attention is permutation-equivariant over sets unless temporal or positional structure is injected. That sets up the temporal encoding discussion as a necessary mathematical intervention, not a cosmetic feature. Encoding time, and then attacking quadratic cost with explicit inner-product or map replacements.

The paper is unusually granular about where the quadratic cost comes from: it is the all-pairs interaction implied by computing similarities across sequence positions. The novelty is in taxonomy rather than invention: it classifies efficiency strategies by what they modify:

positional encodings that augment token vectors with position information,

changes to the similarity computation itself to incorporate position or structure,

changes that reduce quadratic complexity by altering the inner product mechanism,

outright replacement of the attention map with an alternative that has cheaper scaling.

This decomposition matters methodologically because it separates “keep attention but compute it smarter” from “replace attention with a different operator”, and it lets you reason about what invariances or expressivity you are sacrificing.

Sequence generation is treated as a decision procedure operating on the learned conditional distribution.

Decoding is presented as its own algorithmic layer: once you have a conditional distribution, deployment means choosing a procedure to produce a concrete sequence. The paper cleanly distinguishes deterministic rules (greedy-style) from stochastic rules (sampling-based), and also covers mixed procedures that combine both. The important methodological point is that decoding is not part of the trained model, but it strongly shapes the induced distribution of outputs at inference time. In this formulation, “the LLM” is incomplete without a specified decoding operator.

Diffusion-based models appear as an alternative probabilistic mechanism, to situate autoregression.

Finally, diffusion-based generation is introduced as a contrasting paradigm: rather than building a joint distribution by sequential conditioning, it constructs generation by iteratively transforming noise toward data. The novelty here is the clean conceptual comparison: autoregression is a chain of conditional measures over discrete tokens; diffusion is an iterative stochastic transformation in a continuous (or discretized) space, usually tied to denoising objectives.

Overall, the paper’s contribution is a rigorous, end-to-end mathematical typing of the LLM workflow. It gives you a language to ask sharper questions about what exactly is being approximated, where randomness enters, which operators are learned versus chosen, and how architectural variants correspond to substituting one well-defined map for another.

https://arxiv.org/abs/2601.22170