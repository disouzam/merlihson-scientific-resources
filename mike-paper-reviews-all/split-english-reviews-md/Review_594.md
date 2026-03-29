Review 594: Knowledge Distillation with a "Lego" Approach
Mike’s Daily Paper Review: 29.03.26,  Review #594 
PUZZLE: DISTILLATION-BASED NAS FOR INFERENCE-OPTIMIZED LLMS

A pretty cool paper requested by a good friend, coming from NVIDIA, which is always interesting and unpredictable. The paper proposes a framework called Puzzle for distilling knowledge from a large, powerful LLM (the teacher) into a smaller model that is hardware-optimized (it’s NVIDIA, after all).

The input consists of the teacher model's weights (not its training data). The output is a new model where each layer may have different attention mechanisms, varying FFN (Feed-Forward Network) dimensions, or components that are skipped entirely. These are assembled to maximize throughput, minimize latency, and meet memory requirements on the target GPU.

The framework consists of 3 stages:

Stage 1: Blockwise Local Distillation (BLD)

Each transformer layer in the teacher is treated as a "block" composed of two "sub-blocks": the attention module and the FFN. For every layer, Puzzle defines a set of replacement candidates for each sub-block.

Attention Candidates: Include various types (Standard MHA, GQA, and of course MLA, which gained fame with the legendary DeepSeek paper, linear attention, etc.) with varying head counts, a single linear projection, or a no-op (complete removal).

FFN Candidates: Include the original width plus several reduced intermediate dimensions (down to 10% of the original), a linear layer, or a no-op (meaning no FFN at all, only attention).

Each candidate sub-block is trained independently to mimic the output of its corresponding teacher sub-block using a normalized Mean Squared Error (MSE) loss (normalized by the teacher output's norm). Crucially, each distilled block receives activations from the preceding teacher block. This means blocks are trained in total isolation with no gradient flow between layers, enabling full pipeline parallelism.

The key efficiency trick is "Divide and Conquer": Rather than training every (attention, FFN) pair jointly (grows as AF per layer), Puzzle trains each attention variant alongside a frozen teacher FFN, and each FFN variant alongside a frozen teacher attention, then composes them post-hoc. This reduces training per layer from multiplicative to additive. For Llama-70B (80 layers, 6 attention options, 9 FFN options), this slashes training from 43,200 blocks to just 1,200.

Refinement: The paper admits that decoupled assembly is an approximation, as the interaction between a new attention and a new FFN in the same layer is never directly trained. They suggest a refinement where a decoupled BLD identifies the most common variants, and then a "coupled" BLD is run on that reduced space to keep costs manageable.

Sub-block Initialization:

FFNs: Channels (intermediate layer dimensions) are pruned by ranking their contribution to the final result. This contribution is the product of the activation norm and the L2 norm of the corresponding row in the down-projection matrix, averaged over a training dataset.

Attention (Head Reduction): Each student head is initialized as an average of the teacher's heads (e.g., if the student has 2 heads and the teacher has 8, each student head is the average of 4 teacher heads).

Linear Replacements: The Value and Output projection matrices are multiplied, simulating attention on only a single token (self).

Stage 2: Mixed-Integer Programming (MIP) Search

Each candidate block is scored using a "Replace-1-Block" metric: only one block is swapped into the complete teacher model, and the KL Divergence is measured (the distance between the next-token distributions of the teacher vs. the modified model).

The architecture search is formulated as a Grouped Knapsack Problem. Binary decision variables select exactly one block per layer. The objective is to maximize overall quality (minimizing KL divergence) subject to constraints: total parameter memory, KV-cache memory, runtime, throughput, and latency, all measured empirically on the target hardware.

The MIP is solved repeatedly for different batch sizes, as batch size is not a decision variable but changes the memory-vs-throughput tradeoff. A diversity (entropy) constraint forces successive solutions to differ in a specific number of layers, allowing the exploration of structurally distinct architectures. For Llama-70B, the search space is 10^138 configurations, but because quality is decomposed into per-block scores, the MIP is solved in seconds using off-the-shelf solvers.

The Catch: The additive decomposition assumes block contributions are "independent." This is the core assumption and the main limitation. Errors from early replaced blocks propagate through later blocks that were never trained on such "corrupted" inputs.

Stage 3: Global Knowledge Distillation (GKD)

The assembled student model is trained end-to-end against the teacher using a combination of Cosine Similarity loss on hidden representations (per layer) and KL Divergence between the output logits. Interestingly, the paper finds that adding standard Language Modeling loss (Cross-Entropy on ground truth tokens) hurts performance, likely due to distribution mismatch when the teacher's original training data is unavailable.

What’s New vs. The Closest Baseline?

The direct ancestor is LANA, a NAS method for computer vision. Puzzle’s unique contributions include:

Decoupled BLD (additive training decomposition).

KL-Divergence-based scoring (rather than task-specific accuracy).

Scalability to models with tens of billions of parameters.

Integration with real inference engines supporting variable GQA ratios across layers. This required modifying the paged KV-cache in TensorRT-LLM to handle non-uniform head counts.

https://arxiv.org/abs/2411.19146