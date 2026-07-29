# CL Content Tracker — Implementation Plan

**Derived from:** `AI-Lab-Content-Playbook.md` v0.6 (strategy). This is the **buildable MVP spec**.
**Purpose:** trace relevant **content** and **people** on continual learning & adjacent topics; deliver a ranked digest; optionally draft **2 short technical posts/week** (human-approved, non-AI-looking).
**Version:** impl-v1.0 (finalized) · 2026-07-30 · all four build decisions resolved (§10); ready for Phase 1.

---

## 0. Scope

**In (MVP):**
1. **Listener** — pull CL & adjacent content from research/forum sources on a schedule.
2. **Scorer** — rank items by technical depth + velocity + freshness + topic fit; dedupe.
3. **People tracker** — discover & rank the researchers who own these topics; map to handles.
4. **Digest** — one ranked output (topics + posts + people + "our angle") delivered on a cadence.
5. **Drafter (optional, toggle)** — for the top 2 topics/week, draft a short technical post + run the rigor/anti-slop gate → human approval queue. **Nothing auto-posts.**

**Out (later):** brand/CEO dual-account orchestration, LinkedIn/X auto-posting, carousels (F7), video (F8), full autonomy, scheduler-to-platform. The drafter *produces* drafts; a human posts them by hand in MVP.

**Hard constraint (data access):**
- ✅ Fully buildable & free: **arXiv, OpenReview, Semantic Scholar, Hacker News, Reddit, GitHub, Papers-with-Code**, plus **curated technical news/blog RSS** (topic-gated only — highly technical & related, never general AI news/drama).
- ⚠️ **X (Twitter):** search needs paid API (Basic ~$200/mo) *or* curated public lists ingested manually. Add in Phase 2.
- ❌ **LinkedIn:** no legitimate post-search API; scraping is ToS-breaking + fragile. Treat as **listen-only via echoes** — a topic hot on LinkedIn will surface through the other sources anyway.

---

## 1. Topic definition (the CL taxonomy) — `config/topics.yaml`

The single most important config. Two layers:

- **Core keywords/phrases:** continual learning, catastrophic forgetting, lifelong learning, online/streaming learning, plasticity–stability, loss of plasticity, dormant neurons, effective rank collapse, replay/rehearsal, EWC, synaptic intelligence, LwF, continual pre-training, warm-starting / primacy bias, task-free CL, class-incremental.
- **Adjacent (weighted lower):** PEFT/LoRA fine-tuning dynamics, distillation, feature geometry / representation collapse, superposition, SSM/Mamba memory, MoE, data mixture, eval contamination.
- **Emerging / early (catch these *before* they have a name):** the point is to surface nascent CL-adjacent directions early, not just track the canon. Don't require an exact keyword match — flag items that are **semantically near the profile but use unfamiliar terms**, are **low-citation but from a tracked/rising author (§5)**, or open a **new problem framing** around memory, adaptation, non-stationarity, test-time/continual adaptation, model editing, knowledge injection, or "models that keep learning after deployment." First good take on an emerging thread wins (§4 freshness). Keep an **`emerging` bucket** in the digest for these, explicitly lower-confidence.
- **Semantic filter:** an **interest-profile embedding** (seed from ~30 CL papers the team rates) — score each item by cosine similarity to the profile, not just keyword hits, so **near-but-unnamed** work still surfaces. *(Reuse the `paper_recommender` cached-interest-profile pattern.)* Keep the similarity threshold deliberately loose for the `emerging` bucket; tight for the core digest.

---

## 2. Architecture

```
 sources ──▶ Listener ──▶ normalized item store (jsonl/sqlite)
                              │
                              ▼
                          Scorer (§4)  ──▶ ranked topics + posts
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼                ▼
        People tracker    Digest builder   Drafter (optional)
        (§5)              (§6)             (§7) ──▶ Rigor gate ──▶ approval queue
```

Single Python package, scheduled via launchd/cron (reuse the `news_scout` runner + `last_run.txt` ledger pattern). One config dir, one output dir.

---

## 3. Listener — `listener/`

Per source, a small fetcher returning normalized items `{id, source, url, title, text, authors[], ts, raw_metrics}`:

| Source | Access | Notes |
|--------|--------|-------|
| arXiv | free API | cs.LG, cs.CL, cs.CV new listings; **backbone** |
| OpenReview | API | CL-heavy venues, CoLLAs, workshops |
| Semantic Scholar | API | topic + author search, citations → **people engine** |
| Hacker News | Algolia API (free) | velocity signal |
| Reddit | JSON API | r/MachineLearning, r/LocalLLaMA |
| GitHub | API/trending | new CL repos/tools |
| Papers-with-Code | API/scrape | trending in topic |
| **Technical blogs/newsletters** | RSS | **curated, topic-gated** — see §3.1. Only items passing the topic gate; **no general AI news/drama** |
| X (Phase 2) | paid API **or** curated list | recent-search on topic + tracked handles |

### 3.1 Curated blogs & newsletters (topic-gated RSS) — `config/feeds.yaml`

Known, high-signal sources that regularly write on CL & adjacent topics. Each has an RSS/Atom feed (Substacks and most lab blogs do; a few need a fetch-and-parse fallback). Ingest → run every item through the §1 topic gate → keep only what clears it. Tiered by relevance; each feed carries a `tier_weight` the scorer uses.

**Tier 1 — CL-specific / directly relevant**
- **ContinualAI** — continualai.org (the CL community; the single most on-topic source)
- **Rich Sutton / Dohare — "Loss of plasticity"** — incompleteideas.net (continual learning & plasticity, foundational)
- **Sebastian Ruder** — ruder.io + *NLP News* (transfer / multitask / continual)
- **BAIR blog** — bair.berkeley.edu/blog (frequent lifelong/continual work)
- **Stanford SAIL** — ai.stanford.edu/blog
- **Off the Convex Path** — offconvex.org (optimization & learning dynamics, plasticity)
- **The Gradient** — thegradient.pub
- **Apple ML Research** — machinelearning.apple.com (on-device / continual adaptation)

**Tier 2 — mechanism / architecture / representations / interp**
- **Lil'Log** — lilianweng.github.io (learning dynamics, representations)
- **Transformer Circuits** — transformer-circuits.pub · **Chris Olah** — colah.github.io · **Neel Nanda** — neelnanda.io (interp / what models encode)
- **Gradient Science** — gradientscience.org (MIT Madry lab; data & representations)
- **Jay Alammar** — jalammar.github.io (illustrated architectures)
- **Maarten Grootendorst** — newsletter.maartengrootendorst.com (visual guides; F9 carousel model)
- **Cameron Wolfe — Deep (Learning) Focus** — cameronrwolfe.substack.com
- **Sebastian Raschka — Ahead of AI** — magazine.sebastianraschka.com

**Tier 3 — fine-tuning / practical training / evals**
- **Hugging Face blog** — huggingface.co/blog (PEFT, training, often deeply technical)
- **Answer.AI** — answer.ai/posts (efficient fine-tuning / training)
- **Chip Huyen** — huyenchip.com · **Eugene Yan** — eugeneyan.com · **Hamel Husain** — hamel.dev (applied fine-tuning, evals, systems)

**Tier 4 — curation layers (let others pre-filter)**
- **Davis Summarizes Papers** (Davis Blalock) — high-signal weekly ML-paper summaries
- **Interconnects** (Nathan Lambert) · **Import AI** (Jack Clark) · **The Batch** (DeepLearning.AI)
- **Simon Willison** — simonwillison.net · **TLDR AI** · **Papers-with-Code newsletter** · **Deep Learning Weekly**

**Tier 5 — lab research blogs (release-triggered, topic-gated)**
- **Google Research** · **DeepMind** · **Meta AI / FAIR** · **Microsoft Research** · **Allen AI (AI2)** · **OpenAI** · **Anthropic** · **NVIDIA Research** — often first to post continual-pretraining / adaptation / architecture work.

**Trending-paper aggregators (feed the `emerging`/`viral` buckets):** **Hugging Face Daily Papers** (huggingface.co/papers — has an API), **alphaXiv**, **arXiv-sanity**. *(Podcast/YouTube transcript mining — MLST, Dwarkesh, Latent Space — stays in the playbook's Phase-2 all-media scope, not MVP.)*

*Start with this set; the §10 feedback loop prunes feeds that never clear the topic gate and promotes new ones the team keeps forwarding (via the internal reading feed).*

Dedup on normalized title + URL. Respect each API's rate limits; cache raw responses.

---

## 4. Scorer — `scorer/`

**Two tracks, scored separately:**
- **Track A — CL relevance (depth-first):** the topic-filtered pipeline below. The backbone.
- **Track B — viral-but-weakly-related:** surface items **going viral right now that are only *loosely* connected to the CL taxonomy** — a **weak topic gate**, not topic-agnostic. Scored on **velocity + cross-source spread + amplifier involvement**, gated by a **low similarity threshold** to the interest profile (§1): it must brush the topics (memory, adaptation, forgetting, fine-tuning, representations, architectures…), just not squarely. This is the reactive-add lane (Pillar 4/F5) without drifting into unrelated AI drama. Cap it (e.g. top 3–5/run) so it never drowns the CL core; tag each with a **defensibility + stealth-safety flag** (§6). Skip pure news/legal/safety-incident items even when viral.

### Track A scoring — weighted per item (research-first — depth over noise):

- **Technical depth / substance** *(top weight)* — real mechanism/result/method vs. announcement. Signals: is it a paper? has results/figures? code? Down-weight pure news.
- **Topic fit** — embedding similarity to the CL interest profile (§1).
- **Velocity** — reactions/hr relative to the source's baseline. *(High, never dominant alone.)*
- **Cross-source spread** — same topic in ≥2 sources = "about to be everywhere."
- **Amplifier involvement** — is a tracked researcher (§5) engaging/authoring it?
- **Freshness / early-signal** — room to say something non-obvious before saturation; **boost nascent items** (near the profile but unnamed, low-citation from a rising author, new problem framing) so early/emerging topics aren't buried by high-velocity established ones. These land in the digest's `emerging` bucket.

**Cross-source synthesis pass** (playbook §7.4): after scoring, look for contradictions / cross-domain echoes / under-read implications across the top items + recent archive. Each synthesis carries its 2+ source anchors → these are the best "our angle" candidates.

Output: ranked shortlist, each with score breakdown + a one-line **"our angle"** + source anchor(s).

---

## 5. People tracker — `people/`

Fully buildable, legit, and high-value:

1. From CL papers (arXiv + Semantic Scholar + OpenReview), extract **recurring authors**.
2. Rank by: # CL-topic papers × recency, citation weight, and cross-venue presence.
3. Maintain `people/roster.yaml` — ranked researchers with a **handle map** (X/LinkedIn) filled semi-manually and extended over time (there's no clean API from name→handle).
4. Flag **rising names** (new author appearing across multiple recent CL papers) and **amplifiers** (already-tracked people engaging a hot item) — both feed the scorer's "amplifier involvement" signal.

5. **Viral-but-related people (Track B):** flag accounts going viral *right now* on something **loosely** touching the topics (same weak gate as §4 Track B) — "who's everyone quoting today, in our orbit." Not added to the CL roster; they surface in the digest's `viral` bucket as reactive-engagement candidates.

Output: a living ranked people list + weekly "new names to consider following."

---

## 6. Digest builder — `digest/`

One artifact per run, in three buckets:
- **`core`** — CL-relevant, depth-first (Track A): ranked topics with angle + anchors + platform-lean hint, top posts/papers.
- **`emerging`** — near-but-unnamed / early CL-adjacent threads (§1), explicitly lower-confidence.
- **`viral`** — going viral *and* weakly topic-related (Track B): capped, each with a defensibility + stealth-safety flag.

Plus **people highlights** — rising CL names + viral-but-related accounts (who's engaging what). Delivered as:
- a **Markdown file** in the output dir (always),
- **Telegram** message (reuse existing uploader pattern), and
- **Email** (reuse the `email_digest` sender) — the same digest, formatted for inbox reading.

---

## 7. Drafter (optional toggle) — `drafter/`

For the top 2 topics/week, produce a **short technical post** (X-native: 1 post or a 3–4 post thread; ≤ ~280 chars/post). Toggle in config; off = digest-only.

**System prompt =** playbook §2 (voice) + §2.1a (deeply-technical-plainly-said rules) + §11 as few-shot examples. Drafts must be **technical but not AI-looking** — the hard constraint. Concrete anti-slop rules baked into the prompt *and* checked post-hoc:

- **Plain claim first, precision second.** One idea, one mechanism, one real detail (a number, a named failure mode).
- **Ban list (auto-reject if present):** "delve", "it's important to note", "in the ever-evolving/rapidly-evolving landscape", "game-changer", "unlock", "leverage" (as verb-filler), "🚀/🧵 + 'let me explain'", em-dash-itis, listicle-as-post, "Agree? 👇".
- **No hedging into mush; no hype adjectives; ≤1 hashtag (prefer zero); no link in the first post.**
- **Every load-bearing term glossed in ~4 words.**

Then the **rigor gate** (playbook §9) before the human queue:
1. Extract the core claim (no claim → kill).
2. Anchor it to the exact public source (paper §/figure, repo, post).
3. **Adversarial refute pass** — a separate LLM step tries to prove it wrong; survives → queued *with* refutation notes; fails → auto-killed with reason.
4. Anti-slop + gloss check (above).
5. **§6 moat check** — reject anything drifting toward the lab's own method/results/domain.

Output: 0–2 approved-pending drafts/week in the queue (Telegram/file). Human edits/approves; human posts manually.

---

## 8. Tech & reuse

- **Language:** Python 3.12. **LLM:** Claude (Anthropic key) for scoring-assist, synthesis, drafting, refute pass.
- **Reuse from `scientific-resources` — directly, in place.** It lives in **your** repo under `.repo-tools/scripts/cl_tracker/` and reuses the existing machinery: `news_scout` (fetch→rank→format→Telegram + `last_run.txt` ledger + launchd runner), `paper_recommender` (arXiv + cached interest-profile scoring), `email_digest` (email sender). No copy/fork — import/extend what's there. *(Your repo, results-only deliverable; no stealth/IP separation needed.)*
- **Storage:** sqlite or jsonl item store + yaml configs. **Scheduling:** launchd/cron, same wake-catchup safety pattern.
- **Delivery:** Markdown digest + Telegram + Email (reuse `email_digest` sender).

---

## 9. Phased milestones

- **Phase 1 — Listen + score + digest (research/forum sources).** arXiv + OpenReview + Semantic Scholar + HN + Reddit + GitHub → scorer → ranked Markdown/Telegram digest. *This alone delivers the core value: relevant content, ranked.*
- **Phase 2 — People tracker.** Author extraction → ranked roster + handle map + rising-names flag.
- **Phase 3 — Synthesis pass.** Cross-source angle generation on top items.
- **Phase 4 — Drafter + rigor gate (optional toggle).** 2 short technical drafts/week → approval queue.
- **Phase 5 — X source (if API/lists available).**

Each phase ships independently; MVP "done" = Phases 1–2 (+3), with 4 as the toggle.

---

## 10. Decisions (resolved)

1. ✅ **Delivery** — Markdown file + **Telegram + Email**.
2. ✅ **Drafter** — **ship listen+people first** (Phases 1–3); drafter (Phase 4) is a follow-up.
3. ✅ **X access** — **research-first, skip X for now**; add **curated technical news/blog RSS** (topic-gated, highly technical & related only — no general AI news/drama).
4. ✅ **Repo location** — **your `scientific-resources` repo**, under `.repo-tools/scripts/cl_tracker/`, reusing the existing runners in place. It's your repo and the deliverable is *results*, not code — no stealth/IP separation needed. It will need its own config (Telegram channel, email target, API keys, `last_run.txt`) so it runs independently of your personal review pipeline. Post language = **English** (assumed).
