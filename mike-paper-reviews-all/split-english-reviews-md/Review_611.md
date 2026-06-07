Review 611: GAIA2 & ARE: In-depth Analysis of Agents in Dynamic & Asynchronous Environments
Daily Paper Review by Shimon and Mike: Review 611
 ARE: Scaling Up Agent Environments and Evaluations

Executive Summary
The GAIA2 paper marks a turning point in the evaluation of AI agents: shifting from static question‑answer tests to dynamic, asynchronous environments where the world keeps moving and doesn’t wait for the agent to act. The main finding shows that even an advanced model like GPT‑5 High achieves only 42% success, leading to a clear conclusion: agents will fail in realistic environments without a robust scaffolding infrastructure.

The current bottleneck is not the model’s raw capabilities, but the harness around it: the tools it uses, the run loop, notification mechanism, memory management and time discipline. All of these are essential to enable it to succeed in a dynamic reality that doesn’t pause for it to think.

2. The ARE Framework – What It Is and Why It Exists
 Before ARE appeared, there were two main types of agent benchmarks, both lacking:

Static question‑and‑answer tests (like GAIA v1 and HumanEval): The agent received a task, nothing changed, the question was fully defined, and the agent had unlimited time to think.

Tool‑use tests (like ToolEval and API‑Bank): Tools existed, but the environment between calls was stateless. There was no ongoing world, no asynchronous events, and no other actors.

Neither reflects the real working environment of a virtual assistant. For example, in a real agent’s inbox, messages accumulate while it thinks; a new message arriving mid‑task changes the entire context. Calendar events change, expire, or get cancelled.

The researchers built ARE: Agents Research Environments, a stateful, event‑driven simulation platform designed to mimic this chaos. Its design principles underpin the paper’s results:

Everything is an event: tool calls, environmental changes, user messages. The system keeps running; it doesn’t freeze waiting for the agent, and everyone lives on the same priority queue.

Applications are stateful: Apps (email, calendar, contacts) maintain current status and produce side effects just like real software.

Time is simulated: The clock advances, allowing complex scenarios that require temporal awareness within a reasonable runtime window.

Events are triggered when their scheduled time arrives, not when the agent checks for them. This throws the agent into a busy environment instead of an orderly dialogue.

3. The GAIA2 Benchmark – Structure, Capabilities and Scoring Method
GAIA2 includes 1,120 scenarios (800 core and 320 extended) spread across 10 “worlds.” Each world represents a user’s digital life: contacts, weeks of calendar history, and prior email threads.

3.1 Capabilities
The capabilities were chosen to isolate weaknesses that classic tests miss. They carry equal weight, underscoring that execution alone isn’t enough:

Execution: Correct sequence of tool actions that change the environment.

Search: Combining information from multiple apps and sources.

Adaptability: Responding to changes occurring after the initial action.

Time: Precise timing, dealing with deadlines and timeouts.

Ambiguity: Identifying tasks that are underspecified or contradictory.

Agent‑to‑Agent: Negotiating with other agents (apps) instead of direct API calls.

Noise: Resilience to environmental disturbances (API errors, distracting emails).

3.2 Action‑Level Scoring
Scoring is based on an LLM judge comparing the actual event stream to the target (oracle) events in each scenario. The judge examines action‑level evidence, not a final natural‑language answer. There’s no way to bluff with a confident summary; you either called send_email with the correct content and recipient or you didn’t.

3.3 Main Data Points

GPT‑5 High: About 42% pass@1 – the current leading model, though it largely fails time‑dependent tasks due to overthinking.

Claude‑4 Sonnet: Lower score than GPT‑5 but offers excellent cost effectiveness.

Kimi‑K2: Around 21% pass@1, the best among open source models.

4. Our Empirical Findings – What We Saw and Why
 We ran seven OpenAI models across five scenarios covering four of GAIA2’s capabilities.

4.1 Taxonomy of Model Failures
Every failure we observed fell into an operational category rather than “lack of understanding” or logic:

Silent no‑op: The model decided no action was needed and did nothing.

Early termination: The model replied with current data and never waited for future events.

Infinite wait loop: The model invoked wait_for_duration repeatedly without checking new inputs.

Frozen‑clock failure: The model replied too quickly, causing the simulated clock to freeze before asynchronous events occurred.

Tool error: Sending wrong data types, rejected by the system.

Stage 2 never reached: The model successfully completed stage one, but the agent loop ended and never reawakened for the second stage.

4.2 Case Study: Universe 21
In scenario universe_21_5e0gvz (adaptability), the agent had to schedule a “movie production day,” email a friend and dynamically reschedule if the friend replied with different availability.

Stage 1: OpenAI o3 did it perfectly, searching contacts, resolving ambiguities, deleting overlapping calendar events, setting the meeting, and sending the email (4 of 4 target actions achieved).

Stage 2: The model did nothing. The simulated clock advanced, the friend’s email arrived, but the agent loop had finished and shut down (0 of 7 target actions achieved).

This illustrates the 42% ceiling: impressive execution in the first stage collapses entirely due to operational harness gaps in the second.

5. The Harness Problem – Why Models Fail
The harness encompasses everything between the LLM and its environment (memory, tool layer, event artery, scheduler). GAIA2 exposes failures in each part:

Tool‑layer failures: Models understand the goal but fail due to strict data type mismatches (solution: schema validation and automatic correction).

Agent loop failures: Models end their loop instead of awaiting environmental triggers (solution: event‑driven re‑awakening).

Notification failures: The agent receives an email but no “push” notification and assumes the task is done (solution: clear notification routing policy).

Time discipline: Models respond too quickly because they can’t recognize they should wait for an unannounced event (solution: planning envelope with predefined waiting strategies).

The remaining failures, true ambiguity detection and cross‑application inference, are the LLM’s real work, but they make up a much smaller portion than the raw 58% gap suggests.

6. Practical Implications for Production Systems
 For anyone building agents in dynamic environments, GAIA2 provides a clear insight: improve the harness before rushing to upgrade the model.

Build the loop before the model: tasks must have persistent state and reawakening points. The agent should run because something happened in the environment, not just because a user typed something.

Design the notification surface: wrong notification routing choices cause silent failures. Decide in advance what to push, what to summarize and what to ignore.

Make time a first‑class citizen: provide the model with the current time, awareness of deadlines and explicit polling patterns.

Action‑level verification: treat the model’s verbal confirmation as low‑trust; treat actual API calls as high‑trust.

A well‑built harness around GPT‑4‑level models will consistently outperform a poor harness around GPT‑5‑level models in asynchronous tasks. ARE’s methodology, reproducible and verifiable simulation, is exactly how real development and engineering processes should measure progress.

https://arxiv.org/abs/2602.11964.