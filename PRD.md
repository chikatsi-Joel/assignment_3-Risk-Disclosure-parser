# Product Requirements Document
## Financial Intelligence Platform — 10-K / 10-Q MD&A & Risk Disclosure Analyzer
**Version:** 2.0  
**Date:** 2026-06-18  
**Author:** FinTech Research Group  
**Status:** Active Development

---

## 1. Executive Summary

The Financial Intelligence Platform is a real-time, browser-based analytical tool that
connects to the U.S. Securities and Exchange Commission's EDGAR database, downloads
publicly-filed annual (10-K) and quarterly (10-Q) disclosures from major financial
institutions, and applies computational linguistics techniques to surface patterns in
management tone, risk language, and strategic priorities.

**Elevator pitch:** _"Bloomberg Terminal for qualitative filings — instantly surface
what banks are worrying about and how confident management sounds, across all major
institutions, side-by-side."_

---

## 2. Problem Statement

### 2.1 The Gap
Quantitative financial data (EPS, ROE, NIM, CET1 ratios) is commoditized and available
everywhere. The qualitative narrative — what management says about credit quality, the
macro environment, regulatory risk, or digital transformation — lives in 100-to-400-page
HTML documents filed with the SEC. Reading those manually takes hours per company.

### 2.2 Who Suffers
- **Buy-side analysts** reading 10+ bank filings per quarter during earnings season
- **Risk officers** needing to benchmark competitors' disclosed risks
- **Academic researchers** studying financial communication and earnings guidance
- **Business students** learning to interpret corporate disclosures

### 2.3 What Currently Exists
| Tool | Gap |
|------|-----|
| SEC EDGAR full-text search | Returns raw HTML; no NLP or cross-bank view |
| Bloomberg (terminal) | Quantitative only; no parsed qualitative sections |
| Refinitiv Eikon | Expensive; limited qualitative parsing |
| Manual reading | 4–8 hrs per filing; not scalable |

---

## 3. Goals & Non-Goals

### Goals (v2.0)
- [x] Real-time fetch from SEC EDGAR (no data warehouse needed)
- [x] Parse MD&A, Risk Factors, and Market Risk sections automatically
- [x] Apply Loughran-McDonald financial sentiment scoring
- [x] Surface top risk themes per bank via keyword taxonomy
- [x] Enable side-by-side multi-bank tone comparison
- [x] 12 major US banks covered out-of-the-box
- [x] Zero-cost operation (all data is public)

### Non-Goals (v2.0)
- Real-time stock price integration (v3 roadmap)
- LLM-generated summaries of filings (v3 roadmap)
- Non-US filers / IFRS filings (v3 roadmap)
- User authentication / saved portfolios (v3 roadmap)
- Automated alerting / email digests (v3 roadmap)

---

## 4. User Personas

### Persona A — "The Analyst" (Primary)
- **Role:** Equity research analyst, bank sector
- **Goal:** During earnings season, rapidly compare Q-over-Q tone shifts in MD&A
  across 8 banks in under 30 minutes
- **Pain:** Currently spends 4+ hours doing this manually
- **Success:** Opens the platform, selects 6 banks, sees tone comparison within 5 minutes

### Persona B — "The Risk Officer" (Secondary)
- **Role:** CRO team at a mid-sized bank
- **Goal:** Benchmark how competitors disclose credit, market, and operational risk
- **Pain:** Legal says they can't use competitor data without systematic sourcing
- **Success:** Downloads the heatmap and summary table as a quarterly benchmark report

### Persona C — "The Student" (Tertiary)
- **Role:** Finance/MBA student in a capital markets course
- **Goal:** Understand how to read a 10-K filing without reading 300 pages
- **Pain:** No structured guide exists; EDGAR is overwhelming
- **Success:** Loads one 10-K, sees extracted sections, understands key risk themes

---

## 5. Feature Requirements

### 5.1 Core Features (Must Have)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-01 | EDGAR Live Fetch | Pull latest N filings for any bank via CIK | P0 |
| F-02 | Section Extraction | Parse MD&A, Risk Factors, Market Risk from HTML | P0 |
| F-03 | LM Sentiment Scoring | Positive/negative word counts + tone percentage | P0 |
| F-04 | Risk Theme Detection | 8-category keyword taxonomy (credit, market, cyber…) | P0 |
| F-05 | Single-Bank Deep Dive | All sections with charts for one filing | P0 |
| F-06 | Multi-Bank Comparison | Tone bar + risk heatmap for up to 6 banks | P0 |
| F-07 | Summary Table | Exportable comparison table with conditional formatting | P1 |
| F-08 | Filing Selector | Pick from last N filings (not just most recent) | P1 |
| F-09 | Full Text Viewer | Expandable raw extracted text per section | P1 |
| F-10 | Bank Catalog | Pre-loaded CIKs for 12 major US financial institutions | P0 |

### 5.2 Enhanced Features (Should Have)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-11 | Trend Chart | Tone score over time (across multiple filings) | P1 |
| F-12 | Keyword Bar Chart | Top-N keywords per section | P1 |
| F-13 | Radar Chart | Risk theme spider/radar per bank | P1 |
| F-14 | Section Word Count | Filing completeness indicator | P2 |
| F-15 | Filing Timeline | Scatter chart of all filing dates | P2 |

### 5.3 Future Features (v3 Roadmap)

| ID | Feature | Description |
|----|---------|-------------|
| F-20 | LLM Summary | GPT/Claude-generated 3-bullet summary of MD&A |
| F-21 | Earnings Call Transcript | Parse 8-K earnings call transcripts |
| F-22 | International Filers | European banks via XBRL/IFRS |
| F-23 | Alerts | Email/Slack when new 10-Q drops for watchlist |
| F-24 | Portfolio Mode | User-defined watchlist with persistent state |
| F-25 | PDF Export | Download analysis as branded PDF report |
| F-26 | API Endpoint | FastAPI wrapper for programmatic access |

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | First filing render < 30 s (network-bound); cached renders < 1 s |
| **Caching** | Session-level 1-hour cache via `st.cache_data` |
| **Rate Limiting** | SEC EDGAR: ≤ 10 req/s; platform inserts 120 ms delay between calls |
| **Scalability** | Stateless; each Streamlit session is independent |
| **Security** | No user credentials stored; all data is public SEC data |
| **Reliability** | Graceful error handling if EDGAR is unreachable |
| **Cost** | $0 infrastructure cost; all external data is free/public |
| **Accessibility** | Responsive layout; no auth required; runs locally or on Streamlit Cloud |

---

## 7. Technical Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  app.py  (Streamlit UI)                   │
│  - Sidebar controls        - Tab routing                  │
│  - st.cache_data wrappers  - Conditional rendering        │
└────────────┬─────────────┬─────────────┬─────────────────┘
             │             │             │
   ┌─────────▼──┐  ┌───────▼──┐  ┌──────▼──────┐
   │edgar_fetcher│  │ parser.py│  │ analyzer.py │
   │            │  │          │  │             │
   │ EDGAR REST │  │BeautifulS│  │ LM Sentiment│
   │ API calls  │  │oup + regex│  │ Risk Themes │
   │ CIK lookup │  │ Section  │  │ Keywords    │
   │ HTML DL    │  │ splitter │  └──────┬──────┘
   └────────────┘  └──────────┘         │
                                  ┌──────▼──────┐
                                  │  charts.py  │
                                  │  Plotly figs│
                                  └─────────────┘

External APIs
  └── SEC EDGAR (data.sec.gov)  — submissions metadata
  └── SEC EDGAR (www.sec.gov)   — filing HTML documents
```

### 7.1 Data Flow
1. User selects bank + form type in sidebar
2. `edgar_fetcher.get_company_filings()` → EDGAR submissions API → list of filings
3. User selects a specific filing
4. `edgar_fetcher.fetch_filing_html()` → downloads primary HTML document
5. `parser.extract_sections()` → BeautifulSoup extracts MD&A, Risk Factors, Market Risk
6. `analyzer.analyze_sections()` → LM sentiment + risk themes + keywords
7. `charts.*` → Plotly figures rendered in Streamlit

### 7.2 Technology Stack
| Layer | Technology |
|-------|------------|
| UI Framework | Streamlit 1.32+ |
| Data Source | SEC EDGAR REST API (no auth) |
| HTML Parsing | BeautifulSoup 4 + lxml |
| Sentiment | Loughran-McDonald word list (built-in) |
| Visualization | Plotly 5.x |
| Data Manipulation | Pandas 2.x |
| Runtime | Python 3.11+ |
| Deployment | Streamlit Cloud / Docker / local |

---

## 8. Success Metrics

| Metric | Target (v2.0) | How to Measure |
|--------|---------------|----------------|
| Time to first insight | < 30 seconds | Stopwatch from page load to first chart |
| Section extraction accuracy | > 80% of filings | Manual spot-check of 20 random filings |
| Banks covered | 12 | Static catalog count |
| Form types supported | 10-K and 10-Q | Test matrix |
| Multi-bank comparison | Up to 6 simultaneous | Load test |
| Zero-cost operation | $0/month | AWS/cloud billing check |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SEC EDGAR rate limits 429 | Medium | High | Exponential backoff + session cache |
| HTML structure varies by filer | High | Medium | Dual-strategy parser (anchor + plain-text fallback) |
| Very large filings (>5MB) timeout | Low | Medium | 40-second timeout + error message |
| Section not found | Medium | Low | "(Section not found)" graceful message |
| EDGAR downtime | Low | High | Caching means second visit still works |
| LM wordlist incomplete | Medium | Low | Covers ~2 400 financial-specific terms; well-validated in literature |

---

## 10. Acceptance Criteria

- [ ] App launches with `streamlit run app.py` without errors
- [ ] JPMorgan Chase 10-K loads and displays MD&A tone score
- [ ] Multi-bank comparison renders tone bar for 3+ banks
- [ ] Risk theme heatmap displays when 2+ banks selected
- [ ] Full text expander shows raw section text
- [ ] Summary table shows conditional-colored tone columns
- [ ] Error messages display if EDGAR is unreachable
- [ ] No hardcoded financial values in app.py (all from edgar_fetcher/parser)

---

## 11. Release Timeline

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| v1.0 — Single bank, 10-K only | 2026-05-01 | Basic EDGAR fetch + section display |
| **v2.0 — Multi-bank, 10-K + 10-Q** | **2026-06-18** | **Full platform (this document)** |
| v2.1 — Trend charts over time | 2026-07-15 | Historical tone per bank |
| v3.0 — LLM summaries + alerts | 2026-09-01 | Claude API integration |

---

*Document maintained in `fin/tt/PRD.md`. Update version field on every revision.*
