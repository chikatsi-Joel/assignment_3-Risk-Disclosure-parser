# analyzer.py — Financial Text Sentiment & Theme Analyzer
# Implements Loughran-McDonald-style financial sentiment scoring.
# No external NLP model required — pure Python word-list approach.

import re
from collections import Counter

# ─── Loughran-McDonald Financial Sentiment Word Lists (abbreviated) ─
# Source: Loughran & McDonald (2011) Journal of Finance

LM_NEGATIVE = {
    "abandon", "abandonment", "abandoned", "adverse", "adversely", "adversity",
    "affected", "allegation", "allegations", "alleged", "ambiguous", "ambiguity",
    "bankruptcy", "below", "breach", "bribery", "burden", "challenge",
    "challenges", "claim", "claims", "closure", "collapse", "complain",
    "complaint", "concentration", "concerns", "conflict", "controversy",
    "corruption", "counterclaim", "credit loss", "credit losses", "criminal",
    "curtailed", "decline", "declined", "declining", "decrease", "decreased",
    "default", "defaulted", "defaults", "delinquency", "delinquent",
    "deterioration", "difficulty", "diminished", "dispute", "disrupt",
    "disruption", "dissolution", "distress", "downturn", "erode", "erosion",
    "exceed", "excessive", "exhausted", "fail", "failed", "failure", "falling",
    "fault", "fear", "foreclose", "foreclosure", "fraud", "fraudulent",
    "hamper", "harm", "harmed", "hazard", "impairment", "impaired",
    "inadequate", "inability", "insufficient", "intense", "investigation",
    "lawsuit", "layoffs", "less", "limit", "limited", "liquidation",
    "litigation", "lose", "loss", "losses", "misconduct", "mismanagement",
    "negative", "nonperforming", "obstacle", "problem", "prohibit",
    "penalty", "poor", "problematic", "recession", "reduce", "reduced",
    "reduction", "regulatory", "reject", "restriction", "risk", "risks",
    "risky", "severe", "shortage", "slowed", "slowdown", "stress",
    "struggling", "uncertainty", "unfavorable", "unpredictable", "unstable",
    "unresolved", "violation", "volatile", "volatility", "vulnerability",
    "warn", "warning", "weak", "weakness", "withdraw", "written off",
    "writedown", "write-off", "wrote off",
}

LM_POSITIVE = {
    "achieve", "achieved", "achievement", "advantageous", "beneficial",
    "benefit", "benefits", "better", "capitalize", "certainty", "confident",
    "confident", "deliver", "delivered", "diversified", "efficient",
    "efficiency", "enhance", "enhanced", "excellent", "exceed", "exceeded",
    "exceptional", "expansion", "favorable", "gain", "gains", "grow",
    "growth", "higher", "improve", "improved", "improvement", "increase",
    "increased", "innovative", "investment", "leader", "leading", "leverage",
    "opportunistic", "opportunity", "outperform", "positive", "profit",
    "profitable", "profitability", "progress", "promote", "record",
    "resilient", "resilience", "robust", "solid", "stable", "stability",
    "strength", "strong", "successful", "success", "superior", "support",
    "sustainable", "well-positioned",
}

# ─── Risk Theme Keywords ────────────────────────────────────────────
RISK_THEMES = {
    "Credit Risk":        ["credit risk", "credit loss", "default", "nonperforming", "delinquency", "charge-off", "allowance for credit"],
    "Market Risk":        ["market risk", "interest rate risk", "foreign exchange", "fx risk", "rate sensitivity", "hedging", "derivatives"],
    "Operational Risk":   ["operational risk", "system failure", "cybersecurity", "cyber", "data breach", "fraud", "technology risk"],
    "Regulatory/Legal":   ["regulatory", "compliance", "enforcement", "litigation", "lawsuit", "penalty", "investigation", "consent order"],
    "Liquidity Risk":     ["liquidity risk", "funding", "capital ratio", "tier 1", "leverage ratio", "liquidity coverage"],
    "Macroeconomic":      ["recession", "inflation", "gdp", "unemployment", "economic downturn", "interest rate environment", "federal reserve"],
    "Climate/ESG":        ["climate", "esg", "sustainability", "carbon", "environmental", "transition risk", "physical risk"],
    "Geopolitical":       ["geopolitical", "sanctions", "russia", "china", "war", "tariff", "trade war", "ukraine"],
}


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer ignoring punctuation."""
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def sentiment_score(text: str) -> dict:
    """
    Compute Loughran-McDonald sentiment metrics for a block of text.
    Returns: positive_count, negative_count, total_words, tone_score.
    tone_score = (pos - neg) / total_words * 100  (percentage points)
    """
    words = _tokenize(text)
    total = len(words)
    if total == 0:
        return {"positive": 0, "negative": 0, "total": 0, "tone": 0.0, "tone_pct": 0.0}

    pos = sum(1 for w in words if w in LM_POSITIVE)
    neg = sum(1 for w in words if w in LM_NEGATIVE)

    tone = (pos - neg) / total * 100
    return {
        "positive":  pos,
        "negative":  neg,
        "total":     total,
        "tone":      round(tone, 4),
        "tone_pct":  round(tone, 2),
    }


def identify_risk_themes(text: str, top_n: int = 6) -> list[tuple[str, int]]:
    """Count occurrences of each risk theme in the text."""
    text_lower = text.lower()
    counts: dict[str, int] = {}
    for theme, keywords in RISK_THEMES.items():
        total = sum(text_lower.count(kw) for kw in keywords)
        if total > 0:
            counts[theme] = total
    sorted_themes = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_themes[:top_n]


def top_keywords(text: str, n: int = 30, exclude_stopwords: bool = True) -> list[tuple[str, int]]:
    """Return the top-N most frequent non-trivial words."""
    stopwords = {
        "the", "and", "of", "to", "a", "in", "that", "is", "for", "on",
        "our", "we", "are", "have", "with", "as", "or", "an", "may", "will",
        "be", "by", "at", "from", "this", "such", "not", "also", "which",
        "its", "their", "these", "other", "any", "were", "has", "been",
        "if", "it", "more", "but", "all", "than", "can", "had", "when",
        "would", "could", "do", "no", "up", "into", "during", "including",
        "under", "certain", "there", "each", "further", "however", "s",
        "us", "who", "was", "they", "them", "about", "between", "through",
        "i", "he", "she", "so", "what", "some", "those", "new", "year",
        "years", "related", "based", "used", "result", "results", "total",
        "within", "whether", "use", "should", "without", "following",
        "company", "bank", "financial", "corporation", "inc", "llc",
    }
    words = _tokenize(text)
    if exclude_stopwords:
        words = [w for w in words if w not in stopwords and len(w) > 3]
    counter = Counter(words)
    return counter.most_common(n)


def analyze_sections(sections: dict[str, str]) -> dict[str, dict]:
    """Run full analysis on all parsed sections."""
    results: dict[str, dict] = {}
    for section_key, text in sections.items():
        if text.startswith("(Section not"):
            results[section_key] = {
                "sentiment":  {"positive": 0, "negative": 0, "total": 0, "tone": 0.0, "tone_pct": 0.0},
                "themes":     [],
                "keywords":   [],
                "word_count": 0,
                "found":      False,
            }
        else:
            results[section_key] = {
                "sentiment":  sentiment_score(text),
                "themes":     identify_risk_themes(text),
                "keywords":   top_keywords(text, n=20),
                "word_count": len(text.split()),
                "found":      True,
            }
    return results


def compare_tone_across_banks(bank_analyses: dict[str, dict], section: str = "mda") -> list[dict]:
    """
    Given a dict of {bank_name: analysis_result}, return a list sorted
    by tone_pct for easy comparison bar chart.
    """
    rows = []
    for bank, analysis in bank_analyses.items():
        sec = analysis.get(section, {})
        sent = sec.get("sentiment", {})
        rows.append({
            "bank":      bank,
            "tone":      sent.get("tone_pct", 0.0),
            "positive":  sent.get("positive", 0),
            "negative":  sent.get("negative", 0),
            "words":     sent.get("total", 0),
        })
    return sorted(rows, key=lambda r: r["tone"], reverse=True)
