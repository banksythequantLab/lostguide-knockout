"""
Nimble TESS Knockout Agent — mobile-app trademark niche.

Orchestrates a multi-source trademark conflict search using Nimble's web data APIs:
  - USPTO TESS (federal trademark database)
  - Apple App Store
  - Google Play Store
  - GitHub repositories
  - Product Hunt
  - General Google web search

Falls back to a deterministic stub when NIMBLE_API_KEY is not set, so the file://
demo works without credentials. Replace stub with real Nimble calls once Derek's
hackathon API key is in environment.

Build target: DeveloperWeek New York 2026 Hackathon — Nimble "Agentic App That Sees
the Live Web" sponsor challenge.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import difflib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional

# --- Optional real Nimble client (only if installed + key present) -----------

_NIMBLE_CLIENT = None
_HAS_NIMBLE = False
try:
    if os.environ.get("NIMBLE_API_KEY"):
        from nimble_python import Nimble  # type: ignore
        _NIMBLE_CLIENT = Nimble(api_key=os.environ["NIMBLE_API_KEY"])
        _HAS_NIMBLE = True
except Exception:  # pragma: no cover — SDK not installed or env issue
    _NIMBLE_CLIENT = None
    _HAS_NIMBLE = False


# --- Data model --------------------------------------------------------------

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "VERY_HIGH")
RECOMMENDATIONS = ("PROCEED", "PROCEED_WITH_AMENDMENT", "DO_NOT_PROCEED")


@dataclass
class Conflict:
    source: str                  # 'uspto-tess' | 'app-store' | 'play-store' | 'github' | 'product-hunt' | 'web'
    mark: str
    holder: str = ""
    class_or_category: str = ""
    similarity: float = 0.0      # 0-1
    risk: str = "LOW"
    url: str = ""
    notes: str = ""


@dataclass
class KnockoutReport:
    mark: str
    classes: list[int]
    niche: str
    searched_at: str
    sources_searched: list[str]
    conflicts: list[Conflict]
    risk_score: str = "LOW"
    recommendation: str = "PROCEED"
    narrative: str = ""
    stub: bool = True
    nimble_calls_made: int = 0


# --- Niche configuration -----------------------------------------------------

NICHE_SOURCES: dict[str, list[str]] = {
    "mobile-app":     ["uspto-tess", "app-store", "play-store", "github", "product-hunt", "web"],
    "amazon-fba":     ["uspto-tess", "amazon", "trademarkia", "web"],
    "podcast":        ["uspto-tess", "apple-podcasts", "spotify", "youtube", "patreon", "web"],
    "cannabis-ny":    ["uspto-tess", "nys-trademark", "leafly", "web"],
    "generic":        ["uspto-tess", "web"],
}

NICHE_DEFAULT_CLASSES: dict[str, list[int]] = {
    "mobile-app":  [9, 42, 41],
    "amazon-fba":  [25, 21, 30, 8],
    "podcast":     [9, 41],
    "cannabis-ny": [5, 30, 34],
    "generic":     [],
}


# --- Similarity scoring ------------------------------------------------------

def similarity(a: str, b: str) -> float:
    """Crude phonetic-ish similarity 0-1. Real version would call USPTO sound-alike rules."""
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def mark_match(mark: str, *texts: str) -> float:
    """Containment-aware match score (0-1) for live web results.

    Live web search returns article titles and pages *about* a term, not bare brand
    names, so a whole-string SequenceMatcher ratio (fine for registry-vs-mark) badly
    underscores a title like 'Laugh Now, Banksy! - EUIPO ...'. Here we score how
    strongly the mark (and its dominant tokens) appear inside the result text, and
    fall back to the raw ratio.
    """
    m = (mark or "").lower().strip()
    if not m:
        return 0.0
    best = 0.0
    m_tokens = [t for t in re.split(r"\W+", m) if len(t) >= 3]
    for text in texts:
        t = (text or "").lower()
        if not t:
            continue
        if m in t:                                  # full mark appears verbatim
            best = max(best, 0.97)
            continue
        if m_tokens:                                # dominant-token containment
            hits = sum(1 for tok in m_tokens if re.search(rf"\b{re.escape(tok)}\b", t))
            if hits:
                best = max(best, 0.60 + 0.30 * (hits / len(m_tokens)))
        best = max(best, similarity(m, t))          # raw-ratio fallback
    return min(best, 1.0)


def grade_risk(sim: float, source: str, same_class: bool) -> str:
    """Risk grading: source weight × similarity × class overlap."""
    weight = {
        "uspto-tess":     1.0,
        "app-store":      0.85,
        "play-store":     0.85,
        "amazon":         0.80,
        "trademarkia":    0.75,
        "github":         0.45,
        "product-hunt":   0.55,
        "apple-podcasts": 0.65,
        "spotify":        0.65,
        "youtube":        0.50,
        "patreon":        0.40,
        "leafly":         0.55,
        "nys-trademark":  0.85,
        "web":            0.30,
    }.get(source, 0.4)
    if not same_class:
        weight *= 0.55
    score = sim * weight
    if score >= 0.85: return "VERY_HIGH"
    if score >= 0.65: return "HIGH"
    if score >= 0.40: return "MEDIUM"
    return "LOW"


# --- Real Nimble caller ------------------------------------------------------

def _nimble_search(query: str, site: Optional[str] = None, max_results: int = 10) -> list[dict]:
    """Real Nimble client.search() wrapper. Returns a list of {title, url, snippet} dicts.
    NOTE: shape may need adjustment based on actual SearchResponse fields — replace
    accessor pattern with whatever client.search() actually returns when first
    tested with a live key. Caller treats this as best-effort."""
    if not _HAS_NIMBLE:
        return []
    # Verified against nimble_python 0.18.0 (live call 2026-05-29): client.search()
    # takes query=str plus optional include_domains/max_results, and returns a
    # SearchResponse whose .results is a list of Result objects with fields
    # {title, url, description, content, metadata{position,...}}. The old code read a
    # non-existent `snippet` field and an alternate `data` attr, so the live path
    # produced no usable rows. We map description -> snippet here.
    kwargs: dict = {"query": query, "max_results": max_results}
    if site:
        # Use the API's domain filter instead of a `site:` query hack.
        kwargs["include_domains"] = [site]
    try:
        resp = _NIMBLE_CLIENT.search(**kwargs)  # type: ignore[union-attr]
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[nimble] search failed for site={site!r}: {e}\n")
        return []
    out: list[dict] = []
    for item in (getattr(resp, "results", None) or []):
        if isinstance(item, dict):
            title = item.get("title", "") or ""
            url = item.get("url", "") or ""
            desc = item.get("description", "") or item.get("content", "") or ""
            meta = item.get("metadata", {}) or {}
            pos = meta.get("position") if isinstance(meta, dict) else None
        else:
            title = getattr(item, "title", "") or ""
            url = getattr(item, "url", "") or ""
            desc = getattr(item, "description", "") or getattr(item, "content", "") or ""
            meta = getattr(item, "metadata", None)
            pos = getattr(meta, "position", None) if meta is not None else None
        out.append({"title": title, "url": url, "snippet": desc, "position": pos})
    return out


# --- Stub mode (realistic fake data for file:// demo) -----------------------

def _stub_conflicts(mark: str, classes: list[int], niche: str) -> list[Conflict]:
    """Hand-curated mobile-app niche conflicts for demo purposes.
    Returns a mix of LOW/MEDIUM/HIGH so the demo shows the report's range.
    Conflicts are calibrated for mark='BANKSY AI' so the demo narrative makes sense."""
    has_9 = 9 in classes
    has_42 = 42 in classes
    has_41 = 41 in classes

    conflicts = [
        Conflict(
            source="uspto-tess",
            mark="BANKSY",
            holder="Pest Control Office Limited (Banksy LLC)",
            class_or_category="Class 16, 25, 41",
            similarity=similarity(mark, "BANKSY"),
            risk=grade_risk(similarity(mark, "BANKSY"), "uspto-tess", same_class=has_41),
            url="https://tsdr.uspto.gov/#caseNumber=88876543",
            notes=("Live registration owned by the holder controlling rights to the artist 'Banksy'. "
                   "Class 41 overlap is material if your app provides entertainment or art-related content. "
                   "Class 25 (clothing) and 16 (paper goods) outside scope but signal aggressive enforcement."),
        ),
        Conflict(
            source="uspto-tess",
            mark="BANKSY VAULT",
            holder="Banksy Vault LLC",
            class_or_category="Class 35, 42",
            similarity=similarity(mark, "BANKSY VAULT"),
            risk=grade_risk(similarity(mark, "BANKSY VAULT"), "uspto-tess", same_class=has_42),
            url="https://tsdr.uspto.gov/#caseNumber=97123456",
            notes=("Software-services class (42) overlap is the § 2(d) trigger if your goods/services include "
                   "SaaS. 'AI' suffix doesn't sufficiently distinguish from the dominant 'Banksy' element."),
        ),
        Conflict(
            source="app-store",
            mark="Banksy AR",
            holder="Banksy AR Studios",
            class_or_category="iOS app — Photo & Video",
            similarity=similarity(mark, "Banksy AR"),
            risk=grade_risk(similarity(mark, "Banksy AR"), "app-store", same_class=has_9),
            url="https://apps.apple.com/us/app/banksy-ar/id1234567890",
            notes=("Live iOS app, ~50K downloads. Common-law rights in the same channel of trade as your "
                   "intended app. Strong evidence of consumer confusion if both ship."),
        ),
        Conflict(
            source="play-store",
            mark="Banksy Wallpapers",
            holder="WallpaperHub Studios",
            class_or_category="Android app — Personalization",
            similarity=similarity(mark, "Banksy Wallpapers"),
            risk=grade_risk(similarity(mark, "Banksy Wallpapers"), "play-store", same_class=has_9),
            url="https://play.google.com/store/apps/details?id=com.wallpaperhub.banksy",
            notes=("Descriptive use of 'Banksy' as wallpaper subject, not as a brand. Lower § 2(d) risk but still "
                   "shows the namespace is crowded in the mobile-app channel."),
        ),
        Conflict(
            source="github",
            mark="banksy-ai",
            holder="github.com/example-org/banksy-ai",
            class_or_category="open-source repo (AI/ML)",
            similarity=similarity(mark, "banksy-ai"),
            risk=grade_risk(similarity(mark, "banksy-ai"), "github", same_class=has_9 or has_42),
            url="https://github.com/example-org/banksy-ai",
            notes=("Identical mark used as project name. ~120 stars, MIT license. Not registered but visible "
                   "developer-community use creates a § 43(a) unregistered-mark risk."),
        ),
        Conflict(
            source="product-hunt",
            mark="Banksy.ai",
            holder="independent indie developer",
            class_or_category="Product Hunt launch (AI)",
            similarity=similarity(mark, "Banksy.ai"),
            risk=grade_risk(similarity(mark, "Banksy.ai"), "product-hunt", same_class=has_9 or has_42),
            url="https://www.producthunt.com/posts/banksy-ai",
            notes=("Launched 6 months ago, ~400 upvotes. Domain 'banksy.ai' actively used. Even if not "
                   "USPTO-registered, this creates priority of common-law use in your target market."),
        ),
        Conflict(
            source="web",
            mark="Banksy AI Art Generator",
            holder="various unrelated parties",
            class_or_category="Generic web mentions",
            similarity=similarity(mark, "Banksy AI Art Generator"),
            risk="LOW",
            url="https://www.google.com/search?q=%22banksy+ai%22+art+generator",
            notes=("Descriptive uses of 'Banksy AI' as a category label (AI tools that mimic Banksy's style). "
                   "Not a single conflicting source but evidence the term is becoming descriptive — § 2(e)(1) "
                   "concern in addition to § 2(d)."),
        ),
    ]
    # Filter conflicts to those above zero similarity (defensive)
    return [c for c in conflicts if c.similarity > 0]


# --- Aggregator + narrative --------------------------------------------------

def _aggregate(conflicts: list[Conflict]) -> tuple[str, str]:
    """Roll up per-conflict risks into an overall risk score and recommendation."""
    if not conflicts:
        return "LOW", "PROCEED"
    counts = {r: 0 for r in RISK_LEVELS}
    for c in conflicts:
        counts[c.risk] = counts.get(c.risk, 0) + 1
    if counts["VERY_HIGH"] > 0:
        return "VERY_HIGH", "DO_NOT_PROCEED"
    if counts["HIGH"] >= 2:
        return "HIGH", "DO_NOT_PROCEED"
    if counts["HIGH"] == 1:
        return "HIGH", "PROCEED_WITH_AMENDMENT"
    if counts["MEDIUM"] >= 3:
        return "MEDIUM", "PROCEED_WITH_AMENDMENT"
    if counts["MEDIUM"] > 0:
        return "MEDIUM", "PROCEED_WITH_AMENDMENT"
    return "LOW", "PROCEED"


def _narrative(report: KnockoutReport) -> str:
    """Plain-English attorney-style summary."""
    high = [c for c in report.conflicts if c.risk in ("HIGH", "VERY_HIGH")]
    med = [c for c in report.conflicts if c.risk == "MEDIUM"]
    sources = ", ".join(report.sources_searched)
    parts: list[str] = []
    parts.append(
        f"Knockout search on '{report.mark}' in international class(es) "
        f"{', '.join(str(c) for c in report.classes)} across {sources}."
    )
    if report.recommendation == "PROCEED":
        parts.append(
            "Overall risk is LOW. No live registrations or common-law uses materially overlap in your "
            "class scope. We recommend proceeding to filing with the goods/services description as drafted."
        )
    elif report.recommendation == "PROCEED_WITH_AMENDMENT":
        parts.append(
            f"Overall risk is {report.risk_score}. There are conflicts in your class scope that we should "
            "address before filing — typically by tightening the goods/services description, switching to a "
            "Supplemental Register if descriptive, or amending the mark to add distinctiveness."
        )
    else:
        parts.append(
            f"Overall risk is {report.risk_score} — we recommend NOT filing this mark as-is. "
            "The conflicts below would almost certainly draw a § 2(d) likelihood-of-confusion refusal, "
            "putting your $250–$350 USPTO fee at risk. We recommend rebrand or significant mark modification."
        )
    if high:
        parts.append("High-risk conflicts:")
        for c in high:
            parts.append(f"  • {c.source.upper()}: '{c.mark}' ({c.holder or 'unattributed'}) — {c.notes}")
    if med:
        parts.append("Medium-risk conflicts (worth amending around):")
        for c in med:
            parts.append(f"  • {c.source.upper()}: '{c.mark}' — {c.notes}")
    if report.stub:
        parts.append("")
        parts.append("[DEMO STUB] This report was generated in stub mode (NIMBLE_API_KEY not set). "
                     "Real searches against USPTO TESS, Apple App Store, Google Play, GitHub, and Product "
                     "Hunt happen when the env var is set.")
    return "\n".join(parts)


# --- Public entry point ------------------------------------------------------

def knockout_search(mark: str, classes: list[int], niche: str = "mobile-app") -> KnockoutReport:
    """Orchestrate the multi-source knockout search and return a structured report.
    Falls back to stub mode if Nimble is not configured."""
    sources = NICHE_SOURCES.get(niche, NICHE_SOURCES["generic"])
    report = KnockoutReport(
        mark=mark,
        classes=classes,
        niche=niche,
        searched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sources_searched=sources,
        conflicts=[],
        stub=not _HAS_NIMBLE,
    )

    if _HAS_NIMBLE:
        # Real agent loop — placeholder shape; real implementation maps each source
        # to the right Nimble template (e.g. amazon-product-page, app-store-search,
        # play-store-search, github-search, product-hunt-search) plus client.search()
        # for generic web. Each call yields candidates → score → append.
        for src in sources:
            site_filter = {
                "uspto-tess":     "tsdr.uspto.gov",
                "app-store":      "apps.apple.com",
                "play-store":     "play.google.com",
                "github":         "github.com",
                "product-hunt":   "producthunt.com",
                "amazon":         "amazon.com",
                "trademarkia":    "trademarkia.com",
                "apple-podcasts": "podcasts.apple.com",
                "spotify":        "spotify.com",
                "youtube":        "youtube.com",
                "patreon":        "patreon.com",
                "leafly":         "leafly.com",
                "nys-trademark":  "dos.ny.gov",
                "web":            None,
            }.get(src)
            results = _nimble_search(mark, site=site_filter)
            report.nimble_calls_made += 1
            registry_like = src in ("uspto-tess", "app-store", "play-store",
                                     "amazon", "trademarkia", "nys-trademark")
            for r in results[:8]:
                title = (r.get("title") or "").strip()
                snippet = (r.get("snippet") or "").strip()
                if not title and not snippet:
                    continue
                sim = mark_match(mark, title, snippet)
                if sim < 0.55:
                    continue
                report.conflicts.append(
                    Conflict(
                        source=src,
                        mark=title or "(untitled live result)",
                        holder=snippet[:120],
                        class_or_category="(live result - Nice class not inferred; attorney to confirm)",
                        similarity=round(sim, 3),
                        risk=grade_risk(sim, src, same_class=registry_like),
                        url=r.get("url", ""),
                        notes="Live Nimble web result - attorney should open the source and confirm class + status.",
                    )
                )
    else:
        # Stub mode — deterministic, demo-friendly
        report.conflicts = _stub_conflicts(mark, classes, niche)

    report.risk_score, report.recommendation = _aggregate(report.conflicts)
    report.narrative = _narrative(report)
    return report


def to_json(report: KnockoutReport) -> str:
    """Serialize report to indented JSON."""
    def _enc(o):
        if dataclasses.is_dataclass(o):
            return asdict(o)
        raise TypeError
    return json.dumps(asdict(report), indent=2, default=_enc)


# --- CLI ---------------------------------------------------------------------

def _main():
    p = argparse.ArgumentParser(description="Nota.Lawyer Nimble TESS knockout agent")
    p.add_argument("--mark", required=True, help="Trademark text to search")
    p.add_argument("--classes", required=True,
                   help="Comma-separated Nice classification numbers, e.g. 9,42,41")
    p.add_argument("--niche", default="mobile-app",
                   choices=list(NICHE_SOURCES.keys()), help="Niche tuning")
    p.add_argument("--out", help="Write report JSON to this path; else stdout")
    args = p.parse_args()
    classes = [int(c.strip()) for c in args.classes.split(",") if c.strip()]
    report = knockout_search(args.mark, classes, args.niche)
    blob = to_json(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(blob)
        sys.stderr.write(f"wrote {args.out}\n")
        sys.stderr.write(f"risk={report.risk_score} rec={report.recommendation} stub={report.stub}\n")
    else:
        print(blob)


if __name__ == "__main__":
    _main()
