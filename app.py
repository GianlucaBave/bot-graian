import os
import json
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from anthropic import Anthropic

# ── Page config ─────────────────────────────────────────────────────
st.set_page_config(page_title="Graian Capital — Loan Portfolio Intelligence", layout="wide")

# ── Custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }

    /* Force light mode everywhere */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
    }

    [data-testid="stChatMessage"], [data-testid="stExpander"] {
        background-color: transparent !important;
        color: #1E293B !important;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] td,
    [data-testid="stMarkdownContainer"] th,
    [data-testid="stMarkdownContainer"] strong {
        color: #1E293B !important;
    }

    [data-testid="stExpander"] summary span {
        color: #1E293B !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
    }

    [data-testid="stBottomBlockContainer"] {
        background-color: #F8FAFC !important;
    }

    /* Tables */
    table, th, td {
        color: #1E293B !important;
        border-color: #E2E8F0 !important;
    }

    /* Layout — tighter, more professional spacing */
    .stApp [data-testid="stAppViewContainer"] > section > div {
        max-width: 900px;
        margin: 0 auto;
        padding-top: 0 !important;
    }

    /* Remove top padding from main block */
    .block-container {
        padding-top: 1rem !important;
    }

    h1 {
        color: #0D9488 !important;
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-top: 0.5rem !important;
    }

    /* Chat messages — compact like ChatGPT/Perplexity */
    [data-testid="stChatMessage"] {
        padding: 0.75rem 0 !important;
        border: none !important;
        border-bottom: 1px solid #F1F5F9 !important;
        border-radius: 0 !important;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    /* Plotly charts — proper height */
    .stPlotlyChart {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .stPlotlyChart > div {
        height: 360px !important;
    }

    .thinking-block {
        background-color: #F1F5F9 !important;
        border-left: 3px solid #0D9488;
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        color: #475569 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Title ───────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="color:#0D9488; margin-bottom:0;">GRAIAN CAPITAL — Loan Portfolio Intelligence</h1>'
    '<p style="color:#64748B; font-size:0.95rem; margin-top:0;">AI-powered exposure analytics, LTV monitoring & risk insights</p>',
    unsafe_allow_html=True,
)

# ── Plotly layout template ──────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#1E293B", family="Inter, sans-serif", size=12),
    title_font=dict(color="#0F172A", size=13),
    xaxis=dict(gridcolor="#E2E8F0", linecolor="#CBD5E1"),
    yaxis=dict(gridcolor="#E2E8F0", linecolor="#CBD5E1"),
    colorway=["#0D9488", "#F59E0B", "#3B82F6", "#EF4444"],
    margin=dict(l=50, r=20, t=36, b=36),
    legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="#E2E8F0"),
    height=360,
)

# ── Load data ───────────────────────────────────────────────────────
@st.cache_data
def load_data():
    txn = pd.read_csv("clean_transactions.csv", parse_dates=["transaction-date"])
    prod = pd.read_csv("clean_products.csv")
    port = pd.read_csv("clean_portfolios.csv")
    fx = pd.read_csv("clean_fx.csv", parse_dates=["price-date"])
    prices = pd.read_csv("clean_prices.csv", parse_dates=["price-date"])
    return txn, prod, port, fx, prices

transactions, products, portfolios, fx, prices = load_data()

# ── Merge helper ────────────────────────────────────────────────────
@st.cache_data
def get_loan_transactions():
    loan_products = products[products["product-type"] == "LN"]
    merged = transactions.merge(loan_products, on="product-code", how="inner")
    return merged

loan_txn = get_loan_transactions()

# ── Tool implementations ────────────────────────────────────────────

def tool_get_loan_exposure(portfolio_code=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No loan transactions found for given filters."})
    df["exposure"] = df["transaction-quantity"] * df["transaction-price"]
    result = df.groupby("portfolio-code")["exposure"].sum().reset_index()
    result["exposure"] = result["exposure"].round(2)
    total = result["exposure"].sum()
    rows = result.to_dict(orient="records")
    return json.dumps({"portfolios": rows, "total_exposure": round(total, 2)})


def tool_get_loan_exposure_by_issuer(portfolio_code=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No loan transactions found."})
    df["exposure"] = df["transaction-quantity"] * df["transaction-price"]
    result = df.groupby("product-issuer-code")["exposure"].sum().reset_index()
    result = result.sort_values("exposure", ascending=False)
    result["exposure"] = result["exposure"].round(2)
    return json.dumps({"issuers": result.to_dict(orient="records")})


def tool_get_ltv(portfolio_code=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No loan transactions found."})
    # Filter outliers: ratio > 0 AND ratio < 10
    df = df[(df["loan-property-value-ratio"] > 0) & (df["loan-property-value-ratio"] < 10)]
    df["ltv"] = 1.0 / df["loan-property-value-ratio"]
    result = df.groupby("portfolio-code")["ltv"].mean().reset_index()
    result["ltv"] = result["ltv"].round(4)
    return json.dumps({"portfolios": result.to_dict(orient="records")})


def tool_get_portfolio_value(portfolio_code, date_to):
    dt = pd.Timestamp(date_to)
    valid = prices[prices["price-date"] <= dt].sort_values("price-date", ascending=False)
    if valid.empty:
        return json.dumps({"error": "No price data available before that date."})
    row = valid.iloc[0]
    col_map = {"P1-EUR": "P1-EUR", "P2-USD": "P2-USD"}
    col = col_map.get(portfolio_code)
    if col is None:
        return json.dumps({"error": f"Unknown portfolio code: {portfolio_code}"})
    value = row[col]
    if pd.isna(value):
        return json.dumps({
            "portfolio_code": portfolio_code,
            "date": str(row["price-date"].date()),
            "value": None,
            "note": "NAV not available for this date (null)."
        })
    return json.dumps({
        "portfolio_code": portfolio_code,
        "date": str(row["price-date"].date()),
        "value": round(float(value), 2)
    })


def tool_get_loan_exposure_pct(portfolio_code, date_to):
    exp_raw = json.loads(tool_get_loan_exposure(portfolio_code, date_to))
    val_raw = json.loads(tool_get_portfolio_value(portfolio_code, date_to))
    if "error" in exp_raw or "error" in val_raw:
        return json.dumps({"error": exp_raw.get("error") or val_raw.get("error")})
    if val_raw["value"] is None or val_raw["value"] == 0:
        return json.dumps({"error": "Portfolio value is null or zero, cannot compute percentage."})
    exposure = exp_raw["total_exposure"]
    value = val_raw["value"]
    pct = round((exposure / value) * 100, 2)
    return json.dumps({
        "portfolio_code": portfolio_code,
        "date_to": date_to,
        "loan_exposure": exposure,
        "portfolio_value": value,
        "exposure_pct": pct
    })


def tool_get_fx_rate(date):
    dt = pd.Timestamp(date)
    valid = fx[fx["price-date"] <= dt].sort_values("price-date", ascending=False)
    if valid.empty:
        return json.dumps({"error": "No FX data available before that date."})
    row = valid.iloc[0]
    return json.dumps({
        "date": str(row["price-date"].date()),
        "EURUSD": round(float(row["EURUSD"]), 4)
    })


def tool_plot_exposure_trend(portfolio_code=None, date_from=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_from:
        df = df[df["transaction-date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No data for the given filters."}), None
    df["exposure"] = df["transaction-quantity"] * df["transaction-price"]
    fig = go.Figure()
    for pf in sorted(df["portfolio-code"].unique()):
        pf_df = df[df["portfolio-code"] == pf].sort_values("transaction-date")
        pf_df["cumulative"] = pf_df["exposure"].cumsum()
        fig.add_trace(go.Scatter(
            x=pf_df["transaction-date"], y=pf_df["cumulative"],
            mode="lines", name=pf
        ))
    fig.update_layout(**PLOTLY_LAYOUT, title="Cumulative Net Loan Exposure Over Time")
    fig.update_yaxes(title_text="Exposure")
    fig.update_xaxes(title_text="Date")
    return json.dumps({"status": "chart_rendered"}), fig


def tool_plot_issuer_breakdown(portfolio_code=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No data found."}), None
    df["exposure"] = df["transaction-quantity"] * df["transaction-price"]
    grouped = df.groupby("product-issuer-code")["exposure"].sum().reset_index()
    grouped = grouped[grouped["exposure"] > 0].sort_values("exposure", ascending=True)
    if grouped.empty:
        return json.dumps({"error": "No positive exposures found."}), None
    fig = go.Figure(go.Bar(
        x=grouped["exposure"], y=grouped["product-issuer-code"],
        orientation="h",
        marker_color="#0D9488"
    ))
    title = "Loan Exposure by Issuer"
    if portfolio_code:
        title += f" — {portfolio_code}"
    fig.update_layout(**PLOTLY_LAYOUT, title=title)
    fig.update_xaxes(title_text="Exposure")
    return json.dumps({"status": "chart_rendered"}), fig


def tool_plot_ltv_by_issuer(portfolio_code=None, date_to=None):
    df = loan_txn.copy()
    if portfolio_code:
        df = df[df["portfolio-code"] == portfolio_code]
    if date_to:
        df = df[df["transaction-date"] <= pd.Timestamp(date_to)]
    if df.empty:
        return json.dumps({"error": "No data found."}), None
    df = df[(df["loan-property-value-ratio"] > 0) & (df["loan-property-value-ratio"] < 10)]
    df["ltv"] = 1.0 / df["loan-property-value-ratio"]
    grouped = df.groupby("product-issuer-code")["ltv"].mean().reset_index()
    grouped = grouped.sort_values("ltv", ascending=False)
    fig = go.Figure(go.Bar(
        x=grouped["product-issuer-code"], y=grouped["ltv"],
        marker_color="#0D9488"
    ))
    fig.add_hline(y=0.80, line_dash="dash", line_color="#EF4444",
                  annotation_text="80% LTV threshold")
    title = "LTV by Issuer"
    if portfolio_code:
        title += f" — {portfolio_code}"
    fig.update_layout(**PLOTLY_LAYOUT, title=title)
    fig.update_yaxes(title_text="LTV")
    return json.dumps({"status": "chart_rendered"}), fig


def tool_get_data_quality_summary():
    summary = """Data Quality Summary:
1. 1 transaction with price = 0 → corrected to 1 during cleaning
2. 5 null FX values → filled forward using previous valid rate
3. 18 legacy transaction codes (not starting with TR-) → tagged as LEGACY in source-system column
4. PR-P4N4N has LPVR outlier of 33.33 → excluded from LTV calculations (filter: ratio < 10)
5. P2-USD shows zero values May–Aug 2021 → replaced with null (portfolio was pre-funding)
6. P1-EUR July 2021 NAV dip of -49.5% → retained in data but flagged as anomalous"""
    return json.dumps({"summary": summary})


# ── Tool dispatch ───────────────────────────────────────────────────
TOOL_DISPATCH = {
    "get_loan_exposure": tool_get_loan_exposure,
    "get_loan_exposure_by_issuer": tool_get_loan_exposure_by_issuer,
    "get_ltv": tool_get_ltv,
    "get_portfolio_value": tool_get_portfolio_value,
    "get_loan_exposure_pct": tool_get_loan_exposure_pct,
    "get_fx_rate": tool_get_fx_rate,
    "plot_exposure_trend": tool_plot_exposure_trend,
    "plot_issuer_breakdown": tool_plot_issuer_breakdown,
    "plot_ltv_by_issuer": tool_plot_ltv_by_issuer,
    "get_data_quality_summary": tool_get_data_quality_summary,
}

PLOT_TOOLS = {"plot_exposure_trend", "plot_issuer_breakdown", "plot_ltv_by_issuer"}

# ── Tool definitions for Claude ─────────────────────────────────────
TOOLS = [
    {
        "name": "get_loan_exposure",
        "description": "Get total loan exposure (sum of quantity × price for LN products) by portfolio. Optionally filter by portfolio_code and/or date_to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code, e.g. P1-EUR or P2-USD. Omit for all portfolios."},
                "date_to": {"type": "string", "description": "End date filter in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "get_loan_exposure_by_issuer",
        "description": "Get loan exposure grouped by issuer, sorted descending. Optionally filter by portfolio_code and/or date_to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code. Omit for all portfolios."},
                "date_to": {"type": "string", "description": "End date filter in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "get_ltv",
        "description": "Get average LTV (loan-to-value = 1/ratio) per portfolio, excluding outlier ratios (ratio > 0 AND ratio < 10). Optionally filter by portfolio_code and/or date_to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code. Omit for all."},
                "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "get_portfolio_value",
        "description": "Get most recent month-end NAV for a portfolio at or before date_to from clean_prices.csv.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code: P1-EUR or P2-USD."},
                "date_to": {"type": "string", "description": "Date in YYYY-MM-DD format."}
            },
            "required": ["portfolio_code", "date_to"]
        }
    },
    {
        "name": "get_loan_exposure_pct",
        "description": "Get loan exposure as a percentage of portfolio NAV.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code: P1-EUR or P2-USD."},
                "date_to": {"type": "string", "description": "Date in YYYY-MM-DD format."}
            },
            "required": ["portfolio_code", "date_to"]
        }
    },
    {
        "name": "get_fx_rate",
        "description": "Get the most recent EURUSD FX rate at or before the given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."}
            },
            "required": ["date"]
        }
    },
    {
        "name": "plot_exposure_trend",
        "description": "Generate a Plotly line chart of cumulative net loan exposure over time, one line per portfolio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code. Omit for all."},
                "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "plot_issuer_breakdown",
        "description": "Generate a Plotly horizontal bar chart of loan exposure by issuer, sorted descending, excluding zero/negative exposures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code. Omit for all."},
                "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "plot_ltv_by_issuer",
        "description": "Generate a Plotly bar chart of average LTV by issuer with a horizontal reference line at 0.80.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio_code": {"type": "string", "description": "Portfolio code. Omit for all."},
                "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format."}
            },
            "required": []
        }
    },
    {
        "name": "get_data_quality_summary",
        "description": "Returns a summary of key data quality findings and corrections applied during cleaning.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]

# ── System prompt ───────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior risk analyst at Graian Capital Management, a Swiss independent asset manager \
based in Lugano. You think like an experienced risk professional and portfolio manager.

You have access to two loan portfolios: P1-EUR and P2-USD, spanning May 2021 to June 2022. \
You can query loan exposure, LTV ratios, portfolio NAV, FX rates, and generate charts.

Risk framework you apply naturally (don't list these unless relevant):
- Concentration risk: flag single issuer >15% or top 3 >50% of exposure
- LTV: 80% threshold, rising LTV = deteriorating collateral coverage
- Exposure vs NAV: flag if exposure > 100% of NAV
- FX mismatch between EUR/USD portfolios
- Data quality caveats when relevant

Response style:
- Be concise and professional. Answer in 3-8 sentences for simple questions, longer only for complex analysis.
- Lead with the key finding, support with data, close with one actionable takeaway.
- Use precise numbers and basis points for small changes.
- Do NOT write ASCII art, fake tables, implementation plans, governance frameworks, or compliance checklists.
- Do NOT roleplay organizational processes. Stick to data analysis.
- If a question is about the dashboard itself (code, implementation), answer briefly — you are an analyst, not a developer."""

# ── Session state ───────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "figures" not in st.session_state:
    st.session_state.figures = {}  # msg_index -> list of figures

# ── Render chat history ─────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if i in st.session_state.figures:
            for j, fig in enumerate(st.session_state.figures[i]):
                st.plotly_chart(fig, use_container_width=True, key=f"hist_{i}_{j}")

# ── Chat input ──────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about portfolio data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build API messages
    api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    figures_for_msg = []

    # Run the agent loop outside of chat_message to avoid spinner overlay on history
    thinking_steps = []
    with st.status("Thinking...", expanded=True) as status:
        # Agentic tool-use loop
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=api_messages,
        )

        # Process tool calls in a loop
        while response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    fn = TOOL_DISPATCH[tool_name]

                    # Log thinking step
                    input_summary = ", ".join(f"{k}={v}" for k, v in tool_input.items()) if tool_input else "no filters"
                    step_text = f"Calling **{tool_name}**({input_summary})"
                    thinking_steps.append(step_text)
                    st.markdown(step_text)

                    if tool_name in PLOT_TOOLS:
                        result_str, fig = fn(**tool_input)
                        if fig is not None:
                            figures_for_msg.append(fig)
                    else:
                        result_str = fn(**tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
                elif hasattr(block, "text") and block.text.strip():
                    thinking_steps.append(block.text.strip())
                    st.markdown(block.text.strip())

            # Append assistant response + tool results to messages
            api_messages.append({"role": "assistant", "content": response.content})
            api_messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=api_messages,
            )

        # Extract final text
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        status.update(label="Reasoning process", state="complete", expanded=False)

    with st.chat_message("assistant"):
        st.markdown(final_text)
        msg_idx = len(st.session_state.messages)
        for j, fig in enumerate(figures_for_msg):
            st.plotly_chart(fig, use_container_width=True, key=f"new_{msg_idx}_{j}")

    # Save to session state
    st.session_state.messages.append({"role": "assistant", "content": final_text})
    if figures_for_msg:
        st.session_state.figures[msg_idx] = figures_for_msg
