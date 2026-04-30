Review 606: When the Source Is Real but the Content Is Fabricated: What Hallucinations in Language Models Look Like
Mike and Jonathan’s Daily Review: 29.04.26, Review 606
HALLUHARD: TESTING HALLUCINATIONS IN LONG, MULTI-TURN, CITATION-GROUNDED CONVERSATIONS

Okay, friends, today’s review deals with one of the most annoying, stubborn, and challenging problems in language models: hallucinations. Not the simple kind of hallucination where “the model invented a fact in a single question,” but the more dangerous kind: hallucinations that build up over the course of a conversation, rely on seemingly real sources, and continue rolling forward as if they were established facts.

The authors introduce HalluHard, a new benchmark that tries to measure exactly this: how faithful LLMs remain to sources across extended conversations, especially in domains where verifying the truth is difficult.

Not Just One Trivia Question and Done

Most hallucination tests evaluate models in a relatively simple structure: ask a question, receive an answer, and check whether it is correct. But that is not really how people use agents. In practice, users continue asking follow-up questions, request clarifications, go into details, and expect the model to remember what has already been said.

The problem is that if the model made a mistake early in the conversation, that mistake can become a “local fact” inside the context. From that point onward, the model is no longer merely wrong. It is building an entire building on crooked foundations. The benchmark tests exactly this mechanism: how mistakes are created, repeated, and deepened over the course of a full conversation.

What Is Inside the Benchmark?

The idea is not to test models on general knowledge or trivia questions, but on niche, complex, and sometimes difficult-to-verify information. The data includes questions about court rulings, niche academic papers alongside well-known papers with thousands of citations, medical guidelines, and programming tasks such as function calls, imports, and downloading libraries and code packages.

In simple terms: not “Who was the first president of the United States,” but questions where even an average person would need to check a source, read carefully, and avoid guessing confidently.

The evaluation is done along two separate axes:

Reference Grounding: Does the source cited by the model even exist?

Content Grounding: Does that source actually support the claim the model attributes to it?

This distinction is critical, because a model does not need to invent a source in order to hallucinate. Sometimes it does something much more sophisticated and annoying: it cites a real source, and then invents what is written in it.

The More Dangerous Hallucination: Real Source, Wrong Content

This may be the most important result in the paper: models tend to fail more on content grounding than on reference failure. In other words, in many cases they are not inventing an article, court ruling, or medical document from scratch. The source really exists. The problem is that the content the model attributes to the source does not actually appear in it, or is not supported by it.

And this is a more dangerous hallucination, because it looks credible. When a model cites a source that does not exist, it is relatively easy to catch. But when it cites a real source and dresses it up with an incorrect claim, the user gets the impression that there is evidence behind the answer. In practice, what we have is a nice academic costume for a statistical hallucination.

Web Search Does Not Solve the Problem Either

Another important conclusion is that web search tools do not eliminate the problem. Even when the model gets access to search and successfully finds a relevant document, it can still fail to faithfully represent the content of the source. In other words, retrieval is not grounding. The model can reach the correct document, read it partially or incorrectly, and then independently fill in the missing information.

Reasoning Models Help, but Not Enough

The paper finds a certain advantage for reasoning models, but shows that more “thinking” does not necessarily solve the problem. Sometimes longer and more detailed answers simply create more failure points: more claims, more details, more references, and more opportunities to be confidently wrong.

This is an important point, since users tend to believe that a long, reasoned, and well-organized answer is also a more reliable answer. But in practice, sometimes it is just a reasoned hallucination.

Completely Fabricated Information Versus Niche Information

Another experiment in the paper examines the difference between completely fabricated information and niche information. It turns out that models are actually not bad at identifying cases where something does not exist at all. Sometimes they even avoid answering.

But when they detect “residue” of niche knowledge from training, they tend to guess. That is exactly the dangerous zone: not when the model has no idea at all, but when it has a little bit of an idea. Enough to sound convincing, not enough to be correct.

The Bottom Line: Intelligence Has Advanced Faster Than Reliability

The central conclusion of the paper is that the capabilities of language models have advanced faster than their reliability. They can perform complex tasks, produce impressive answers, work across long conversations, and use search tools. But they still struggle with three basic things:

Knowing when they do not know

Reading a source and representing it faithfully

Avoiding speculation when the information is partial

HalluHard shows that the problem is not just information retrieval. The problem is grounding information reliably over time. Or, in simple terms: it is not enough for the model to find a source. It also needs not to invent what is written in it.

https://arxiv.org/abs/2602.01031