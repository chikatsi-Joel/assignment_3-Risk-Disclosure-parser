# charts.py — Plotly visualization factory
# All functions receive data as parameters; no imports of edgar_fetcher/analyzer.

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


PALETTE = px.colors.qualitative.Set3


def sentiment_tone_bar(rows: list[dict], title: str = "MD&A Tone Score by Bank") -> go.Figure:
    """
    Horizontal bar chart of tone_pct per bank.
    rows: list of {bank, tone, positive, negative, words}
    """
    df = pd.DataFrame(rows).sort_values("tone")
    colors = ["#e74c3c" if t < 0 else "#2ecc71" for t in df["tone"]]

    fig = go.Figure(go.Bar(
        x=df["tone"],
        y=df["bank"],
        orientation="h",
        marker_color=colors,
        text=[f"{t:+.2f}%" for t in df["tone"]],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Tone: %{x:.2f}%<br>"
            "Positive words: %{customdata[0]}<br>"
            "Negative words: %{customdata[1]}<extra></extra>"
        ),
        customdata=list(zip(df["positive"], df["negative"])),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Tone Score (% of total words)",
        yaxis_title="",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(350, len(df) * 48),
        margin=dict(l=160, r=60, t=50, b=40),
        xaxis=dict(zeroline=True, zerolinecolor="#aaa"),
    )
    return fig


def risk_theme_radar(themes: list[tuple[str, int]], bank_name: str) -> go.Figure:
    """Spider/radar chart of risk theme mention counts."""
    if not themes:
        return go.Figure()

    labels = [t[0] for t in themes]
    values = [t[1] for t in themes]
    # Close the polygon
    labels += [labels[0]]
    values += [values[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=labels,
        fill="toself",
        fillcolor="rgba(52, 152, 219, 0.25)",
        line=dict(color="#3498db", width=2),
        name=bank_name,
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, showticklabels=True)),
        title=f"Risk Theme Profile — {bank_name}",
        showlegend=False,
        height=420,
    )
    return fig


def keyword_bar(keywords: list[tuple[str, int]], bank_name: str, section: str) -> go.Figure:
    """Top-N keyword frequency bar chart."""
    if not keywords:
        return go.Figure()
    words, counts = zip(*keywords[:20])
    fig = go.Figure(go.Bar(
        x=counts[::-1],
        y=words[::-1],
        orientation="h",
        marker_color="#3498db",
    ))
    fig.update_layout(
        title=f"Top Keywords — {bank_name} / {section.upper()}",
        xaxis_title="Frequency",
        yaxis_title="",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=460,
        margin=dict(l=140, r=30, t=50, b=40),
    )
    return fig


def multi_bank_heatmap(
    bank_names: list[str],
    theme_names: list[str],
    matrix: list[list[float]],
) -> go.Figure:
    """Heatmap of risk-theme intensity across banks."""
    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=theme_names,
        y=bank_names,
        colorscale="YlOrRd",
        hovertemplate="Bank: %{y}<br>Theme: %{x}<br>Mentions: %{z}<extra></extra>",
        colorbar=dict(title="Mentions"),
    ))
    fig.update_layout(
        title="Risk Theme Intensity Heatmap — Multi-Bank Comparison",
        xaxis=dict(tickangle=-30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(350, len(bank_names) * 42 + 120),
        margin=dict(l=160, r=30, t=60, b=80),
    )
    return fig


def section_size_bar(stats: dict[str, dict[str, dict]], section: str = "mda") -> go.Figure:
    """Bar chart comparing section word counts across banks."""
    rows = []
    for bank, sec_stats in stats.items():
        wc = sec_stats.get(section, {}).get("word_count", 0)
        rows.append({"bank": bank, "words": wc})

    df = pd.DataFrame(rows).sort_values("words", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["bank"],
        y=df["words"],
        marker_color="#9b59b6",
        text=df["words"],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Section Size Comparison — {section.upper()} (word count)",
        xaxis_title="Bank",
        yaxis_title="Words",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=400,
        margin=dict(l=40, r=30, t=60, b=80),
    )
    return fig


def filing_timeline(filings_by_bank: dict[str, list[dict]]) -> go.Figure:
    """Scatter timeline of all filings per bank."""
    fig = go.Figure()
    for i, (bank, filings) in enumerate(filings_by_bank.items()):
        dates = [f["date"] for f in filings]
        forms = [f["form"] for f in filings]
        fig.add_trace(go.Scatter(
            x=dates,
            y=[bank] * len(dates),
            mode="markers+text",
            text=forms,
            textposition="top center",
            marker=dict(size=12, color=PALETTE[i % len(PALETTE)]),
            name=bank,
        ))
    fig.update_layout(
        title="Filing History Timeline",
        xaxis_title="Filing Date",
        yaxis_title="",
        height=max(400, len(filings_by_bank) * 50 + 100),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        margin=dict(l=160, r=30, t=60, b=40),
    )
    return fig
