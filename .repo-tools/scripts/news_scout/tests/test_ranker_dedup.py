# -*- coding: utf-8 -*-
"""Dedup tests for the news_scout ranker.

Locks in the concrete cases surfaced by adversarial review: version-token
preservation, the false-merge pairs that must NOT collapse, the genuine
duplicate cluster that MUST collapse, and the two-layer (slug + lexical)
non-destructive selection in _dedupe_by_story.
"""
from news_scout.ranker import (
    _distinctive_tokens,
    _same_story,
    _dedupe_by_story,
    RankedItem,
)
from news_scout.fetcher import NewsItem


def _item(title: str) -> NewsItem:
    return NewsItem(
        title=title,
        url=f"http://x/{abs(hash(title)) % 999999}",
        source="test",
        summary="",
        published="",
    )


def _ranked(title: str, score: int, story: str = "") -> RankedItem:
    return RankedItem(item=_item(title), score=score, reason="", story=story)


# ---------- tokenization ----------

def test_version_identifiers_preserved():
    toks = _distinctive_tokens("OpenAI ships GPT-5.6 to enterprise")
    assert "gpt-5.6" in toks          # kept whole
    assert "gpt" not in toks          # not shredded to bare "gpt"


def test_pure_number_tokens_dropped():
    toks = _distinctive_tokens("Amazon cuts 14,000 corporate jobs")
    assert "000" not in toks and "14" not in toks   # kills the 14,000 -> 000 bug


# ---------- FALSE MERGE: different stories must NOT collapse ----------

FALSE_MERGE_PAIRS = [
    ("Musk sues OpenAI over nonprofit shift",
     "Musk sues California over data-privacy law"),
    ("Amazon cuts 14,000 corporate jobs in restructuring",
     "IBM cuts jobs as AI takes over support roles"),
    ("Nvidia chips smuggled into China despite ban",
     "AMD chips approved for sale in China"),
    ("Grok goes rogue with antisemitic posts",
     "Grok goes offline across Europe"),
    ("OpenAI unveils Sora",
     "Sora Ventures raises $200M for crypto fund"),
    ("OpenAI launches GPT-5.6",
     "OpenAI shuts down its Atlas browser"),
]


def test_no_false_merges():
    for a, b in FALSE_MERGE_PAIRS:
        assert not _same_story(a, b), f"FALSE MERGE: {a!r} vs {b!r}"


def test_distinct_versions_not_merged():
    assert not _same_story("OpenAI releases GPT-5.6", "OpenAI releases GPT-4.1")


# ---------- MISSED DUP: the real cluster MUST collapse ----------

FIDJI_CLUSTER = [
    "OpenAI exec Fidji Simo says she's stepping down due to chronic illness",
    "Fidji Simo steps down from OpenAI's no. 2 role",
    "OpenAI's AGI deployment chief Fidji Simo to step down after a year",
    "OpenAI's CEO of AGI Deployment, Fidji Simo, Is Stepping Down",
]


def test_fidji_cluster_all_merge():
    for other in FIDJI_CLUSTER[1:]:
        assert _same_story(FIDJI_CLUSTER[0], other), f"MISSED DUP: {other!r}"


# ---------- _dedupe_by_story: two-layer, non-destructive ----------

def test_slug_collapse_keeps_highest_scored():
    ranked = [
        _ranked("Chip export controls tighten again", 90, story="chip-export-controls"),
        _ranked("Fidji Simo out — first outlet's take", 80, story="fidji-departure"),
        _ranked("Fidji Simo leaving, second outlet's angle", 70, story="fidji-departure"),
        _ranked("Anthropic closes a giant funding round", 60, story="anthropic-funding"),
    ]
    out = _dedupe_by_story(ranked, top_n=7)
    assert [r.score for r in out] == [90, 80, 60]   # the two fidji items -> one (the 80)


def test_lexical_backstop_when_model_forgot_to_group():
    # Same event, but the model returned empty slugs -> the title backstop must catch it.
    ranked = [
        _ranked("Fidji Simo steps down from OpenAI's no. 2 role", 90, story=""),
        _ranked("OpenAI's AGI chief Fidji Simo to step down", 85, story=""),
        _ranked("Meta puts its own AI chip into production", 70, story=""),
    ]
    out = _dedupe_by_story(ranked, top_n=7)
    assert len(out) == 2                             # two fidji collapse via backstop


def test_distinct_stories_are_all_kept():
    titles = [
        "Nvidia hits a five trillion dollar valuation",
        "Meta puts its AI chip into production",
        "Anthropic closes a giant funding round",
        "Instagram image generator alarms privacy experts",
        "SpaceX wealth fuels private-jet demand",
    ]
    ranked = [_ranked(t, 90 - i, story=f"s{i}") for i, t in enumerate(titles)]
    out = _dedupe_by_story(ranked, top_n=7)
    assert len(out) == len(titles)                  # nothing wrongly merged


def test_top_n_is_respected():
    titles = [
        "Nvidia hits five trillion valuation",
        "Meta AI chip enters production",
        "Anthropic closes giant funding round",
        "Instagram generator alarms privacy experts",
        "SpaceX wealth fuels private-jet demand",
        "Google DeepMind unveils weather forecaster",
        "Apple delays its smart-home display",
        "Amazon warehouse robots pass a milestone",
    ]
    ranked = [_ranked(t, 90 - i, story=f"s{i}") for i, t in enumerate(titles)]
    out = _dedupe_by_story(ranked, top_n=7)
    assert len(out) == 7


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
