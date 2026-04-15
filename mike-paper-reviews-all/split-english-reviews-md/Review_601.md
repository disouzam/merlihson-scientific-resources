Review 601: Anthropic’s Revolution on Trial: Do Skills Actually Help Your Agents?
Shmulik and Mike’s Daily Article: April 15, 2026 | Review 602 (423 of 1024) SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks

A few months ago, when Anthropic introduced the Agent Skills protocol, the market was buzzing. The idea was enticingly simple: instead of building a complex agent from scratch for every task, you simply "equip" it with sets of pre-made capabilities (Skills). These are modular packages of procedural knowledge consisting of instructions, scripts, and examples.

But then came the million-dollar question: Do these Skills actually improve performance, or are they just "noise" cluttering the context window? Don't Frontier models already know how to perform these tasks on their own? The SkillsBench paper brings order to the chaos, testing this systematically and scientifically.

What Exactly is a Skill?

The paper defines a Skill as a modular functional unit designed to guide the agent on the "how" of task execution. Unlike RAG (which provides facts) or tool documentation, a Skill focuses on procedure.

It consists of three core components:

Work Instructions (SKILL.md): A natural language file detailing the methodology, execution steps, and professional conventions.

Execution Resources: Code files, scripts, or templates the agent can actually run to streamline the path to a solution.

Examples: Proven usage patterns showing the agent what a successful task execution looks like.

The study focuses on portable skills (collected from GitHub or Smithery.ai) designed to work with any agent or model on the market.

Methodology: How Do You Benchmark Skills?

To truly measure the impact of Skills, researchers developed a benchmark based on three stages:

Skill Collection: Researchers sampled 47,150 unique skills from the web and commercial companies.

Building the Test: 84 tasks across 11 different domains. Each task runs in an isolated Docker container (using the Harbor infrastructure), ensuring deterministic verification via Pytest. Every task has an "Oracle" (a perfect solution) proving it is indeed solvable.

Strict Quality Filtering: Only 26.7% of the proposed tasks were accepted. Filtering included AI Detection (to ensure instructions were human-written), a Leakage Audit (to ensure the skill doesn't "leak" the specific solution), and data realism.

Experimental Results: Who Actually Needs Skills?

Researchers performed 7,308 runs across 7 model and agent configurations (such as Claude Code or Gemini CLI).

The Good: Skills Work (Where They are Actually Needed)

Average Improvement: High-quality human skills increased success rates by an average of 16.2%.

Victory for Niche Domains: The biggest improvements were recorded in Healthcare (+51.9pp) and Manufacturing (+41.9pp).

The Software Gap: In Software Engineering, the improvement was negligible (<4.5%). Models already know how to code and saw plenty of relevant data during training, so skills added only minor value.

The Bad: Models Can't Help Themselves

Self-Generation Failure: When models were asked to generate their own skills, performance dropped by 1.3%. They simply don't know how to define the rules they need to succeed.

Cognitive Load: Using four or more skills dropped the improvement to just 5.9pp (compared to ~18pp with 2-3 skills). Too many instructions create confusion and "noise."

Over-Documentation: "Comprehensive" skills actually hurt performance by 2.9pp. Conclusion: An agent needs a checklist, not an encyclopedia.

The Surprising: David vs. Goliath and Economic Efficiency

Haiku > Opus: A small model like Claude Haiku 4.5 with skills (27.7%) outperformed Claude Opus 4.5 without skills (22.0%). A good skill can compensate for a weaker model in specific tasks.

Gemini 3 Flash is the Value King: Although it consumes 2.3x more tokens (it explores more rather than thinking deeply), it remains about 47% cheaper per task thanks to its low pricing.

Failure Analysis: Where Does it Break?

Researchers analyzed 5,171 failure cases and discovered a fascinating picture of the "glass ceiling" for agents:

Quality Over Structure: The most common failure (49.8%) was quality below the defined threshold. The agents understood the task and produced the correct output structure, but the result simply wasn't accurate enough.

Over-Exertion: The Timeout rate rose from 16.1% to 18.6% when skills were added. Why? Instead of "giving up" and producing trash output quickly, the skills caused the agents to try harder and explore solutions more deeply until time ran out.

Partial Solutions (10.2%): The agent managed to solve parts of the task but left critical (usually the most complex) components unaddressed.

When Does It Fail?

Clash with Prior Knowledge: In 16 tasks, skills actually decreased performance. This happened in tasks where models are already strong; there, the skill added unnecessary noise and complexity.

Self-Generation Failure: Models fail at writing skills for themselves because they generate overly general instructions (like "use Pandas") without specific code templates, or they fail to recognize that specific niche knowledge (e.g., manufacturing or finance) is required and try to solve the problem generically.

Summary and Conclusions

The paper proves that Agent Skills are not a universal "magic pill" but rather a tool dependent on context and quality. The central finding is that a high-quality skill can be a substitute for Scale, allowing small models to beat giants in specific tasks.

Shmulik’s Insights:

The Software Gap: It’s fascinating that the improvement in software was the smallest (+4.5pp). This suggests that the real edge for Skills today is in areas where AI is still "young" and lacks procedural knowledge from training, like Medicine or Industrial Manufacturing.

Procedure vs. New Knowledge: The paper focused mainly on workflows. My caveat is that the Skills protocol is much more flexible, it can be our way of providing the agent with tools and libraries created yesterday (like a new CLI you wrote that the model has never heard of).

Human Importance (and ROI): Models cannot generate effective skills for themselves (a 1.3pp average drop). Our role is changing, we are becoming the architects for our models. The investment in writing a high-quality skill (scoring 10.1/12 in the study vs. a community average of 6.2/12) is what enables the performance leap.

Don't Add a Skill "Because You Can": One of the important innovations in the paper is the precise comparison between tasks with and without skills. We saw that performance in 16 out of 84 tasks was harmed by adding skills. Often, people create trivial skills for things the model already knows how to do, which only adds noise.

The Bottom Line: Don’t just throw skills at your agent because it’s trendy. Before adding a skill, do a small test to see if your model actually needs it. Invest in high-quality, human-written, focused instructions (2-3 skills per task) rather than generic web scrapings, and you’ll see how even small, cheap models can perform like the giants.

https://arxiv.org/abs/2602.12670