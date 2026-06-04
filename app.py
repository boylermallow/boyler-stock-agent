import base64
import hashlib
import html
import json
import math
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf


APP_DIR = Path(__file__).parent
PORTFOLIO_FILE = APP_DIR / "my_investments.json"
CATEGORIES_FILE = APP_DIR / "investment_categories.json"
LOGO_DIR = APP_DIR / "assets" / "logos"
DEFAULT_CATEGORY = "Watchlist"
NY_TZ = ZoneInfo("America/New_York")

REFRESH_SECONDS = 5
QUOTE_TTL = 5
SCORE_TTL = 10
COMPANY_TTL = 24 * 60 * 60
SEARCH_TTL = 24 * 60 * 60
NEWS_TTL = 30 * 60

SECTOR_STOCKS = {
    "Chips": {
        "High Risk Reward": ["AMD", "MRVL", "ARM", "COHR", "SNDK", "RMBS", "ON", "WOLF", "LSCC", "AMBA"],
        "Balanced": ["NVDA", "AVGO", "TSM", "AMAT", "LRCX", "KLAC", "QCOM", "TXN", "MU", "ADI"],
        "Low Risk": ["AVGO", "TXN", "ADI", "INTC", "QCOM", "NXPI", "MCHP", "ASML", "TER", "MPWR"],
    },
    "Software": {
        "High Risk Reward": ["PLTR", "CRWD", "DDOG", "SNOW", "PATH", "NET", "MDB", "AI", "S", "U"],
        "Balanced": ["MSFT", "NOW", "CRM", "ADBE", "ORCL", "PANW", "INTU", "SHOP", "TEAM", "WDAY"],
        "Low Risk": ["MSFT", "ORCL", "ADBE", "INTU", "SAP", "IBM", "ADP", "ACN", "CDNS", "SNPS"],
    },
    "Space": {
        "High Risk Reward": ["RKLB", "ASTS", "LUNR", "SPIR", "BKSY", "SIDU", "SATL", "RDW", "IRDM", "VSAT"],
        "Balanced": ["LMT", "NOC", "BA", "RTX", "HON", "GD", "TXT", "TDG", "HEI", "LDOS"],
        "Low Risk": ["LMT", "NOC", "RTX", "HON", "GD", "TDG", "HEI", "LDOS", "LHX", "BA"],
    },
    "AI & Data": {
        "High Risk Reward": ["AI", "SOUN", "BBAI", "PLTR", "IONQ", "RXRX", "PATH", "UPST", "SMCI", "ESTC"],
        "Balanced": ["MSFT", "NVDA", "GOOGL", "META", "AMZN", "CRM", "SNOW", "NOW", "ORCL", "IBM"],
        "Low Risk": ["MSFT", "GOOGL", "AMZN", "IBM", "ORCL", "ACN", "ADP", "INTU", "CDNS", "SNPS"],
    },
    "Energy": {
        "High Risk Reward": ["ENPH", "SEDG", "RUN", "FSLR", "TE", "PLUG", "BE", "NOVA", "ARRY", "QS"],
        "Balanced": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "FANG"],
        "Low Risk": ["XOM", "CVX", "COP", "EOG", "MPC", "PSX", "VLO", "KMI", "OKE", "WMB"],
    },
}

SECTOR_PROXIES = {
    "Chips": "SMH",
    "Software": "IGV",
    "Space": "ARKX",
    "AI & Data": "BOTZ",
    "Energy": "XLE",
}

SEARCH_OVERRIDES = {
    "SOFI": ("SOFI", "SoFi Technologies"),
    "SOFI TECHNOLOGIES": ("SOFI", "SoFi Technologies"),
    "T1 ENERGY": ("TE", "T1 Energy"),
    "TE": ("TE", "T1 Energy"),
    "SERVICENOW": ("NOW", "ServiceNow"),
    "NOW": ("NOW", "ServiceNow"),
    "SANDISK": ("SNDK", "SanDisk"),
}

COMPANY_DOMAINS = {
    "AAPL": "apple.com",
    "AMD": "amd.com",
    "AMZN": "amazon.com",
    "ARM": "arm.com",
    "AVGO": "broadcom.com",
    "COHR": "coherent.com",
    "GOOG": "abc.xyz",
    "GOOGL": "abc.xyz",
    "IBM": "ibm.com",
    "LLY": "lilly.com",
    "META": "meta.com",
    "MRVL": "marvell.com",
    "MSFT": "microsoft.com",
    "NOK": "nokia.com",
    "NOW": "servicenow.com",
    "NVDA": "nvidia.com",
    "PLTR": "palantir.com",
    "SHOP": "shopify.com",
    "SNDK": "sandisk.com",
    "SOFI": "sofi.com",
    "STX": "seagate.com",
    "TE": "t1energy.com",
    "TSLA": "tesla.com",
    "TSM": "tsmc.com",
}


st.set_page_config(page_title="Agent 101", layout="wide", page_icon="📈")


def css():
    st.markdown(
        """
        <style>
        :root {
            --bg: #090d14;
            --panel: #101722;
            --panel-2: #151b26;
            --line: rgba(255,255,255,0.12);
            --text: #f7f8fb;
            --muted: rgba(255,255,255,0.62);
            --green: #00d36f;
            --red: #ff4655;
            --orange: #ffb020;
            --blue: #2f7df6;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--bg);
            color: var(--text);
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] *,
        .stApp,
        .stApp * {
            transition: none !important;
            animation-duration: 0s !important;
        }
        .stale,
        [class*="stale"],
        [class*="Stale"],
        [data-stale="true"],
        [data-testid="stExpander"],
        [data-testid="stExpander"] *,
        details,
        details *,
        summary,
        body [style*="opacity"],
        body [style*="filter"],
        [data-testid="stAppViewContainer"] [style*="opacity"],
        [data-testid="stAppViewContainer"] [style*="filter"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
            animation: none !important;
        }
        [data-testid="stElementContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"],
        [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"],
        [data-testid="stDataFrame"],
        .element-container,
        .stMarkdown,
        .stDataFrame,
        .stButton,
        .stSelectbox,
        .stTextInput {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
            animation: none !important;
        }
        [data-testid="stHeader"] { background: transparent; }
        .block-container { padding-top: 1.25rem; max-width: 1500px; }
        h1, h2, h3, label, p, div { letter-spacing: 0 !important; }
        div[data-testid="stMetricValue"] { color: var(--text); }
        div[data-testid="stMetricDelta"] { border-radius: 999px; width: fit-content; padding: 2px 10px; }
        div[data-testid="stButton"] button { white-space: nowrap; min-width: fit-content; }
        .top-nav {
            display: flex; gap: 10px; align-items: center; margin: 8px 0 18px;
            border-bottom: 1px solid var(--line); padding-bottom: 12px;
        }
        .brand-mark {
            width: 36px; height: 36px; border-radius: 10px;
            display: grid; place-items: center; font-weight: 900;
            color: white; background: linear-gradient(135deg, #0cc17a, #2f7df6);
            box-shadow: 0 0 0 1px rgba(255,255,255,0.16) inset;
        }
        .brand-name { font-weight: 900; font-size: 1.05rem; margin-right: 12px; }
        .nav-pill {
            display: inline-flex; align-items: center; justify-content: center;
            border: 1px solid var(--line); border-radius: 999px; padding: 8px 14px;
            color: var(--muted); text-decoration: none; font-weight: 800;
        }
        .nav-pill.active { color: white; background: #172033; border-color: rgba(47,125,246,0.55); }
        .card {
            background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
            padding: 16px; margin-bottom: 14px;
        }
        .signal-card {
            background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
            padding: 18px; min-height: 176px;
        }
        .signal-label { color: var(--muted); font-size: 0.82rem; font-weight: 900; text-transform: uppercase; }
        .signal-main { font-size: 2.25rem; font-weight: 950; margin: 6px 0; line-height: 1; }
        .score-row {
            height: 36px; display: flex; align-items: center; border-radius: 8px;
            padding: 0 12px; margin: 7px 0; font-weight: 850;
        }
        .stock-line {
            display: flex; align-items: center; gap: 9px; min-width: 0;
            background: #0f1625; border: 1px solid rgba(255,255,255,0.10);
            border-radius: 8px; padding: 7px 9px; margin: 7px 0;
        }
        .stock-line .ticker { color: white; font-weight: 950; white-space: nowrap; }
        .stock-line .name {
            color: rgba(255,255,255,0.66); white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis; min-width: 0;
        }
        .stock-price {
            margin-left: auto; display: flex; align-items: center; gap: 10px;
            white-space: nowrap; font-weight: 900;
        }
        .stock-price .price { color: white; }
        .stock-price .change {
            border-radius: 999px; padding: 3px 9px; font-size: 0.86rem;
            color: #06130c;
        }
        .stock-price .change.up { background: #20d672; }
        .stock-price .change.down { background: #ff5362; color: white; }
        .stock-price .change.flat { background: #ffbd45; }
        .trade-stock-cell {
            display: flex; align-items: center; gap: 10px; min-width: 0;
            font-weight: 950; color: white;
        }
        .trade-stock-cell .trade-name {
            color: rgba(255,255,255,0.58); font-size: 0.84rem;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .stock-table {
            width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px;
            overflow: hidden; border-radius: 8px;
        }
        .stock-table th {
            color: rgba(255,255,255,0.58); font-size: 0.78rem; text-transform: uppercase;
            text-align: left; padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
        }
        .stock-table td {
            padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.08);
            vertical-align: middle; color: white;
        }
        .stock-table tr:last-child td { border-bottom: 0; }
        .stock-table .logo-cell { width: 44px; }
        .stock-table .ticker-cell { width: 96px; font-weight: 950; }
        .stock-table .company-cell {
            color: rgba(255,255,255,0.68); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .stock-table .price-cell { width: 120px; font-weight: 900; text-align: right; }
        .stock-table .today-cell { width: 110px; text-align: right; }
        .today-pill {
            display: inline-flex; border-radius: 999px; padding: 4px 9px;
            font-weight: 900; font-size: 0.86rem; color: #06130c;
        }
        .today-pill.up { background: #20d672; }
        .today-pill.down { background: #ff5362; color: white; }
        .today-pill.flat { background: #ffbd45; }
        .edit-cell { width: 92px; }
        .portfolio-header {
            color: rgba(255,255,255,0.58); font-size: 0.78rem; text-transform: uppercase;
            font-weight: 900; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.12);
        }
        .portfolio-cell {
            min-height: 48px; display: flex; align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08); overflow: hidden;
        }
        .portfolio-ticker { color: white; font-weight: 950; }
        .portfolio-company {
            color: rgba(255,255,255,0.68); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .portfolio-price { color: white; font-weight: 950; justify-content: flex-end; }
        .portfolio-today { justify-content: flex-end; }
        .portfolio-edit { justify-content: flex-end; }
        .portfolio-edit div[data-testid="stButton"] button,
        .portfolio-edit button { min-width: 74px; white-space: nowrap; }
        .logo-badge {
            width: 34px; height: 34px; border-radius: 8px; flex: 0 0 34px;
            display: grid; place-items: center; overflow: hidden;
            background: #202a3b; color: white; font-weight: 950; font-size: 0.84rem;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.12) inset;
        }
        .logo-badge img { width: 100%; height: 100%; object-fit: contain; background: white; }
        .category-title {
            margin-top: 14px; padding: 10px 12px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.14); background: #171d2a;
            font-size: 1.06rem; font-weight: 950;
        }
        .category-card {
            border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
            background: rgba(16,23,34,0.72); padding: 12px; margin: 12px 0 18px;
        }
        .small-muted { color: var(--muted); font-size: 0.88rem; }
        .estimate {
            border-radius: 8px; padding: 16px; border: 1px solid rgba(255,255,255,0.12);
            font-weight: 950; font-size: 1.8rem; text-align: center;
        }
        .estimate.up { border-color: #00d36f; background: rgba(0,211,111,0.12); color: #2cff91; }
        .estimate.flat { border-color: #ffb020; background: rgba(255,176,32,0.12); color: #ffcf72; }
        .estimate.down { border-color: #ff4655; background: rgba(255,70,85,0.12); color: #ff6b78; animation: pulseDown 1.2s infinite; }
        @keyframes pulseDown { 0%,100% { opacity: 1; } 50% { opacity: .55; } }
        .news-card {
            display: grid; grid-template-columns: 140px 1fr; gap: 14px;
            background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
            padding: 12px; margin-bottom: 12px;
        }
        .news-image { width: 140px; height: 92px; border-radius: 8px; object-fit: cover; background: #202a3b; }
        .news-title { color: white; font-weight: 950; margin-bottom: 4px; }
        .news-meta, .news-summary { color: var(--muted); font-size: 0.9rem; }
        .bell-banner {
            position: sticky; top: 0; z-index: 999;
            margin: -1.25rem calc(50% - 50vw) 18px; padding: 10px 24px;
            background: linear-gradient(90deg, #0c6d48, #1268c6);
            color: white; font-weight: 950; text-align: center;
            box-shadow: 0 6px 20px rgba(0,0,0,0.28);
        }
        @media (max-width: 760px) {
            .news-card { grid-template-columns: 1fr; }
            .news-image { width: 100%; height: 170px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


css()


def read_json(path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return fallback


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2))


def clean_ticker(ticker):
    return re.sub(r"[^A-Z0-9.\\-]", "", str(ticker).upper().strip())


def clean_category(name):
    name = str(name or "").strip()
    return name or DEFAULT_CATEGORY


def widget_key(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_") or "item"


def load_portfolio():
    rows = read_json(PORTFOLIO_FILE, [])
    clean_rows = []
    seen = set()
    for row in rows:
        ticker = clean_ticker(row.get("Ticker", ""))
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        clean_rows.append(
            {
                "Ticker": ticker,
                "Name": str(row.get("Name") or ticker).strip(),
                "Category": clean_category(row.get("Category")),
            }
        )
    return clean_rows


def save_portfolio(rows):
    write_json(PORTFOLIO_FILE, rows)


def load_categories(rows=None):
    cats = [clean_category(c) for c in read_json(CATEGORIES_FILE, [DEFAULT_CATEGORY])]
    if rows:
        cats.extend(clean_category(row.get("Category")) for row in rows)
    output = []
    for cat in cats:
        if cat not in output:
            output.append(cat)
    if DEFAULT_CATEGORY not in output:
        output.insert(0, DEFAULT_CATEGORY)
    return output


def save_categories(categories):
    output = []
    for category in categories:
        category = clean_category(category)
        if category not in output:
            output.append(category)
    write_json(CATEGORIES_FILE, output or [DEFAULT_CATEGORY])


def logo_path(ticker):
    aliases = {"SNDK": "SNDK", "SAN": "SNDK"}
    ticker = aliases.get(ticker, ticker)
    path = LOGO_DIR / f"{ticker}.png"
    return path if path.exists() else None


def logo_html(ticker, name="", size=34, use_remote=True):
    ticker = clean_ticker(ticker)
    initials = "".join(part[0] for part in re.findall(r"[A-Za-z0-9]+", name or ticker)[:2]).upper() or ticker[:2]
    fallback_text = html.escape(initials)
    path = logo_path(ticker)
    if path:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'<span class="logo-badge" style="width:{size}px;height:{size}px;flex-basis:{size}px;"><img src="data:image/png;base64,{data}" alt="{html.escape(ticker)}"></span>'
    if use_remote:
        try:
            info = company_info(ticker)
            logo_url = info.get("Logo") or ""
            domain = info.get("Domain") or COMPANY_DOMAINS.get(ticker, "")
            if not logo_url and domain:
                logo_url = f"https://logo.clearbit.com/{domain}"
            if logo_url:
                safe_url = html.escape(logo_url, quote=True)
                return (
                    f'<span class="logo-badge" style="width:{size}px;height:{size}px;flex-basis:{size}px;">'
                    f'<img src="{safe_url}" alt="{html.escape(ticker)}" onerror="this.remove();this.parentElement.textContent=&quot;{fallback_text}&quot;">'
                    "</span>"
                )
        except Exception:
            pass
    colors = ["#0b8f68", "#2f7df6", "#7c3ff2", "#117c7a", "#a45012", "#9f2c48"]
    color = colors[int(hashlib.sha1(ticker.encode()).hexdigest(), 16) % len(colors)]
    return f'<span class="logo-badge" style="width:{size}px;height:{size}px;flex-basis:{size}px;background:{color};">{fallback_text}</span>'


def stock_line_html(ticker, name, price=None, today=None):
    price_html = ""
    if price is not None or today is not None:
        if today is None or pd.isna(today):
            change_class = "flat"
        elif today > 0:
            change_class = "up"
        elif today < 0:
            change_class = "down"
        else:
            change_class = "flat"
        price_html = (
            '<span class="stock-price">'
            f'<span class="price">{html.escape(fmt_price(price))}</span>'
            f'<span class="change {change_class}">{html.escape(fmt_pct(today))}</span>'
            "</span>"
        )
    return (
        '<div class="stock-line">'
        f'{logo_html(ticker, name)}'
        f'<span class="ticker">{html.escape(ticker)}</span>'
        f'<span class="name">{html.escape(name)}</span>'
        f"{price_html}"
        "</div>"
    )


def today_class(today):
    if today is None or pd.isna(today):
        return "flat"
    if today > 0:
        return "up"
    if today < 0:
        return "down"
    return "flat"


def stock_table_html(category_rows):
    body = []
    for row in category_rows:
        q = quote(row["Ticker"])
        ticker = html.escape(row["Ticker"])
        name = html.escape(row["Name"])
        today = q.get("Today")
        body.append(
            "<tr>"
            f'<td class="logo-cell">{logo_html(row["Ticker"], row["Name"], 30, use_remote=False)}</td>'
            f'<td class="ticker-cell">{ticker}</td>'
            f'<td class="company-cell">{name}</td>'
            f'<td class="price-cell">{html.escape(fmt_price(q.get("Price")))}</td>'
            f'<td class="today-cell"><span class="today-pill {today_class(today)}">{html.escape(fmt_pct(today))}</span></td>'
            '<td class="edit-cell"></td>'
            "</tr>"
        )
    return (
        '<table class="stock-table">'
        "<thead><tr><th></th><th>Ticker</th><th>Company</th><th>Price</th><th>Today</th><th></th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def render_portfolio_stock_row(row, category, categories, rows):
    q = quote(row["Ticker"])
    logo_col, ticker_col, company_col, price_col, today_col, edit_col = st.columns(
        [0.06, 0.12, 0.36, 0.16, 0.16, 0.14],
        vertical_alignment="center",
    )
    with logo_col:
        st.markdown(f'<div class="portfolio-cell">{logo_html(row["Ticker"], row["Name"], 30, use_remote=False)}</div>', unsafe_allow_html=True)
    with ticker_col:
        st.markdown(f'<div class="portfolio-cell portfolio-ticker">{html.escape(row["Ticker"])}</div>', unsafe_allow_html=True)
    with company_col:
        st.markdown(f'<div class="portfolio-cell portfolio-company">{html.escape(row["Name"])}</div>', unsafe_allow_html=True)
    with price_col:
        st.markdown(f'<div class="portfolio-cell portfolio-price">{html.escape(fmt_price(q.get("Price")))}</div>', unsafe_allow_html=True)
    with today_col:
        today = q.get("Today")
        st.markdown(
            f'<div class="portfolio-cell portfolio-today"><span class="today-pill {today_class(today)}">{html.escape(fmt_pct(today))}</span></div>',
            unsafe_allow_html=True,
        )
    with edit_col:
        with st.popover("Edit"):
            other_categories = [item for item in categories if item != category]
            target = st.selectbox(
                "Move to",
                other_categories or [category],
                key=f"row_target_{category}_{row['Ticker']}",
                disabled=not other_categories,
            )
            if st.button("Move", key=f"row_move_{category}_{row['Ticker']}", disabled=not other_categories):
                for item in rows:
                    if item["Ticker"] == row["Ticker"]:
                        item["Category"] = target
                        break
                save_portfolio(rows)
                st.session_state["last_move_message"] = f"Moved {row['Ticker']} to {target}."
                st.rerun()
            if st.button("Remove", key=f"remove_{category}_{row['Ticker']}"):
                save_portfolio([item for item in rows if item["Ticker"] != row["Ticker"]])
                st.rerun()


def fmt_price(value):
    if value is None or pd.isna(value):
        return "Waiting"
    return f"${float(value):,.2f}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return "0.00%"
    return f"{float(value):+.2f}%"


def fmt_volume(value):
    if value is None or pd.isna(value):
        return "Waiting"
    value = float(value)
    for suffix in ["", "K", "M", "B"]:
        if abs(value) < 1000:
            return f"{value:.1f}{suffix}" if suffix else f"{value:.0f}"
        value /= 1000
    return f"{value:.1f}T"


def score_color(score):
    score = max(0, min(10, float(score or 0)))
    if score >= 7:
        light = int(72 - (score - 7) * 10)
        return f"hsl(145, 90%, {max(42, light)}%)"
    if score >= 4:
        return "hsl(38, 95%, 52%)"
    return "hsl(354, 90%, 58%)"


def score_text(score):
    return f"{float(score):.1f}/10"


def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def empty_quote(ticker):
    return {"Ticker": ticker, "Price": None, "Today": None, "Volume": None, "Name": ticker}


def direct_yahoo_quotes(tickers):
    tickers = list(dict.fromkeys(clean_ticker(ticker) for ticker in tickers if clean_ticker(ticker)))
    output = {ticker: empty_quote(ticker) for ticker in tickers}
    if not tickers:
        return output
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={quote_plus(','.join(tickers))}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        with urlopen(Request(url, headers=headers), timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for item in payload.get("quoteResponse", {}).get("result", []):
            ticker = clean_ticker(item.get("symbol", ""))
            if not ticker:
                continue
            output[ticker] = {
                "Ticker": ticker,
                "Price": safe_float(item.get("regularMarketPrice")),
                "Today": safe_float(item.get("regularMarketChangePercent")),
                "Volume": safe_float(item.get("regularMarketVolume")),
                "Name": item.get("shortName") or item.get("longName") or ticker,
            }
    except Exception:
        pass
    return output


def direct_yahoo_quote(ticker):
    ticker = clean_ticker(ticker)
    if not ticker:
        return empty_quote(ticker)
    quick = direct_yahoo_quotes([ticker]).get(ticker, empty_quote(ticker))
    if quick.get("Price") is not None:
        return quick
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(ticker)}?range=1d&interval=1m&includePrePost=true"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        with urlopen(Request(url, headers=headers), timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return empty_quote(ticker)

        meta = result.get("meta", {})
        quote_block = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = [safe_float(value) for value in quote_block.get("close", [])]
        volumes = [safe_float(value) for value in quote_block.get("volume", [])]
        closes = [value for value in closes if value is not None]
        volumes = [value for value in volumes if value is not None]

        price = safe_float(meta.get("regularMarketPrice")) or (closes[-1] if closes else None)
        previous = safe_float(meta.get("chartPreviousClose") or meta.get("previousClose"))
        today = None
        if price is not None and previous:
            today = (price - previous) / previous * 100
        elif price is not None and closes:
            first = closes[0]
            if first:
                today = (price - first) / first * 100

        return {
            "Ticker": ticker,
            "Price": price,
            "Today": today,
            "Volume": volumes[-1] if volumes else safe_float(meta.get("regularMarketVolume")),
            "Name": ticker,
        }
    except Exception:
        return empty_quote(ticker)


@st.cache_data(ttl=QUOTE_TTL, show_spinner=False)
def history(ticker, period="1d", interval="1m"):
    ticker = clean_ticker(ticker)
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False, prepost=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.reset_index()
        if "Datetime" not in data.columns and "Date" in data.columns:
            data = data.rename(columns={"Date": "Datetime"})
        return data.dropna(subset=["Close"]).tail(390)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=QUOTE_TTL, show_spinner=False)
def quote(ticker):
    ticker = clean_ticker(ticker)
    price = None
    today = None
    volume = None

    direct = direct_yahoo_quote(ticker)
    price = direct.get("Price")
    today = direct.get("Today")
    volume = direct.get("Volume")
    if price is not None:
        return direct

    try:
        fast = dict(yf.Ticker(ticker).fast_info)
        price = safe_float(fast.get("last_price") or fast.get("lastPrice"))
        previous = safe_float(
            fast.get("regular_market_previous_close")
            or fast.get("regularMarketPreviousClose")
            or fast.get("previous_close")
            or fast.get("previousClose")
        )
        volume = safe_float(fast.get("day_volume") or fast.get("last_volume") or fast.get("volume"))
        if price is not None and previous:
            today = (price - previous) / previous * 100
    except Exception:
        pass

    data = history(ticker)
    if not data.empty:
        last = data.iloc[-1]
        first = data.iloc[0]
        candle_price = safe_float(last.get("Close"))
        first_price = safe_float(first.get("Close"))
        candle_volume = safe_float(last.get("Volume"))
        price = price if price is not None else candle_price
        if today is None and candle_price is not None and first_price:
            today = (candle_price - first_price) / first_price * 100
        volume = volume if volume is not None else candle_volume

    if price is None:
        try:
            daily = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
            if not daily.empty:
                last = daily.iloc[-1]
                prev = daily.iloc[-2] if len(daily) > 1 else daily.iloc[-1]
                price = safe_float(last.get("Close"))
                previous = safe_float(prev.get("Close"))
                volume = volume if volume is not None else safe_float(last.get("Volume"))
                if today is None and price is not None and previous:
                    today = (price - previous) / previous * 100
        except Exception:
            pass

    return {"Ticker": ticker, "Price": price, "Today": today, "Volume": volume, "Name": ticker}


def parse_quote_frame(ticker, data):
    if data is None or data.empty:
        return {"Ticker": ticker, "Price": None, "Today": None, "Volume": None, "Name": ticker}
    data = data.dropna(subset=["Close"])
    if data.empty:
        return {"Ticker": ticker, "Price": None, "Today": None, "Volume": None, "Name": ticker}
    last = data.iloc[-1]
    first = data.iloc[0]
    price = safe_float(last.get("Close"))
    first_price = safe_float(first.get("Close"))
    volume = safe_float(last.get("Volume"))
    today = None
    if price is not None and first_price:
        today = (price - first_price) / first_price * 100
    return {"Ticker": ticker, "Price": price, "Today": today, "Volume": volume, "Name": ticker}


@st.cache_data(ttl=QUOTE_TTL, show_spinner=False)
def quotes_for(tickers):
    tickers = list(dict.fromkeys(clean_ticker(ticker) for ticker in tickers if clean_ticker(ticker)))
    if not tickers:
        return {}
    direct_output = direct_yahoo_quotes(tickers)
    if any(item.get("Price") is not None for item in direct_output.values()):
        return direct_output
    try:
        data = yf.download(
            tickers,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=False,
            prepost=True,
            threads=False,
        )
        output = {}
        if isinstance(data.columns, pd.MultiIndex):
            ticker_level = 1 if data.columns.names[1] in {"Ticker", "Symbols", None} else 0
            for ticker in tickers:
                try:
                    frame = data.xs(ticker, axis=1, level=ticker_level)
                    output[ticker] = parse_quote_frame(ticker, frame)
                except Exception:
                    output[ticker] = {"Ticker": ticker, "Price": None, "Today": None, "Volume": None, "Name": ticker}
        else:
            output[tickers[0]] = parse_quote_frame(tickers[0], data)
        return output
    except Exception:
        return {ticker: quote(ticker) for ticker in tickers[:3]}


@st.cache_data(ttl=COMPANY_TTL, show_spinner=False)
def company_info(ticker):
    try:
        info = yf.Ticker(ticker).get_info()
        website = info.get("website") or ""
        domain = urlparse(website).netloc.replace("www.", "") if website else COMPANY_DOMAINS.get(ticker, "")
        return {
            "Name": info.get("shortName") or info.get("longName") or ticker,
            "Sector": info.get("sector") or "Unknown",
            "Logo": info.get("logo_url") or "",
            "Website": website,
            "Domain": domain,
        }
    except Exception:
        return {
            "Name": ticker,
            "Sector": "Unknown",
            "Logo": "",
            "Website": "",
            "Domain": COMPANY_DOMAINS.get(ticker, ""),
        }


def add_indicators(data):
    if data.empty:
        return data
    df = data.copy()
    close = df["Close"].astype(float)
    volume = df.get("Volume", pd.Series([0] * len(df))).astype(float).replace(0, np.nan)
    typical = (df["High"].astype(float) + df["Low"].astype(float) + close) / 3
    df["VWAP"] = (typical * volume).cumsum() / volume.cumsum()
    df["EMA 9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA 21"] = close.ewm(span=21, adjust=False).mean()
    return df


def estimate_stock(ticker):
    df = add_indicators(history(ticker))
    if df.empty or len(df) < 10:
        return {"Label": "FLAT", "Score": 5.0, "Pressure": 0, "Recent": 0, "Volume": 0, "Why": "Waiting for enough live data."}
    last10 = df.tail(10)
    last = df.iloc[-1]
    close = float(last["Close"])
    start = float(last10.iloc[0]["Close"])
    recent = (close - start) / start * 100 if start else 0
    vwap_gap = (close - float(last["VWAP"])) / close * 100 if close and not pd.isna(last["VWAP"]) else 0
    ema9_gap = (close - float(last["EMA 9"])) / close * 100 if close else 0
    ema21_gap = (close - float(last["EMA 21"])) / close * 100 if close else 0
    green_volume = last10.loc[last10["Close"] >= last10["Open"], "Volume"].sum()
    red_volume = last10.loc[last10["Close"] < last10["Open"], "Volume"].sum()
    pressure = ((green_volume - red_volume) / max(green_volume + red_volume, 1)) * 100
    volume_lift = (last10["Volume"].tail(3).mean() / max(last10["Volume"].head(7).mean(), 1) - 1) * 100
    raw = 5 + recent * 1.6 + vwap_gap * 2.1 + ema9_gap * 2 + ema21_gap * 1.4 + pressure * 0.018 + volume_lift * 0.01
    score = round(max(1, min(10, raw)), 1)
    if score >= 6.3:
        label = "UP"
    elif score <= 4.2:
        label = "DOWN"
    else:
        label = "FLAT"
    why = "10 minute view using price position, VWAP, moving averages, and buy/sell volume pressure."
    return {"Label": label, "Score": score, "Pressure": pressure, "Recent": recent, "Volume": volume_lift, "Why": why}


@st.cache_data(ttl=SEARCH_TTL, show_spinner=False)
def search_stocks(query):
    query = str(query or "").strip()
    if len(query) < 3:
        return []
    key = query.upper()
    results = []
    for override_key, item in SEARCH_OVERRIDES.items():
        if key in override_key or key in item[1].upper() or key in item[0]:
            results.append(item)
    try:
        search = yf.Search(query, max_results=8)
        quotes = search.quotes or []
        for item in quotes:
            ticker = clean_ticker(item.get("symbol", ""))
            name = item.get("shortname") or item.get("longname") or ticker
            if ticker and item.get("quoteType") in {"EQUITY", "ETF"}:
                results.append((ticker, name))
    except Exception:
        for ticker in set(sum((v for sector in SECTOR_STOCKS.values() for v in sector.values()), [])):
            info = company_info(ticker)
            if key in ticker or key in info["Name"].upper():
                results.append((ticker, info["Name"]))
    deduped = []
    seen = set()
    for ticker, name in results:
        if ticker not in seen:
            seen.add(ticker)
            deduped.append({"Ticker": ticker, "Name": name})
    return deduped[:8]


def nav():
    selected = st.query_params.get("page", "My Investments")
    if selected not in {"My Investments", "Trading", "News"}:
        selected = "My Investments"
    st.markdown(
        f"""
        <div class="top-nav">
          <div class="brand-mark">B</div>
          <div class="brand-name">Agent 101</div>
          <a class="nav-pill {'active' if selected == 'My Investments' else ''}" href="?page=My%20Investments">My Investments</a>
          <a class="nav-pill {'active' if selected == 'Trading' else ''}" href="?page=Trading">Trading</a>
          <a class="nav-pill {'active' if selected == 'News' else ''}" href="?page=News">News</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return selected


def market_banner():
    now = datetime.now(NY_TZ)
    today = now.date()
    open_at = datetime.combine(today, time(9, 30), NY_TZ)
    close_at = datetime.combine(today, time(16, 0), NY_TZ)
    target = None
    label = ""
    if open_at - timedelta(minutes=30) <= now < open_at:
        target = open_at
        label = "Opening bell"
    elif close_at - timedelta(minutes=30) <= now < close_at:
        target = close_at
        label = "Closing bell"
    if target:
        remaining = target - now
        mins, secs = divmod(int(remaining.total_seconds()), 60)
        st.markdown(f'<div class="bell-banner">{label} in {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
    if now.time() == time(9, 30):
        components.html(
            "<script>new Audio('https://actions.google.com/sounds/v1/alarms/dinner_bell_triangle.ogg').play().catch(()=>{});</script>",
            height=0,
        )


def render_search_add(location):
    st.markdown("### Add a stock")
    query = st.text_input("Search by ticker or company", key=f"search_{location}", placeholder="Type 3 letters")
    results = search_stocks(query)
    portfolio = load_portfolio()
    tickers = {row["Ticker"] for row in portfolio}
    if query and len(query) < 3:
        st.caption("Type at least 3 characters.")
    for item in results:
        ticker, name = item["Ticker"], item["Name"]
        c1, c2 = st.columns([0.78, 0.22], vertical_alignment="center")
        with c1:
            st.markdown(stock_line_html(ticker, name), unsafe_allow_html=True)
        with c2:
            if ticker in tickers:
                st.caption("Added")
            elif st.button("Add", key=f"add_{location}_{ticker}"):
                category = DEFAULT_CATEGORY
                portfolio.append({"Ticker": ticker, "Name": name, "Category": category})
                save_portfolio(portfolio)
                st.rerun()


def render_category_stock_add(category, rows):
    category_key = widget_key(category)
    query_key = f"category_add_query_{category_key}"
    clear_key = f"clear_{query_key}"
    if st.session_state.pop(clear_key, False):
        st.session_state[query_key] = ""

    search_col, close_col = st.columns([0.9, 0.1], vertical_alignment="center")
    with search_col:
        query = st.text_input(
            "Add stock",
            key=query_key,
            placeholder=f"Add to {category}",
            label_visibility="collapsed",
        )
    with close_col:
        if query:
            if st.button("Close", key=f"category_close_{category_key}"):
                st.session_state[clear_key] = True
                st.rerun()

    results = search_stocks(query)
    tickers = {row["Ticker"] for row in rows}
    if query and len(query) < 3:
        st.caption("Type 3 letters.")
    for item in results[:4]:
        ticker, name = item["Ticker"], item["Name"]
        result_col, add_col = st.columns([0.86, 0.14], vertical_alignment="center")
        with result_col:
            st.markdown(stock_line_html(ticker, name), unsafe_allow_html=True)
        with add_col:
            if ticker in tickers:
                st.caption("Added")
            elif st.button("Add", key=f"category_add_{category_key}_{ticker}"):
                rows.append({"Ticker": ticker, "Name": name, "Category": category})
                save_portfolio(rows)
                st.session_state[clear_key] = True
                st.rerun()


def render_portfolio_table(rows):
    if not rows:
        st.info("Add stocks to start your portfolio.")
        return
    sort_by = st.segmented_control("Sort by", ["Category", "Price", "Today"], default="Category")
    if sort_by == "Category":
        df = pd.DataFrame(rows).sort_values(["Category", "Ticker"])
        st.dataframe(
            df[["Ticker", "Name", "Category"]],
            width="stretch",
            hide_index=True,
        )
        return
    enriched = []
    for row in rows:
        q = quote(row["Ticker"])
        info = company_info(row["Ticker"])
        enriched.append({**row, **q, "Sector": info["Sector"]})
    df = pd.DataFrame(enriched)
    if sort_by == "Price":
        df = df.sort_values("Price", ascending=False, na_position="last")
    elif sort_by == "Today":
        df = df.sort_values("Today", ascending=False, na_position="last")
    else:
        df = df.sort_values(["Sector", "Ticker"])
    st.dataframe(
        df[["Ticker", "Name", "Sector", "Price", "Today", "Volume"]].assign(
            Price=lambda x: x["Price"].map(fmt_price),
            Today=lambda x: x["Today"].map(fmt_pct),
            Volume=lambda x: x["Volume"].map(fmt_volume),
        ),
        width="stretch",
        hide_index=True,
    )


def render_category_manager(rows):
    st.markdown("### Categories")
    categories = load_categories(rows)
    with st.expander("Edit categories", expanded=False):
        add_col, rename_col = st.columns(2)
        with add_col:
            new_cat = st.text_input("New category", key="new_category")
            if st.button("Add category") and new_cat.strip():
                categories.append(clean_category(new_cat))
                save_categories(categories)
                st.rerun()
        with rename_col:
            old = st.selectbox("Rename", categories, key="rename_old")
            new_name = st.text_input("New name", key="rename_new")
            if st.button("Save name") and new_name.strip():
                renamed = clean_category(new_name)
                for row in rows:
                    if clean_category(row.get("Category")) == old:
                        row["Category"] = renamed
                categories = [renamed if cat == old else cat for cat in categories]
                save_categories(categories)
                save_portfolio(rows)
                st.rerun()

    if rows and st.session_state.get("last_move_message"):
        st.success(st.session_state["last_move_message"])

    for category in categories:
        st.markdown(f'<div class="category-title">{html.escape(category)}</div>', unsafe_allow_html=True)
        with st.container(border=True):
            render_category_stock_add(category, rows)
            category_rows = [row for row in rows if clean_category(row.get("Category")) == category]
            if not category_rows:
                st.caption("No stocks yet.")
            else:
                header = st.columns([0.06, 0.12, 0.36, 0.16, 0.16, 0.14])
                for col, label in zip(header, ["", "Ticker", "Company", "Price", "Today", ""]):
                    col.markdown(f'<div class="portfolio-header">{label}</div>', unsafe_allow_html=True)
                for row in category_rows:
                    render_portfolio_stock_row(row, category, categories, rows)


def market_signal():
    tickers = ["SPY", "QQQ", "IWM", "VIXY", "TLT"]
    values = {ticker: quote(ticker)["Today"] or 0 for ticker in tickers}
    score = 5 + values["SPY"] * 1.4 + values["QQQ"] * 1.2 + values["IWM"] * 0.8 - values["VIXY"] * 0.45 - values["TLT"] * 0.25
    score = round(max(1, min(10, score)), 1)
    label = "RISK ON" if score >= 5.8 else "RISK OFF" if score <= 4.2 else "WAITING"
    return label, score, values


def sector_momentum():
    proxy_quotes = quotes_for(list(SECTOR_PROXIES.values()))
    scores = {}
    for sector, proxy in SECTOR_PROXIES.items():
        today = proxy_quotes.get(proxy, {}).get("Today")
        today = today if today is not None and not pd.isna(today) else 0
        scores[sector] = round(max(1, min(10, 5 + today * 1.2)), 1)
    best = max(scores, key=scores.get)
    return best, scores[best], scores


@st.cache_data(ttl=SCORE_TTL, show_spinner=False)
def score_stock_for_table(ticker):
    est = estimate_stock(ticker)
    q = quote(ticker)
    return {
        "Ticker": ticker,
        "Name": company_info(ticker)["Name"],
        "Price": q["Price"],
        "Today": q["Today"],
        "Volume": q["Volume"],
        "Pressure": est["Pressure"],
        "Estimate": est["Label"],
        "Setup Score": est["Score"],
    }


def score_stock_snapshot(ticker, q):
    today = q.get("Today")
    today_value = today if today is not None and not pd.isna(today) else 0
    score = round(max(1, min(10, 5 + today_value * 0.9)), 1)
    return {
        "Ticker": ticker,
        "Name": company_info(ticker)["Name"],
        "Price": q.get("Price"),
        "Today": today,
        "Volume": q.get("Volume"),
        "Pressure": today_value * 8,
        "Estimate": "UP" if score >= 6.3 else "DOWN" if score <= 4.2 else "FLAT",
        "Setup Score": score,
    }


def render_scoreboard():
    st.markdown("### Chips Scoreboard")
    sector = st.selectbox("Choose an area", ["All Leaders"] + list(SECTOR_STOCKS.keys()), label_visibility="collapsed")
    style = st.segmented_control("Trading style", ["All", "High Risk Reward", "Balanced", "Low Risk"], default="All")
    if sector == "All Leaders":
        universe = ["NVDA", "AVGO", "TSM", "AMD", "MRVL", "MSFT", "PLTR", "CRWD", "NOW", "META", "AMZN", "RKLB", "ASTS", "XOM", "TE"]
    elif style == "All":
        universe = sum(SECTOR_STOCKS[sector].values(), [])[:24]
    else:
        universe = SECTOR_STOCKS[sector][style]
    universe = list(dict.fromkeys(universe))
    quote_map = quotes_for(universe)
    rows = [score_stock_snapshot(ticker, quote_map.get(ticker, quote(ticker))) for ticker in universe]
    df = pd.DataFrame(rows).sort_values("Setup Score", ascending=False).head(10)
    if df.empty:
        st.caption("Waiting for stock data.")
        return
    if df["Price"].isna().all():
        st.warning("Live prices are not coming through right now. The app is retrying every 5 seconds.")
    header = st.columns([0.7, 1.35, 1, 1, 1, 1, 1])
    for col, label in zip(header, ["Buy", "Stock", "Price", "Today", "Volume", "Pressure", "Setup Score"]):
        col.caption(label)
    for _, row in df.iterrows():
        color = score_color(row["Setup Score"])
        cols = st.columns([0.7, 1.35, 1, 1, 1, 1, 1], vertical_alignment="center")
        if cols[0].button("Buy", key=f"buy_{row['Ticker']}"):
            st.query_params["stock"] = row["Ticker"]
            st.query_params["stock_name"] = row["Name"]
            st.query_params["page"] = "Trading"
            st.rerun()
        cols[1].markdown(
            f"""
            <div class="trade-stock-cell">
                {logo_html(row["Ticker"], row["Name"], 30, use_remote=True)}
                <div style="min-width:0;">
                    <div>{html.escape(row["Ticker"])}</div>
                    <div class="trade-name">{html.escape(row["Name"])}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols[2].markdown(fmt_price(row["Price"]))
        cols[3].markdown(fmt_pct(row["Today"]))
        cols[4].markdown(fmt_volume(row["Volume"]))
        arrow = "↑" if row["Pressure"] > 10 else "↓" if row["Pressure"] < -10 else "─"
        cols[5].markdown(f"{row['Pressure']:+.0f}% {arrow}")
        cols[6].markdown(f'<div class="score-row" style="background:{color};color:#06130c;">{score_text(row["Setup Score"])}</div>', unsafe_allow_html=True)


def render_chart(ticker):
    data = add_indicators(history(ticker))
    if data.empty:
        st.warning("Waiting for live 1-minute data.")
        return
    chart_df = data.tail(10).copy()
    chart_df["Time"] = pd.to_datetime(chart_df["Datetime"])
    price_cols = ["Close", "VWAP", "EMA 9", "EMA 21"]
    long = chart_df.melt("Time", value_vars=price_cols, var_name="Line", value_name="Price")
    chart = (
        alt.Chart(long)
        .mark_line(size=2)
        .encode(
            x=alt.X("Time:T", title="Last 10 minutes"),
            y=alt.Y("Price:Q", scale=alt.Scale(zero=False)),
            color=alt.Color("Line:N", scale=alt.Scale(range=["#ffffff", "#00d36f", "#2f7df6", "#ffb020"])),
            tooltip=["Line", "Price", "Time"],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, width="stretch")


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_live_stock_panel(ticker):
    q = quote(ticker)
    est = estimate_stock(ticker)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1], vertical_alignment="center")
    c1.metric("Price", fmt_price(q["Price"]), fmt_pct(q["Today"]))
    c2.metric("Recent", fmt_pct(est["Recent"]))
    c3.metric("Volume", fmt_volume(q["Volume"]))
    c4.metric("Pressure", f"{est['Pressure']:+.0f}%")
    eclass = est["Label"].lower()
    st.markdown(f'<div class="estimate {eclass}"><div class="signal-label">Estimate</div>{est["Label"]}</div>', unsafe_allow_html=True)
    st.caption(est["Why"])
    render_chart(ticker)


def render_stock_page(ticker, name):
    ticker = clean_ticker(ticker)
    info = company_info(ticker)
    name = name or info["Name"]
    st.markdown(stock_line_html(ticker, name), unsafe_allow_html=True)
    render_live_stock_panel(ticker)


@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def news_for_ticker(ticker):
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        items = []
    stories = []
    for item in items[:5]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title") or "Market story"
        summary = content.get("summary") or content.get("description") or item.get("summary") or ""
        provider = content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else item.get("publisher", "")
        click_url = content.get("clickThroughUrl", {}) or content.get("canonicalUrl", {}) or {}
        url = click_url.get("url") if isinstance(click_url, dict) else item.get("link", "")
        thumb = ""
        thumbnail = content.get("thumbnail") or {}
        if isinstance(thumbnail, dict):
            resolutions = thumbnail.get("resolutions") or []
            if resolutions:
                thumb = resolutions[-1].get("url", "")
        stories.append({"Ticker": ticker, "Title": title, "Summary": summary, "Provider": provider or ticker, "URL": url, "Image": thumb})
    return stories


def render_news(rows):
    st.markdown("## News")
    all_stories = []
    for row in rows:
        all_stories.extend(news_for_ticker(row["Ticker"]))
    if not all_stories:
        st.info("Waiting for portfolio news.")
        return
    selected = st.query_params.get("story")
    if selected:
        story = next((s for s in all_stories if hashlib.sha1((s["Ticker"] + s["Title"]).encode()).hexdigest()[:10] == selected), None)
        if story:
            if st.button("Back to news"):
                st.query_params.pop("story", None)
                st.rerun()
            st.markdown(f"### {html.escape(story['Title'])}")
            if story["Image"]:
                st.image(story["Image"], width="stretch")
            st.write(story["Summary"] or "This story is available from the publisher, but only a short preview was provided.")
            if story["URL"]:
                st.caption("Full article text is not always available from the public news feed, so this page shows the available preview.")
            return
    for story in all_stories[:20]:
        key = hashlib.sha1((story["Ticker"] + story["Title"]).encode()).hexdigest()[:10]
        img = story["Image"] or ""
        image_html = f'<img class="news-image" src="{html.escape(img)}">' if img else f'<div class="news-image"></div>'
        st.markdown(
            f"""
            <div class="news-card">
                {image_html}
                <div>
                    <div class="news-title">{html.escape(story["Title"])}</div>
                    <div class="news-meta">{html.escape(story["Ticker"])} · {html.escape(story["Provider"])}</div>
                    <div class="news-summary">{html.escape(story["Summary"][:240])}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Read story", key=f"story_{key}"):
            st.query_params["story"] = key
            st.query_params["page"] = "News"
            st.rerun()


def render_my_investments():
    rows = load_portfolio()
    st.markdown("## My Investments")
    render_category_manager(rows)
    render_portfolio_table(rows)


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_live_trading_dashboard():
    try:
        label, score, reasons = market_signal()
        sector, sector_score, all_scores = sector_momentum()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="signal-card"><div class="signal-label">Market Signal</div><div class="signal-main">{label}</div><div class="score-row" style="background:{score_color(score)};color:#06130c;">{score_text(score)}</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("Why this signal", expanded=False):
                st.write({k: fmt_pct(v) for k, v in reasons.items()})
        with c2:
            st.markdown(
                f'<div class="signal-card"><div class="signal-label">Momentum</div><div class="signal-main">{html.escape(sector)}</div><div class="score-row" style="background:{score_color(sector_score)};color:#06130c;">{score_text(sector_score)}</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("View all sectors", expanded=False):
                for name, value in sorted(all_scores.items(), key=lambda item: item[1], reverse=True):
                    st.markdown(f'<div class="score-row" style="background:{score_color(value)};color:#06130c;">{html.escape(name)} · {score_text(value)}</div>', unsafe_allow_html=True)
        render_scoreboard()
    except Exception:
        st.warning("Live trading data paused for this refresh. The app will try again in 5 seconds.")


def render_trading():
    stock = st.query_params.get("stock")
    stock_name = st.query_params.get("stock_name", stock or "")
    if stock:
        if st.button("Back to trading"):
            st.query_params.pop("stock", None)
            st.query_params.pop("stock_name", None)
            st.rerun()
        render_stock_page(stock, stock_name)
        return

    left, right = st.columns([0.72, 0.28], gap="large")
    with left:
        render_live_trading_dashboard()
    with right:
        render_search_add("trading")


def main():
    market_banner()
    page = nav()
    if page == "Trading":
        render_trading()
    elif page == "News":
        render_news(load_portfolio())
    else:
        render_my_investments()


if __name__ == "__main__":
    main()
