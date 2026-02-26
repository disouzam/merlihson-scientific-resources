Review 583: Conceptual-Level Planning in Latent Space
Mike’s Daily Paper Review: 02.24.26
Next Concept Prediction in Discrete Latent Space Leads to Stronger Language Models

You might remember the paper on Concept Language Models that I reviewed about six months ago. Well, there is a follow-up, and I’m happy about it because I really liked the original idea.

The paper we are reviewing today introduces Next Concept Prediction (NCP), a pretraining paradigm that adds a high-level prediction objective on top of standard token-level modeling. The central object of the research is ConceptLM, an approach designed to model discrete concepts (you heard that right, discrete) that span several consecutive tokens within a discrete latent space. As a reminder for those who forgot: a latent space is an abstract mathematical space where the model encodes semantic relationships between input tokens, placing similar concepts closer to one another (hopefully). The input here is, of course, a sequence of tokens, and the output is a dual prediction of both high-level conceptual units and the tokens that comprise them.

The Process: From Tokens to Concepts

The process begins with a token-level encoder, which converts input tokens into continuous hidden representations (in the latent space). To transition from tokens to concepts, the model applies mean pooling over groups of adjacent hidden representations. This process reduces the sequence length and essentially constructs a series of continuous vector representations (in $\mathbb{R}^d$) of the concepts.

To create a prediction target for concept modeling, the paper builds a discrete concept dictionary using Vector Quantization (VQ). Vector quantization is a technique from the world of signal processing that maps high-dimensional continuous vectors to a finite set of vectors called "codebook entries." To ensure this set is expressive enough to "understand" complex patterns with a sufficiently small dictionary, the authors use Product Quantization (PQ). This is a method where a high-dimensional vector is divided into several segments, and each segment undergoes quantization against its own smaller codebook. This allows the model to represent a vast number of unique concepts through the combinatorial combination of these segments. Finally, there is a decoder that transforms the concepts back into tokens.

Training and Loss Functions

The training process includes three main components:

Standard Token-Level Loss: Uses Cross-Entropy to "supervise" the next-token prediction (after the decoder).

NCP Loss: Uses Mean Squared Error to approximate predicted concepts to the model's continuous latent representations. (From what I understand, the concepts are built from the token representations of the model's last layer).

Quantization Loss: Attempts to bring the codebook entries closer to their true latent representations.

To prevent the model from simply "memorizing" future tokens through the concept target, the predicted concept sequence is shifted forward. This ensures the model generates the concept before the corresponding tokens are created.

Inference and Innovation

During inference, the concept-level module uses Transformer layers to process historical concept representations and predict the discrete representation of the next concept (from the codebook). Instead of selecting a single concept, the model generates a weighted combination of codebook entries based on predicted probabilities. This predicted concept is passed back to the token level and merged with the initial encoder hidden representations (via element-wise addition). The decoder then uses this representation to generate tokens autoregressively.

As mentioned, the innovation of this method is the shift from prediction in token space to a discrete latent space. Standard baselines like Next-Token Prediction or Multi-Token Prediction (MTP) remain limited to the vocabulary predefined by the tokenizer. ConceptLM, by contrast, creates its own dictionary of learnable high-level abstractions. This approach relies on the assumption that language has a hierarchical structure where multiple tokens aggregate into stable semantic units.

One potential failure mode the authors address is representation collapse—a common problem in quantization where most inputs are mapped to only a few codebook entries or produce representations that are too close to each other, rendering the dictionary useless. The authors mitigate this by applying a learned two-layer MLP network to the codebook representation. According to the paper (referencing another paper called SimVQ), this "spreads out" the representations. In other words, even if two vectors are close in the codebook, this two-layer network pushes them apart.

Efficiency and Scaling

The method changes the scaling behavior of the model's internal processing. By compressing the sequence length by a factor of k in the concept layers, the model achieves a k^2 reduction in the computational load of the attention mechanism. Additionally, processing concepts instead of individual tokens reduces the KV-Cache, which helps alleviate memory bandwidth bottlenecks. The authors note that while deeper encoders provide more refined representations for concept prediction, there is a trade-off between the depth of the encoder and the computational savings achieved from the compressed concept sequence.

https://arxiv.org/abs/2602.08984