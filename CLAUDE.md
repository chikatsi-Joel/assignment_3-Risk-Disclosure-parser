# CLAUDE.md — Financial Intelligence Platform

## Project Overview

10-K / 10-Q MD&A & Risk Disclosure Analyzer.
Connects live to SEC EDGAR, parses financial filings from 12 major US banks,
applies Loughran-McDonald sentiment analysis and risk theme classification.

---

## File Architecture

```
tt/
├── CLAUDE.md           ← this file
├── app.py              ← Streamlit entry point: streamlit run app.py
├── edgar_fetcher.py    ← SEC EDGAR API client + BANKS_CATALOG (12 banks)
├── parser.py           ← BeautifulSoup + regex section extractor (MD&A, Risk, Market Risk)
├── analyzer.py         ← LM sentiment scoring, risk themes, keyword extraction
├── charts.py           ← Plotly chart factory (receives data, never reads edgar_fetcher)
├── requirements.txt    ← pip install -r requirements.txt
├── PRD.md              ← Product Requirements Document v2.0
└── DEBRIEF.md          ← Class debrief: what was built, challenges, AGI discussion
```

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Architecture Rules

- `charts.py` receives data as parameters — never imports edgar_fetcher or analyzer.
- `parser.py` returns plain dicts — no Streamlit, no Plotly.
- `analyzer.py` returns plain dicts — no Streamlit, no Plotly.
- All EDGAR requests go through `edgar_fetcher._get()` which handles retries + rate limiting.
- All slow operations in `app.py` are wrapped in `@st.cache_data(ttl=3600)`.

---

## Key Data Structures

```python
# Filing (from edgar_fetcher.get_company_filings)
{
  "accession": "0000019617-24-000016",
  "accession_nd": "000001961724000016",
  "date": "2024-02-13",
  "form": "10-K",
  "cik": "19617",
  "primary_doc": "jpm-20231231.htm",
  "base_url": "https://www.sec.gov/Archives/edgar/data/19617/...",
}

# Sections (from parser.extract_sections)
{
  "mda": "text...",
  "risk_factors": "text...",
  "market_risk": "text...",
}

# Analysis (from analyzer.analyze_sections)
{
  "mda": {
    "sentiment": {"positive": 120, "negative": 340, "total": 8500, "tone_pct": -2.59},
    "themes": [("Credit Risk", 45), ("Market Risk", 30), ...],
    "keywords": [("capital", 89), ("risk", 76), ...],
    "word_count": 8500,
    "found": True,
  },
  ...
}
```

---

## Covered Banks

JPMorgan Chase, Bank of America, Wells Fargo, Citigroup, Goldman Sachs,
Morgan Stanley, U.S. Bancorp, PNC Financial, Truist Financial, Capital One,
Charles Schwab, American Express

To add a bank: add an entry to `BANKS_CATALOG` in `edgar_fetcher.py`.
CIK numbers are found at https://www.sec.gov/cgi-bin/browse-edgar

---

## External Dependencies

- **SEC EDGAR** (data.sec.gov / www.sec.gov) — public, no API key required
- User-Agent header MUST include an email per SEC policy (set in edgar_fetcher.py)
- Rate limit: 10 req/s max → platform uses 120ms delay + exponential backoff on 429
