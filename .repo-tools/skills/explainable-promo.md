---
name: explainable-promo
description: Write inspiring, clickbait-style Hebrew promo posts for the explAInable podcast (a Hebrew AI/high-tech interview podcast), tailored separately for Facebook, X/Twitter, and LinkedIn, promoting a reel/episode. Use when the user asks to "write explAInable posts" / "promo posts for a reel" and gives a guest + topic.
---

# explAInable Podcast Promo Posts

Write energetic, clickbait **Hebrew** social posts that promote an explAInable
episode/reel. Produce **three tailored posts** — Facebook, X/Twitter, LinkedIn —
all in Hebrew (RTL). The podcast brand is **explAInable** (written "Explainable"
inside Hebrew text, as the brand does).

## Ask the user for these (at invocation)

1. **Guest** — full name + **LinkedIn profile URL**.
2. **Topic + the juicy hooks** — the surprising story / "wow" moment, the twist or
   conflict, and **concrete numbers** (downloads, training runs, costs, dates).
   The specifics ARE the clickbait — push for them if the user is vague.
3. **The reel** — the short clip being promoted (link/file), for context.
4. **Full-episode links** — YouTube + Spotify URLs (used in the call-to-action).

Read the guest's LinkedIn (WebFetch) to frame them credibly. On **LinkedIn**,
@-mention the guest.

## Voice & style (match these — drawn from real posts)

- Casual, high-energy Hebrew. Slang encouraged: "שבר דיסטנס", "זינקו לשמיים",
  "בלי פילטרים", "שימו אוזן", "הייאוש כבר חגג".
- **Open with a punchy, emotive hook line** — a surprising/relatable claim.
  e.g. `לפעמים הפריצות הכי גדולות בהייטק קורות לגמרי בטעות 😂`
- **Lead with a specific surprising story + concrete numbers** (e.g. "כמעט 200
  ניסיונות אימון", "30,000 הורדות בשבוע", "ממאות אלפי דולרים לעשרות אלפים").
  Specificity is what makes it clickbait, not adjectives.
- Name the guest / company and **Explainable** (the show).
- Emojis — sparing but punchy: 😂 🚀 👇 🎧.
- **No hashtags** (the brand's posts don't use them).
- **CTA** points to the full episode:
  `שימו אוזן, הלינק מחכה לכם ממש פה בתגובות! 👇🎧` + the YouTube + Spotify links.

## Per-platform shaping

- **X/Twitter** — short and tight. A teasing question hook
  (`רוצים לדעת איך…?`) → `תאזינו לפרק המלא כדי לגלות:` → YouTube + Spotify links.
- **Facebook** — the full story version: hook line, the surprising anecdote with
  the numbers, 2-3 lines on what the episode covers, then CTA + both links.
  Blank line between paragraphs.
- **LinkedIn** — like Facebook but a touch more polished; **@-tag the guest**;
  same story + CTA.

## Fixed assets (the podcast's own pages — for reference / CTA fallback)

- YouTube: https://www.youtube.com/@explainable-podcast/videos
- Spotify show: https://open.spotify.com/show/54gAppYYCFoKNP2GqL6coF
- LinkedIn company page id: 110133905

Use the **per-episode** YouTube + Spotify links the user provides for the CTA, not
these show-level links.

## Output

Save the three posts **in the same folder as the reel**, named after the reel file:
- `<reel_dir>/<reel_basename>_facebook.txt`
- `<reel_dir>/<reel_basename>_twitter.txt`
- `<reel_dir>/<reel_basename>_linkedin.txt`

Hebrew, UTF-8. Also print each post in chat in a copy-paste-ready block, labeled
**Facebook / X / LinkedIn**. No hashtags.

## Batch mode

The user often hands over **several reels at once**. Process each reel
independently and save its three posts **beside that reel** (same folder, named
after the reel). After the batch, give a one-line summary per reel (guest + the
folder/files written). Print the full posts for the first reel as a sample, and
the rest on request.

## Reference example (the "Nimotron / Hebatron" episode — match this register)

> לפעמים הפריצות הכי גדולות בהייטק קורות לגמרי בטעות 😂
> צוות הפיתוח של מודל השפה בעברית "נימטרון" הגיע אלינו ל-Explainable ושבר דיסטנס
> על מה שבאמת קורה מאחורי הקלעים של פרויקט AI שמגיע ל-30,000 הורדות בשבוע אחד.
> מתברר שאחרי כמעט 200 ניסיונות אימון … מישהו פשוט שכח את המכונה דולקת למשך הלילה.
> בבוקר הביצועים זינקו לשמיים! 🚀 … שימו אוזן, הלינק מחכה לכם ממש פה בתגובות! 👇🎧
