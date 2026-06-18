# app.py — Financial Intelligence Platform: 10-K / 10-Q Analyzer
# Run with:  streamlit run app.py
# Fetches live SEC EDGAR filings, parses MD&A & Risk Disclosures,
# and performs Loughran-McDonald sentiment + risk theme analysis.

import streamlit as st
import pandas as pd

import edgar_fetcher as ef
import parser as fp
import analyzer as an
import charts as ch

# ─── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Intelligence Platform",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #3498db;
    }
    .positive { border-left-color: #2ecc71 !important; }
    .negative { border-left-color: #e74c3c !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
</style>
""", unsafe_allow_html=True)


# ─── Cached data fetchers ──────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching filing list from SEC EDGAR…")
def cached_filings(cik: str, form_type: str, count: int = 6) -> list[dict]:
    return ef.get_company_filings(cik, form_type=form_type, count=count)


@st.cache_data(ttl=3600, show_spinner="Downloading filing (may take 10–30 s)…")
def cached_html(cik: str, acc_nd: str, primary_doc: str) -> str:
    return ef.fetch_filing_html(cik, acc_nd, primary_doc)


@st.cache_data(ttl=3600, show_spinner="Parsing sections…")
def cached_sections(html: str, form_type: str) -> dict[str, str]:
    return fp.extract_sections(html, form_type)


@st.cache_data(ttl=3600, show_spinner="Running analysis…")
def cached_analysis(sections_frozen: tuple) -> dict[str, dict]:
    sections = dict(sections_frozen)
    return an.analyze_sections(sections)


# ─── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 Financial Intelligence Platform")
    st.caption("SEC EDGAR 10-K / 10-Q Analyzer")
    st.divider()

    st.subheader("Settings")
    selected_bank = st.selectbox(
        "Select Bank",
        options=list(ef.BANKS_CATALOG.keys()),
        index=0,
    )
    form_type = st.radio("Filing Type", ["10-K", "10-Q"], horizontal=True)
    num_filings = st.slider("Number of filings to load", 1, 8, 4)

    st.divider()

    # Bank info card
    info = ef.BANKS_CATALOG[selected_bank]
    st.markdown(f"**Ticker:** {info['ticker']}")
    st.markdown(f"**Sector:** {info['sector']}")
    st.markdown(f"**CIK:** {info['cik']}")
    st.caption(info["description"])

    st.divider()
    st.subheader("Compare Mode")
    compare_banks = st.multiselect(
        "Banks for cross-comparison",
        options=list(ef.BANKS_CATALOG.keys()),
        default=["JPMorgan Chase", "Bank of America", "Wells Fargo"],
        max_selections=6,
    )


# ─── Main area ─────────────────────────────────────────────────────
st.title(f"🏦 {selected_bank} — {form_type} Deep Analysis")

tab_single, tab_compare, tab_about = st.tabs([
    "📄 Single Filing Analysis",
    "📊 Multi-Bank Comparison",
    "ℹ️ About & Methodology",
])


# ═══════════════════════════════════════════════════════════════════
# TAB 1 — Single Filing Analysis
# ═══════════════════════════════════════════════════════════════════
with tab_single:
    cik = ef.BANKS_CATALOG[selected_bank]["cik"]

    # Load filings
    try:
        filings = cached_filings(cik, form_type, count=num_filings)
    except Exception as e:
        st.error(f"Could not reach SEC EDGAR: {e}")
        st.stop()

    if not filings:
        st.warning("No filings found for this bank and form type.")
        st.stop()

    # Filing selector
    filing_options = {f"{f['form']} — {f['date']}": f for f in filings}
    chosen_label = st.selectbox("Select Filing", list(filing_options.keys()))
    filing = filing_options[chosen_label]

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    col_meta1.metric("Form Type", filing["form"])
    col_meta2.metric("Filing Date", filing["date"])
    col_meta3.metric("Accession", filing["accession"])

    st.divider()

    # Load & parse
    try:
        html = cached_html(filing["cik"], filing["accession_nd"], filing["primary_doc"])
    except Exception as e:
        st.error(f"Could not download filing document: {e}")
        st.stop()

    sections = cached_sections(html, form_type)
    analysis = cached_analysis(tuple(sorted(sections.items())))

    # ── Section Metrics Row ────────────────────────────────────────
    st.subheader("Section Overview")
    mcols = st.columns(len(sections))
    section_labels = {"mda": "MD&A", "risk_factors": "Risk Factors", "market_risk": "Market Risk"}

    for i, (key, label) in enumerate(section_labels.items()):
        sec_an = analysis.get(key, {})
        sent   = sec_an.get("sentiment", {})
        tone   = sent.get("tone_pct", 0.0)
        wc     = sec_an.get("word_count", 0)
        found  = sec_an.get("found", False)

        with mcols[i]:
            status = "✅" if found else "❌"
            st.metric(
                label=f"{status} {label}",
                value=f"{wc:,} words",
                delta=f"Tone: {tone:+.2f}%",
                delta_color="normal" if tone >= 0 else "inverse",
            )

    st.divider()

    # ── Deep-dive tabs per section ─────────────────────────────────
    sec_tab_mda, sec_tab_risk, sec_tab_market = st.tabs([
        "📈 MD&A", "⚠️ Risk Factors", "📉 Market Risk"
    ])

    def render_section_detail(section_key: str, label: str, container):
        with container:
            sec_an = analysis.get(section_key, {})
            sent   = sec_an.get("sentiment", {})
            themes = sec_an.get("themes", [])
            kws    = sec_an.get("keywords", [])
            text   = sections.get(section_key, "")

            if not sec_an.get("found"):
                st.info(f"Section '{label}' was not found in this filing.")
                return

            # Sentiment metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Words",     f"{sent.get('total', 0):,}")
            c2.metric("Positive Words",  f"{sent.get('positive', 0):,}")
            c3.metric("Negative Words",  f"{sent.get('negative', 0):,}")
            tone = sent.get("tone_pct", 0.0)
            c4.metric("Tone Score",      f"{tone:+.2f}%",
                      delta="Optimistic" if tone > 0 else "Cautious",
                      delta_color="normal" if tone >= 0 else "inverse")

            st.divider()

            col_left, col_right = st.columns([1, 1])

            with col_left:
                if themes:
                    fig_radar = ch.risk_theme_radar(themes, selected_bank)
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.info("No risk themes detected in this section.")

            with col_right:
                if kws:
                    fig_kw = ch.keyword_bar(kws, selected_bank, label)
                    st.plotly_chart(fig_kw, use_container_width=True)

            st.divider()

            # Full text expander
            with st.expander(f"📄 Full {label} Text (excerpt — first 6 000 chars)", expanded=False):
                st.text(text[:6000] + ("…" if len(text) > 6000 else ""))

    render_section_detail("mda",          "MD&A",         sec_tab_mda)
    render_section_detail("risk_factors", "Risk Factors",  sec_tab_risk)
    render_section_detail("market_risk",  "Market Risk",   sec_tab_market)


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — Multi-Bank Comparison
# ═══════════════════════════════════════════════════════════════════
with tab_compare:
    if len(compare_banks) < 2:
        st.info("Select at least 2 banks in the sidebar to compare.")
    else:
        st.subheader(f"Multi-Bank Comparison — {form_type} (Most Recent)")

        # Fetch one filing per bank
        bank_data: dict[str, dict] = {}
        progress = st.progress(0, text="Loading filings…")
        for idx, bname in enumerate(compare_banks):
            bcik = ef.BANKS_CATALOG[bname]["cik"]
            try:
                bfilings = cached_filings(bcik, form_type, count=1)
                if bfilings:
                    bhtml  = cached_html(bcik, bfilings[0]["accession_nd"], bfilings[0]["primary_doc"])
                    bsecs  = cached_sections(bhtml, form_type)
                    ban    = cached_analysis(tuple(sorted(bsecs.items())))
                    bank_data[bname] = {
                        "filing":   bfilings[0],
                        "sections": bsecs,
                        "analysis": ban,
                    }
            except Exception:
                pass
            progress.progress((idx + 1) / len(compare_banks), text=f"Loaded: {bname}")
        progress.empty()

        if not bank_data:
            st.error("Could not load any filings. Check network connectivity.")
        else:
            # Tone comparison
            tone_rows = an.compare_tone_across_banks(
                {bn: bd["analysis"] for bn, bd in bank_data.items()},
                section="mda",
            )
            fig_tone = ch.sentiment_tone_bar(tone_rows, "MD&A Tone Score — Most Recent 10-K/10-Q")
            st.plotly_chart(fig_tone, use_container_width=True)

            st.divider()

            # Risk theme heatmap
            all_themes_set: set[str] = set()
            for bd in bank_data.values():
                for sec_key in ["mda", "risk_factors"]:
                    for t, _ in bd["analysis"].get(sec_key, {}).get("themes", []):
                        all_themes_set.add(t)

            theme_list = sorted(all_themes_set)
            if theme_list:
                matrix: list[list[float]] = []
                bnames: list[str] = []
                for bname, bd in bank_data.items():
                    bnames.append(bname)
                    row: list[float] = []
                    for theme in theme_list:
                        count = 0
                        for sec_key in ["mda", "risk_factors"]:
                            themes_an = dict(bd["analysis"].get(sec_key, {}).get("themes", []))
                            count += themes_an.get(theme, 0)
                        row.append(float(count))
                    matrix.append(row)

                fig_heat = ch.multi_bank_heatmap(bnames, theme_list, matrix)
                st.plotly_chart(fig_heat, use_container_width=True)

            st.divider()

            # Summary table
            st.subheader("Comparison Summary Table")
            rows_summary = []
            for bname, bd in bank_data.items():
                mda_an    = bd["analysis"].get("mda", {})
                risk_an   = bd["analysis"].get("risk_factors", {})
                rows_summary.append({
                    "Bank":             bname,
                    "Filing Date":      bd["filing"]["date"],
                    "MD&A Words":       mda_an.get("word_count", 0),
                    "MD&A Tone (%)":    mda_an.get("sentiment", {}).get("tone_pct", 0.0),
                    "Risk Words":       risk_an.get("word_count", 0),
                    "Risk Tone (%)":    risk_an.get("sentiment", {}).get("tone_pct", 0.0),
                    "Top Risk Theme":   bd["analysis"].get("risk_factors", {}).get("themes", [("—", 0)])[0][0],
                })
            df_summary = pd.DataFrame(rows_summary)
            st.dataframe(
                df_summary.style
                    .background_gradient(subset=["MD&A Tone (%)", "Risk Tone (%)"], cmap="RdYlGn")
                    .format({"MD&A Tone (%)": "{:+.2f}", "Risk Tone (%)": "{:+.2f}",
                             "MD&A Words": "{:,}", "Risk Words": "{:,}"}),
                use_container_width=True,
                hide_index=True,
            )


# ═══════════════════════════════════════════════════════════════════
# TAB 3 — About
# ═══════════════════════════════════════════════════════════════════
with tab_about:
    st.subheader("About this Platform")
    st.markdown("""
    ### Financial Intelligence Platform — 10-K / 10-Q Analyzer

    **What it does**
    - Connects live to the [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar) REST API (no API key required)
    - Downloads and parses annual (10-K) and quarterly (10-Q) filings for 12 major US banks
    - Extracts three key sections: **MD&A** (Item 7 / Item 2), **Risk Factors** (Item 1A), **Market Risk** (Item 7A / Item 3)
    - Applies **Loughran-McDonald financial sentiment analysis** to score the tone of each section
    - Identifies **8 risk theme categories** using keyword matching
    - Enables **multi-bank comparison** via heatmaps, tone bars, and summary tables

    ---

    ### Sentiment Methodology
    Based on the **Loughran-McDonald (2011)** wordlist designed specifically for financial documents
    (as opposed to general sentiment tools like VADER, which miscategorize finance-specific terms).

    **Tone Score** = (Positive − Negative) / Total Words × 100

    A positive tone suggests management confidence; a highly negative tone indicates elevated risk
    disclosure or cautionary language.

    ---

    ### Covered Banks

    | Bank | Ticker | Sector |
    |------|--------|--------|
    | JPMorgan Chase | JPM | Money-Center |
    | Bank of America | BAC | Money-Center |
    | Wells Fargo | WFC | Money-Center |
    | Citigroup | C | Money-Center |
    | Goldman Sachs | GS | Investment |
    | Morgan Stanley | MS | Investment |
    | U.S. Bancorp | USB | Regional |
    | PNC Financial | PNC | Regional |
    | Truist Financial | TFC | Regional |
    | Capital One | COF | Consumer |
    | Charles Schwab | SCHW | Brokerage |
    | American Express | AXP | Consumer Credit |

    ---

    ### Data Source
    All data is fetched in real-time from [SEC EDGAR](https://www.sec.gov).
    Results are cached for 1 hour per session.
    """)
