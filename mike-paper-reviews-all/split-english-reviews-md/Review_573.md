FusionRoute: Bridging Gaps Between LLMs Via Additional Logit Routing

Mike’s Daily Paper Review: 04.02.26TOKEN-LEVEL LLM COLLABORATION VIA FUSIONROUTE

A paper where I understood the principle quickly, but it took me time to internalize why this idea is necessary for the problem at hand….

The central question in collaboration between multiple language models (Multi-LLM) is the trade-off between coordination resolution and final output stability. Choosing at the Output Level (generating text by everyone and choosing the best one) is coarse and computationally wasteful, as it requires the generation of complete texts from multiple LLMs before a choice can be made. Conversely, previous attempts at collaboration at the Token Level and Task Level (training a model that decides which LLM is suitable for the task) were found to generally work less well, according to the paper. The reason for this lies in the fact that they rely on the assumption (according to the authors) that the available set of LLMs is expressive enough to cover every possible linguistic state. This effectively requires that at least one model in the pool be close to optimal at every single decoding step. The paper presents a method that improves LLM selection using a lightweight router that simultaneously allocates tokens to an LLM and provides a correcting "residual" signal.

The paper is very technical, and the next 3 paragraphs might seem non-trivial and subtle, but they are important. The paper views the process of pure expert selection through the lens of Markov Decision Processes (MDP). Here, the router attempts to select the LLM that maximizes the expected value of future rewards. The authors prove an "Identifiability Failure": training on optimal values along the output alone does not necessarily allow predicting which specific LLM actions (next token prediction) are those that will actually lead to these values in reality (inference). Based on the identifiability failure, the authors argue that designing a reliable method for selecting the optimal model to generate optimal output is particularly difficult. For example, using SFT (Supervised Fine-Tuning) to train a router that selects the optimal model is unreliable, because this is equivalent to Behavior Cloning for learning the actions that maximize the optimal value function Q_{π*}.

The main difficulty is that even if a prompt might theoretically lead to a good answer with our LLMs (i.e., to a state with a large value of Q_π), this answer may not be realizable by the available candidate models. For every token, the set of possible actions is bounded by the fixed expert models. Consequently, whenever the optimal policy π and the expert models are not perfectly aligned, the resulting approximation error becomes uncontrollable.

If the router is limited to choosing from fixed expert outputs only, it is trapped within a policy class that likely does not include the optimal generation policy. This is particularly problematic for models trained for a specific domain; they excel in their niche but produce uncalibrated/unreliable predictions when the context shifts slightly outside their training distribution. To overcome this, FusionRoute expands the effective action space by moving beyond discrete selection toward continuous synthesis in the logit space.

Architectural Innovation: The Complementary Generator

FusionRoute enriches the router's role by splitting its output into two separate channels derived from a shared representation constructed by the models.

LLM Selection: The router generates selection weights by training a learned linear layer on the representations produced by the LLMs. These weights are used to identify the most suitable model for the current token.

Complementary Logits Generation: Simultaneously, the router generates logits (trains a linear layer L) for the next token, meaning it emits a distribution over the token vocabulary of its own (to the best of my understanding, this is done for each model separately).

The Combination: Summing the logits of the selected expert and the router, producing the token distribution, and sampling from it.

By treating the expert output as a base and the router output as a residual, the system can refine, sharpen, or completely override the expert's decision when necessary. This ensures the final policy is not rigidly determined by the distribution of one model, but can approach the optimal policy even when every single expert is locally sub-optimal.

Separated Training and Informative Token Supervision

Training such a system is not trivial because the routing objective and the corrective logits objective might conflict, leading to unstable selection or unstable outputs. The paper uses a two-stage "Mixed Training" strategy to separate these objectives.

SFT Training: The router must first learn to map contexts to model strengths. The authors observe that many tokens, such as punctuation marks or common conjunctions, are predicted identically by all experts and provide no information regarding model specialization. To prevent these "trivial" tokens from influencing the policy, the routing loss is restricted to a "Set of Informative Tokens" meaning positions where the experts actually disagree on the next predicted token.

Complemented Direct Preference Optimization (CDPO): To train the "corrective behavior" (the router's logits), the authors train the linear layer L to align the LLM system to human preferences while considering the model outputs selected by the router. The gradient for L is inversely proportional to the accuracy of the selected model. If an expert is already very confident and correct, the router receives a negligible update. If the expert is weak or uncertain, the gradient increases, forcing the router to "step in" and generate the necessary corrective logits.

The Shift to Expressive Policy Classes

By combining selection weights with additive logits, FusionRoute ensures that the multi-LLM system is fundamentally more expressive than any single model or simple selection mechanism. It bypasses previous methods by having a router that both selects a model for every token and corrects it based on the input. This flexibility is the key factor for the performance improvement of multi-LLM systems in the proposed method.

https://arxiv.org/abs/2601.05106