Review 579: The “Aha” That Wasn’t: When Language Models Only Pretend to Think

The “Aha” That Wasn’t: When Language Models Only Pretend to Think

Omri and Mike’s Daily Paper, 16.02.26The Illusion of Insight in Reasoning Models

We have already heard about the phenomenon where LLMs trained for reasoning with RL (Reinforcement Learning) suddenly sound “self-aware”: in the middle of a solution, they stop with “wait… actually…” or “let’s double-check,” make a U-turn, and continue as if they experienced a moment of enlightenment. This phenomenon has been labeled the “Aha moment,” originating from that legendary DeepSeek paper. The question is whether this is truly a change in strategy that increases accuracy, or simply text that creates an impression of thinking.

To this end, the authors use an LLM-as-a-judge that flags whether a moment of pause and strategy shift appears within the model's answer, sometimes accompanied by expressions like “wait… actually…” or “let’s reconsider.” They apply this identification to a large amount of data, more than a million reasoning traces. The test is conducted across several different domains (mathematics, cryptic crosswords, etc.), at various generation temperatures, and across several models and sizes.

As a first step, they check in a very direct way whether the mere existence of a reasoning shift is beneficial at all: they compare P(r|S_{i,j} = 1) to P(r |S_{i,j} = 0), where “r” denotes a correct answer, S_{i,j} = 1 indicates a trace where a change of direction was identified in the middle of the reasoning, and S_{i,j} = 0 indicates a trace without such a change. They find that P(r | S_{i,j} = 1) is lower than P(r | S_{i,j} = 0) in almost every domain, model, and generation temperature tested.

In the next stage, the authors argue that this check is still “too coarse”: not every reasoning shift should be considered an “Aha moment.” Therefore, they propose a more formal and stringent definition for an Aha moment, which attempts to capture a true strategic change. According to the definition, an Aha moment occurs only if three conditions are met simultaneously, controlled by parameters δ1, δ2, δ3:

(1) Consistent past failure: for all previous checkpoints, the probability of success is lower than δ1;

(2) Previous stability: the rate of reasoning shifts in the past is lower than δ2 across all checkpoints;

(3) Performance gain: at the point of change, the accuracy conditioned on the shift is higher than the general accuracy by at least δ3.

In practice, even when the parameter values are lowered, Aha moments remain very rare: once it is required that reasoning shifts not only appear in the text but also yield a measurable improvement, almost no events remain that meet the definition. Later, they check whether the effect depends on context, for example, during the training phase or the generation temperature and here too, no consistent pattern pointing to improvement is revealed: at most, local fluctuations depending on the domain.

The connection to uncertainty comes through measuring the entropy of the answers. Here too, the conclusion does not “save” the idea: stratification by entropy (for example, the top 20% vs. the bottom 80%) does not reveal a region where spontaneous shifts become consistent and beneficial. Even in a state of high uncertainty, “wait… actually…” moments do not systematically translate into improved performance.

Finally, instead of looking for spontaneous insights, the authors “force” the model to rethink. They generate a regular answer (Pass 1) and then run it again with a short addition in the style of “let’s reconsider” (this is Pass 2) under the same generation settings, checking whether this step improves accuracy, especially when the entropy of Pass 1 is high. The conclusion is that this move can indeed help: external and controlled “rethinking” improves accuracy in a measurable way, mainly in examples with high entropy (meaning when the model is uncertain). In other words, the problem is not that reflection (self-criticism) is not beneficial, but that a spontaneous Aha is rare and inconsistent, while an external trigger activated at the right time succeeds in producing real improvement.

The bottom line is that the paper suggests a reframing of the phenomenon: instead of seeing Aha moments as evidence of internal insight or a self-correction mechanism created thanks to reinforcement learning, it is better to treat them primarily as a sign of instability during inference. However, if “rethinking” is turned into an external tool activated intelligently (for example, according to uncertainty metrics), that same instability can be translated into a practical mechanism that improves performance.

https://arxiv.org/abs/2601.00514