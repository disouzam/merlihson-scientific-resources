Review 608: Can AI Replace Developers in Software Engineering Research? Bridging the Gap Between Academia and Industry
Shmulik and Mike’s Daily Paper Review: Review 608 
Can LLMs Replace Manual Annotation of Software Engineering Artifacts?

One of the most frustrating obstacles in software engineering research is the necessity of human labeling to compare different methods. Recruiting professional developers is expensive, the paper notes an average cost of $60 per hour, which often forces researchers to settle for students or skip user experiments entirely.

The paper identifies a troubling gap: while academia remains cautious of AI due to concerns over scientific accuracy, the industry tends to over-rely on AI tools. The authors propose a "Golden Path" - a hybrid workflow that defines exactly when it is safe (and when it is forbidden) to replace human judgment with LLMs.

Experimental Methodology

The researchers tested 6 models (GPT-4, Claude-3.5-Sonnet, Gemini-1.5-Pro, GPT-3.5, Llama3-70B, Mixtral-8x22B) against 10 diverse labeling tasks from 5 SE datasets:

Code Summary Evaluation: Accuracy, conciseness, coherence, and similarity of function summaries.

Variable Name Consistency: Identifying mismatches between a variable's name and its logical value.

Causality Identification: Extracting cause-and-effect relationships from software requirements.

Semantic Similarity: Comparing functions based on goals, actions, and results.

Static Analysis Alert Analysis: Determining whether a bug alert is relevant or a false positive.

To measure reliability, they used Krippendorff's alpha, which evaluates the level of agreement between humans and models while accounting for agreement that might occur by chance.

The Results: Where AI Wins and Where It Fails

The experiments revealed that the answer is not a simple "yes" or "no," but rather "it depends on the task":

Impressive Success in Classification: In variable name consistency tasks, human-to-human agreement was 0.52, while human-to-model agreement was 0.49 - a negligible gap. In semantic similarity, models performed exceptionally well, showing agreement scores of 0.77–0.78 with humans.

Failure in Complex Logic: Models struggled significantly with tasks requiring a broad understanding of code flow. In static analysis alert evaluation, human agreement was 0.80, while human-to-model agreement plummeted to just 0.15.

Examples Matter: The researchers found that "Zero-shot" approaches were insufficient. Providing 3–4 human examples (Few-shot) in the prompt led to significant improvements.

Small Model Bias: Smaller or open-source models (like Llama 3) exhibited "extremity bias" - they tended to choose only the extreme ends of a Likert scale and ignored middle options, damaging the reliability of the rating.

The "Secret Sauce" for Decision Making

The paper proposes two metrics to decide when AI can be trusted:

Model-Model Agreement (MMA): There is a strong correlation between how much different models agree with each other and their accuracy compared to a human. If the alpha score between models is higher than 0.5, one human rater can potentially be replaced by AI.

Output Probability (Confidence Level): Using the probability the model assigns to its own answer allows for filtering. In code summary tasks, replacing a human with AI for the 50% of samples with the highest confidence maintained the same statistical reliability as a purely human study.

Limits of Automation: Can we remove humans entirely?

The researchers tested whether AI could serve as a "sole judge" to replace human majority voting. The findings were clear: except for semantic similarity tasks, there was no cutoff point, even in samples where the model was 100% confident, where the model consistently matched the human consensus. Therefore, AI can replace one evaluator in a group, but it cannot yet replace the entire human "committee."

Operational Recommendations

The paper warns against the total replacement of all human raters in a given sample, as models do not yet consistently represent a full human consensus.

The Recommended Workflow:

Calibration: Perform human labeling for 3–4 samples to create "Few-shot" prompts.

Cross-Model Check: Verify the agreement level between several strong models (GPT-4, Claude, Gemini).

Hybrid Execution: If the agreement is higher than 0.5, replace one human evaluator with AI. If not, use AI only for samples with high output probability.

Bottom Line: This approach makes research that was previously financially impossible both accessible and relevant. By offloading "grunt work" to models, we can reserve the budget for professional developers to handle truly complex cases, ensuring reliable results at a cost that allows research to move forward.

https://arxiv.org/abs/2408.05534