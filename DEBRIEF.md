# Class Debrief — Financial Intelligence Platform
## What We Built, Challenges Faced, and the AGI Question
**Date:** 2026-06-18  
**Presenter:** Samuel Piedjou  

---

## 1. What We Built

### v1.0 → v2.0: From Budget Manager to Financial Intelligence Platform

Our project has evolved across two distinct phases:

#### Phase 1 — Personal Budget Manager (`fin/`)
- A Streamlit web app for personal finance in XAF (Central African Franc)
- Single user, no external data, 400 000 XAF monthly income tracking
- Features: budget breakdown donut chart, savings gauge, annual projection
- **Constraint:** 100% French UI, no database, no external connections
- **Value delivered:** A practical tool for personal discipline

#### Phase 2 — Financial Intelligence Platform (`fin/tt/`)
- Connects live to the **SEC EDGAR** public database (U.S. Securities & Exchange Commission)
- Downloads and parses **10-K** (annual) and **10-Q** (quarterly) filings from 12 major US banks
- Extracts three key textual sections automatically:
  - **MD&A** — Management's Discussion & Analysis (Item 7 / Item 2)
  - **Risk Factors** (Item 1A) — What management says could go wrong
  - **Market Risk** (Item 7A / Item 3) — Interest rate, FX, and derivatives exposure
- Applies **Loughran-McDonald financial sentiment analysis** — the gold standard wordlist
  for measuring financial text tone (not general sentiment tools like VADER)
- Classifies text into **8 risk theme buckets**: Credit, Market, Operational, Regulatory,
  Liquidity, Macroeconomic, Climate/ESG, and Geopolitical
- **Multi-bank comparison**: side-by-side tone scores, risk heatmaps, and summary tables
- **Banks covered**: JPMorgan, BofA, Wells Fargo, Citigroup, Goldman Sachs, Morgan Stanley,
  U.S. Bancorp, PNC, Truist, Capital One, Charles Schwab, American Express

### Architecture Summary
```
app.py (Streamlit UI)
 ├── edgar_fetcher.py  — SEC EDGAR REST API client
 ├── parser.py         — BeautifulSoup + regex section extractor
 ├── analyzer.py       — LM sentiment + risk themes + keywords
 └── charts.py         — Plotly visualizations
```

---

## 2. Key Technical Challenges & How We Overcame Them

### Challenge 1 — Parsing Inconsistent HTML
**The problem:** SEC filings are written by hundreds of different law firms and accounting
departments over 30+ years. There is no enforced HTML schema. JPMorgan's 10-K looks
completely different from Goldman Sachs's. Section headers appear as:
- `<a name="item7">` (old style)
- `<h2>ITEM 7. MANAGEMENT'S DISCUSSION</h2>` (modern)
- `<div id="iTEM7A">` (XBRL-tagged)
- Plain `ITEM 7` buried in a `<p>` inside a `<table>`

**How we solved it:**
- Built a **dual-strategy parser** in `parser.py`:
  1. First attempts anchor-based extraction (finds `<a name=...>` and heading tags)
  2. Falls back to plain-text regex extraction if the HTML strategy yields < 200 characters
- Used `lxml` (faster than `html.parser`) for BeautifulSoup backend
- Normalized item numbers to lowercase and stripped all variations of punctuation

**Lesson:** Defensive parsing with multiple fallback strategies is essential for real-world
web scraping. The "happy path" HTML is rarely what you encounter in production data.

---

### Challenge 2 — SEC EDGAR Rate Limiting
**The problem:** SEC EDGAR enforces a **10 requests/second** limit and returns HTTP 429
(Too Many Requests) if exceeded. Our multi-bank comparison loads 6+ filings simultaneously,
which can easily breach the limit.

**How we solved it:**
- Added a **120ms sleep** after every EDGAR request in `edgar_fetcher.py`
- Implemented **exponential backoff** (2^n seconds) on HTTP 429 responses, up to 3 retries
- Used `st.cache_data(ttl=3600)` — Streamlit's session cache — so the same filing is never
  downloaded twice in the same hour

**Lesson:** External API rate limits are a first-class engineering constraint, not an
afterthought. Always implement backoff and caching before going to production.

---

### Challenge 3 — Section Boundaries Are Ambiguous
**The problem:** After finding "ITEM 7" in the HTML, how do you know where it ends?
The next section might be labeled "ITEM 7A", "ITEM 8", or might not exist.
Also, the Table of Contents at the beginning of every 10-K contains duplicate
"ITEM 7" anchors that must be skipped.

**How we solved it:**
- Built `_find_item_anchors()` to collect ALL item anchors in document order, then
  extracted text **between** consecutive anchors
- For the plain-text fallback, used a regex that looks for the NEXT item number
  to bound the extraction window
- Added a minimum-length check (< 200 chars = failed extraction → try fallback)

**Lesson:** Text extraction from structured documents is an NLP-adjacent problem.
The structure is implicit, not explicit — the parser must infer it from context.

---

### Challenge 4 — Sentiment Analysis in Finance Is Different
**The problem:** General sentiment tools (VADER, TextBlob) are trained on tweets and
movie reviews. In finance, words like "liability", "risk", "capital", and "hedging"
carry very different connotations. VADER would score a Goldman Sachs risk disclosure as
50% positive because it contains phrases like "we successfully hedged our risk."

**How we solved it:**
- Used the **Loughran-McDonald (2011) financial word list**, published in the _Journal
  of Finance_ and specifically designed for 10-K/10-Q analysis
- The LM list has ~2400 negative and ~354 positive finance-specific terms
- Our tone score = (positive − negative) / total_words × 100, expressed in percentage
  points — the standard formula in the financial NLP literature

**Lesson:** Domain-specific tools beat general-purpose ones. The best model for the job
is the one designed for the specific domain, not the one with the most hype.

---

### Challenge 5 — Making Large Filings Usable
**The problem:** A JPMorgan 10-K is typically 400+ pages and 3–8 MB of HTML.
Displaying 80,000 characters of raw text in a browser is unusable. But truncating
too aggressively loses important content.

**How we solved it:**
- Set a `max_chars=80_000` limit per section in the parser
- The Streamlit UI shows summary metrics (word count, tone, themes) first
- Raw text is behind an **expander widget** (collapsed by default) capped at 6,000 chars
- Charts (keyword bar, radar) provide a navigable visual summary of what matters

**Lesson:** UI/UX design for large datasets is as important as the underlying computation.
Surfacing insights first, raw data second, is the right hierarchy.

---

## 3. What We Would Do Differently

1. **Add LLM summaries (v3):** Claude or GPT integration to generate a 3-bullet
   plain-language summary of each section would be transformative for accessibility.

2. **XBRL structured data:** SEC now requires XBRL tagging for many disclosures.
   Using the structured data API instead of HTML parsing would eliminate the parsing
   fragility problem entirely — but XBRL coverage of qualitative sections is still
   incomplete.

3. **Async loading:** Python's `asyncio` + `httpx` would let us load all 6 banks
   simultaneously instead of sequentially, reducing multi-bank load time from ~90s to ~15s.

4. **Testing:** We have no unit tests for the parser. Filings from 2010 vs 2024 can
   differ significantly — a test suite with representative fixtures would prevent regressions.

---

## 4. Are We at AGI?

### The Honest Answer: Not Yet, But the Gap Is Closing Fast

**AGI** (Artificial General Intelligence) traditionally means a system that can perform
**any intellectual task a human can perform, at human level or better**, across all domains,
including transfer learning to entirely new tasks it has never seen.

### What Current AI (as of June 2026) CAN Do
- Write production-quality code across 50+ languages ✅
- Parse and analyze 300-page legal/financial documents ✅
- Solve IMO-level mathematics problems ✅
- Generate photorealistic images, music, and video ✅
- Reason through multi-step logical problems ✅
- Build full-stack applications from a description ✅
- Explain concepts across medicine, law, physics, history ✅

### What Current AI CANNOT Do (Reliably)
- Maintain truly persistent memory across independent sessions ❌
- Act in the world without human approval on consequential decisions ❌
- Reliably distinguish hallucination from ground truth in real-time ❌
- Adapt to radically novel physical environments (embodied AI is early-stage) ❌
- Demonstrate genuine goal-directed **agency** over months-long horizons ❌
- Understand its own limitations with consistent metacognition ❌

### Where We Stand
The leading models in 2026 — Claude Opus 4.8, GPT-5, Gemini Ultra 2 — exhibit what
researchers call **"proto-AGI" or "narrow superintelligence"**: they dramatically exceed
human performance within specific well-defined tasks, but still require human scaffolding
to function reliably across the full breadth of open-ended real-world situations.

The more important question is not "Are we at AGI?" but:
> **"How do we build the infrastructure to use these capabilities safely and responsibly?"**

That is the actual engineering and governance problem in front of us — and it is exactly
the kind of systems-thinking that financial intelligence platforms like ours are beginning
to address: using AI to surface insights from large document corpora, with human analysts
retaining final judgment.

### For Our Field (Finance)
AI is already transforming financial analysis. Quant hedge funds (Two Sigma, Renaissance,
Man Group) have used ML for decades. What's new:
- **10-K/10-Q NLP** tools are moving from research to production
- **Earnings call transcript analysis** is a mature fintech product category
- **Regulatory filing monitoring** (e.g., tracking Fed speeches for policy signals) is
  now automatable
- The gap between what AI can parse and what human analysts can read is essentially closed

The remaining value of human analysts is **judgment, relationship, and accountability**
— not document processing speed. Our platform is an example of AI augmenting analysts,
not replacing them.

### Bottom Line
We are not at AGI. We are at something arguably more disruptive in the near term:
**AI systems that are superhumanly good at specific cognitive tasks that were previously
gatekept by scarce human expertise.** For financial analysis, that inflection point has
already happened.

---

## 5. Summary

| Dimension | v1.0 | v2.0 |
|-----------|------|------|
| Data source | Hardcoded constants | Live SEC EDGAR API |
| Scope | 1 person, XAF budget | 12 banks, US filings |
| NLP | None | LM sentiment + risk themes |
| Visualization | 3 charts | 6+ chart types |
| Lines of code | ~250 | ~950 |
| Key technique | Streamlit + Pandas | HTML parsing + financial NLP |
| AGI used? | No | No (but AI-assisted development) |

---

The branch of project is main.
*Prepared for class presentation, 2026-06-18*
