import altair as alt
import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(page_title="Boyler Stock Agent", page_icon="B", layout="wide")


def format_price(value):
    return f"${value:,.2f}"


def format_relation(price, level):
    difference = price - level
    direction = "Above" if difference >= 0 else "Below"
    return direction, f"{difference:+.2f}"


def format_percent(value):
    return f"{value:+.2f}%"


def risk_score_from_values(spy, qqq, iwm, hyg, tlt, vix, vix_price):
    score = 0
    score += 1 if spy > 0 else -1
    score += 1 if qqq > 0 else -1
    score += 1 if iwm > 0 else -1
    score += 1 if hyg > 0 else -1
    score += 1 if vix < 0 else -1
    score += 1 if vix_price < 20 else -1
    score += 1 if tlt < 0 else -1
    scale = round(((score + 7) / 14) * 9 + 1)
    return score, max(1, min(10, scale))


def risk_label(score):
    if score >= 3:
        return "Risk On"
    if score <= -3:
        return "Risk Off"
    return "Mixed"


STOCK_THEMES = {
    "AI Leaders": {
        "NVDA": "Nvidia",
        "MSFT": "Microsoft",
        "GOOGL": "Alphabet",
        "AMZN": "Amazon",
        "META": "Meta",
        "PLTR": "Palantir",
        "AMD": "AMD",
        "TSM": "Taiwan Semiconductor",
    },
    "Chips": {
        "NVDA": "Nvidia",
        "AMD": "AMD",
        "AVGO": "Broadcom",
        "MU": "Micron",
        "QCOM": "Qualcomm",
        "INTC": "Intel",
        "ARM": "Arm",
        "TSM": "Taiwan Semiconductor",
    },
    "Software": {
        "MSFT": "Microsoft",
        "CRM": "Salesforce",
        "NOW": "ServiceNow",
        "ADBE": "Adobe",
        "SNOW": "Snowflake",
        "DDOG": "Datadog",
        "CRWD": "CrowdStrike",
        "PLTR": "Palantir",
    },
    "Cybersecurity": {
        "CRWD": "CrowdStrike",
        "PANW": "Palo Alto Networks",
        "ZS": "Zscaler",
        "FTNT": "Fortinet",
        "S": "SentinelOne",
        "OKTA": "Okta",
        "NET": "Cloudflare",
        "CHKP": "Check Point",
    },
    "Mega Cap Tech": {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "NVDA": "Nvidia",
        "GOOGL": "Alphabet",
        "AMZN": "Amazon",
        "META": "Meta",
        "TSLA": "Tesla",
        "AVGO": "Broadcom",
    },
    "EVs & Batteries": {
        "TSLA": "Tesla",
        "RIVN": "Rivian",
        "LCID": "Lucid",
        "NIO": "Nio",
        "LI": "Li Auto",
        "XPEV": "XPeng",
        "ALB": "Albemarle",
        "QS": "QuantumScape",
    },
    "Crypto & Bitcoin": {
        "COIN": "Coinbase",
        "MSTR": "Strategy",
        "MARA": "MARA Holdings",
        "RIOT": "Riot Platforms",
        "CLSK": "CleanSpark",
        "HOOD": "Robinhood",
        "SQ": "Block",
        "PYPL": "PayPal",
    },
    "Energy": {
        "XOM": "Exxon Mobil",
        "CVX": "Chevron",
        "COP": "ConocoPhillips",
        "SLB": "SLB",
        "OXY": "Occidental Petroleum",
        "EOG": "EOG Resources",
        "MPC": "Marathon Petroleum",
        "VLO": "Valero",
    },
    "Clean Energy": {
        "ENPH": "Enphase",
        "FSLR": "First Solar",
        "SEDG": "SolarEdge",
        "RUN": "Sunrun",
        "NEE": "NextEra Energy",
        "BE": "Bloom Energy",
        "PLUG": "Plug Power",
        "GEV": "GE Vernova",
    },
    "Banks & Finance": {
        "JPM": "JPMorgan Chase",
        "BAC": "Bank of America",
        "GS": "Goldman Sachs",
        "MS": "Morgan Stanley",
        "WFC": "Wells Fargo",
        "C": "Citigroup",
        "V": "Visa",
        "MA": "Mastercard",
    },
    "Healthcare": {
        "LLY": "Eli Lilly",
        "UNH": "UnitedHealth",
        "JNJ": "Johnson & Johnson",
        "MRK": "Merck",
        "ABBV": "AbbVie",
        "PFE": "Pfizer",
        "TMO": "Thermo Fisher",
        "ISRG": "Intuitive Surgical",
    },
    "Biotech": {
        "MRNA": "Moderna",
        "BNTX": "BioNTech",
        "GILD": "Gilead",
        "AMGN": "Amgen",
        "REGN": "Regeneron",
        "VRTX": "Vertex",
        "BIIB": "Biogen",
        "CRSP": "CRISPR Therapeutics",
    },
    "Retail & Shopping": {
        "AMZN": "Amazon",
        "WMT": "Walmart",
        "COST": "Costco",
        "TGT": "Target",
        "HD": "Home Depot",
        "LOW": "Lowe's",
        "SHOP": "Shopify",
        "ETSY": "Etsy",
    },
    "Travel & Leisure": {
        "ABNB": "Airbnb",
        "BKNG": "Booking Holdings",
        "MAR": "Marriott",
        "HLT": "Hilton",
        "DAL": "Delta Air Lines",
        "UAL": "United Airlines",
        "CCL": "Carnival",
        "RCL": "Royal Caribbean",
    },
    "Defense": {
        "LMT": "Lockheed Martin",
        "RTX": "RTX",
        "NOC": "Northrop Grumman",
        "GD": "General Dynamics",
        "BA": "Boeing",
        "HII": "Huntington Ingalls",
        "LHX": "L3Harris",
        "KTOS": "Kratos Defense",
    },
    "Space": {
        "RKLB": "Rocket Lab",
        "LUNR": "Intuitive Machines",
        "ASTS": "AST SpaceMobile",
        "PL": "Planet Labs",
        "SPIR": "Spire Global",
        "IRDM": "Iridium",
        "BA": "Boeing",
        "LMT": "Lockheed Martin",
    },
    "Industrials": {
        "CAT": "Caterpillar",
        "DE": "Deere",
        "GE": "GE Aerospace",
        "HON": "Honeywell",
        "UPS": "UPS",
        "FDX": "FedEx",
        "ETN": "Eaton",
        "URI": "United Rentals",
    },
    "Real Estate": {
        "AMT": "American Tower",
        "PLD": "Prologis",
        "EQIX": "Equinix",
        "SPG": "Simon Property",
        "O": "Realty Income",
        "DLR": "Digital Realty",
        "CBRE": "CBRE",
        "VICI": "VICI Properties",
    },
    "Media & Streaming": {
        "NFLX": "Netflix",
        "DIS": "Disney",
        "WBD": "Warner Bros Discovery",
        "PARA": "Paramount",
        "ROKU": "Roku",
        "SPOT": "Spotify",
        "TTD": "The Trade Desk",
        "CMCSA": "Comcast",
    },
}


EXTRA_THEME_STOCKS = {
    "AI Leaders": {"ORCL": "Oracle", "IBM": "IBM"},
    "Chips": {"ASML": "ASML", "LRCX": "Lam Research"},
    "Software": {"ORCL": "Oracle", "MDB": "MongoDB"},
    "Cybersecurity": {"TENB": "Tenable", "CYBR": "CyberArk"},
    "Mega Cap Tech": {"ORCL": "Oracle", "NFLX": "Netflix"},
    "EVs & Batteries": {"F": "Ford", "GM": "General Motors"},
    "Crypto & Bitcoin": {"IBIT": "iShares Bitcoin Trust", "BTDR": "Bitdeer"},
    "Energy": {"HAL": "Halliburton", "PSX": "Phillips 66"},
    "Clean Energy": {"NOVA": "Sunnova", "ARRY": "Array Technologies"},
    "Banks & Finance": {"AXP": "American Express", "SCHW": "Charles Schwab"},
    "Healthcare": {"ABT": "Abbott", "DHR": "Danaher"},
    "Biotech": {"ILMN": "Illumina", "NTLA": "Intellia"},
    "Retail & Shopping": {"NKE": "Nike", "LULU": "Lululemon"},
    "Travel & Leisure": {"AAL": "American Airlines", "EXPE": "Expedia"},
    "Defense": {"LDOS": "Leidos", "TXT": "Textron"},
    "Space": {"BKSY": "BlackSky", "GSAT": "Globalstar"},
    "Industrials": {"PH": "Parker Hannifin", "ROK": "Rockwell Automation"},
    "Real Estate": {"WELL": "Welltower", "PSA": "Public Storage"},
    "Media & Streaming": {"FOXA": "Fox", "LYV": "Live Nation"},
}


def theme_stocks(theme_name):
    stocks = STOCK_THEMES[theme_name].copy()
    stocks.update(EXTRA_THEME_STOCKS.get(theme_name, {}))
    return stocks


THEME_MOMENTUM_SYMBOLS = {
    "AI Leaders": "AIQ",
    "Chips": "SOXX",
    "Software": "IGV",
    "Cybersecurity": "CIBR",
    "Mega Cap Tech": "QQQ",
    "EVs & Batteries": "DRIV",
    "Crypto & Bitcoin": "BITO",
    "Energy": "XLE",
    "Clean Energy": "ICLN",
    "Banks & Finance": "XLF",
    "Healthcare": "XLV",
    "Biotech": "XBI",
    "Retail & Shopping": "XRT",
    "Travel & Leisure": "JETS",
    "Defense": "ITA",
    "Space": "ARKX",
    "Industrials": "XLI",
    "Real Estate": "XLRE",
    "Media & Streaming": "XLC",
}


@st.cache_data(ttl=30, show_spinner=False)
def load_risk_data():
    tickers = ["SPY", "QQQ", "IWM", "HYG", "TLT", "^VIX"]
    data = yf.download(
        tickers,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if data.empty or "Close" not in data:
        return {}

    closes = data["Close"].dropna(how="all")
    if len(closes) < 2:
        return {}

    latest = closes.iloc[-1]
    previous = closes.iloc[-2]
    changes = ((latest - previous) / previous) * 100

    return {
        ticker: {
            "price": latest.get(ticker),
            "change": changes.get(ticker),
        }
        for ticker in tickers
        if pd.notna(latest.get(ticker)) and pd.notna(changes.get(ticker))
    }


@st.cache_data(ttl=60, show_spinner=False)
def load_risk_timeline():
    tickers = ["SPY", "QQQ", "IWM", "HYG", "TLT", "^VIX"]
    data = yf.download(
        tickers,
        period="1d",
        interval="5m",
        auto_adjust=False,
        progress=False,
        group_by="column",
        prepost=False,
    )

    if data.empty or "Close" not in data:
        return pd.DataFrame()

    closes = data["Close"].dropna(how="all")
    if len(closes) < 2:
        return pd.DataFrame()

    changes = ((closes - closes.iloc[0]) / closes.iloc[0]) * 100
    rows = []

    for timestamp, row in changes.iterrows():
        signals = []
        for symbol in ["SPY", "QQQ", "IWM", "HYG"]:
            if symbol in row and pd.notna(row[symbol]):
                signals.append(1 if row[symbol] > 0 else -1)

        if "TLT" in row and pd.notna(row["TLT"]):
            signals.append(1 if row["TLT"] < 0 else -1)

        if "^VIX" in row and pd.notna(row["^VIX"]):
            signals.append(1 if row["^VIX"] < 0 else -1)

        if "^VIX" in closes and pd.notna(closes.loc[timestamp, "^VIX"]):
            signals.append(1 if closes.loc[timestamp, "^VIX"] < 20 else -1)

        if not signals:
            continue

        score = sum(signals)
        scale = round(((score + len(signals)) / (2 * len(signals))) * 9 + 1)
        scale = max(1, min(10, scale))
        rows.append(
            {
                "Time": timestamp,
                "Score": scale,
                "Signal": risk_label(score),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=60, show_spinner=False)
def load_theme_momentum():
    symbols = list(THEME_MOMENTUM_SYMBOLS.values())
    data = yf.download(
        symbols,
        period="1d",
        interval="5m",
        auto_adjust=False,
        progress=False,
        group_by="column",
        prepost=False,
    )

    if data.empty or "Close" not in data:
        return None

    closes = data["Close"]
    rows = []

    for theme_name, symbol in THEME_MOMENTUM_SYMBOLS.items():
        if symbol not in closes:
            continue

        prices = closes[symbol].dropna()
        if len(prices) < 2:
            continue

        start_price = prices.iloc[0]
        latest_price = prices.iloc[-1]
        change = ((latest_price - start_price) / start_price) * 100 if start_price else 0
        rows.append(
            {
                "theme": theme_name,
                "symbol": symbol,
                "change": change,
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("change", ascending=False)


@st.cache_data(ttl=60, show_spinner=False)
def load_theme_stocks(theme_name):
    stocks = theme_stocks(theme_name)
    symbols = list(stocks.keys())
    data = yf.download(
        symbols,
        period="1d",
        interval="5m",
        auto_adjust=False,
        progress=False,
        group_by="column",
        prepost=False,
    )

    if data.empty or "Close" not in data:
        return pd.DataFrame()

    closes = data["Close"]
    volumes = data["Volume"] if "Volume" in data else pd.DataFrame()
    rows = []

    for symbol in symbols:
        if symbol not in closes:
            continue

        close_series = closes[symbol].dropna()
        if len(close_series) < 2:
            continue

        start_price = close_series.iloc[0]
        latest_price = close_series.iloc[-1]
        change = ((latest_price - start_price) / start_price) * 100 if start_price else 0
        volume = 0

        if not volumes.empty and symbol in volumes:
            volume = volumes[symbol].dropna().sum()

        rows.append(
            {
                "Ticker": symbol,
                "Name": stocks[symbol],
                "Price": latest_price,
                "Today": change,
                "Volume": volume,
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("Today", ascending=False)


@st.cache_data(ttl=5, show_spinner=False)
def load_intraday_data(ticker):
    data = yf.download(
        ticker,
        period="1d",
        interval="1m",
        auto_adjust=False,
        progress=False,
        prepost=False,
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data.dropna()


def add_indicators(data):
    chart_data = data.copy()
    typical_price = (
        chart_data["High"] + chart_data["Low"] + chart_data["Close"]
    ) / 3
    volume_total = chart_data["Volume"].cumsum()

    chart_data["VWAP"] = (typical_price * chart_data["Volume"]).cumsum() / volume_total
    chart_data["EMA 9"] = chart_data["Close"].ewm(span=9, adjust=False).mean()
    chart_data["EMA 21"] = chart_data["Close"].ewm(span=21, adjust=False).mean()
    chart_data = chart_data.reset_index().rename(columns={"Datetime": "Time"})

    if "Date" in chart_data.columns:
        chart_data = chart_data.rename(columns={"Date": "Time"})

    return chart_data


def build_line_chart(chart_data):
    lines = chart_data.melt(
        id_vars=["Time"],
        value_vars=["Close", "VWAP", "EMA 9", "EMA 21"],
        var_name="Series",
        value_name="Price",
    )

    return (
        alt.Chart(lines)
        .mark_line()
        .encode(
            x=alt.X("Time:T", title="Time"),
            y=alt.Y("Price:Q", title="Price", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Close", "VWAP", "EMA 9", "EMA 21"],
                    range=["#1f77b4", "#111827", "#16a34a", "#dc2626"],
                ),
            ),
            tooltip=[
                alt.Tooltip("Time:T", title="Time"),
                alt.Tooltip("Series:N", title="Line"),
                alt.Tooltip("Price:Q", title="Price", format="$.2f"),
            ],
        )
        .properties(height=460)
        .interactive()
    )


def build_candlestick_chart(chart_data):
    base = alt.Chart(chart_data).encode(
        x=alt.X("Time:T", title="Time"),
        color=alt.condition(
            "datum.Close >= datum.Open",
            alt.value("#16a34a"),
            alt.value("#dc2626"),
        ),
        tooltip=[
            alt.Tooltip("Time:T", title="Time"),
            alt.Tooltip("Open:Q", title="Open", format="$.2f"),
            alt.Tooltip("High:Q", title="High", format="$.2f"),
            alt.Tooltip("Low:Q", title="Low", format="$.2f"),
            alt.Tooltip("Close:Q", title="Close", format="$.2f"),
            alt.Tooltip("Volume:Q", title="Volume", format=","),
        ],
    )

    wicks = base.mark_rule().encode(
        y=alt.Y("Low:Q", title="Price", scale=alt.Scale(zero=False)),
        y2="High:Q",
    )
    bodies = base.mark_bar(size=3).encode(y="Open:Q", y2="Close:Q")
    overlays = build_line_chart(chart_data).mark_line(strokeWidth=1.7)

    return (wicks + bodies + overlays).properties(height=460).interactive()


st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #07090d 0%, #151923 100%);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 24px 26px;
        border-radius: 8px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 18px;
    ">
        <svg width="72" height="72" viewBox="0 0 72 72" role="img" aria-label="Boyler Stock Agent logo" style="flex: 0 0 auto;">
            <defs>
                <linearGradient id="markGradient" x1="12" y1="8" x2="60" y2="64" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#f8fafc"/>
                    <stop offset="1" stop-color="#94a3b8"/>
                </linearGradient>
                <linearGradient id="accentGradient" x1="18" y1="48" x2="57" y2="26" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#22c55e"/>
                    <stop offset="1" stop-color="#38bdf8"/>
                </linearGradient>
            </defs>
            <rect x="4" y="4" width="64" height="64" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)" />
            <path d="M22 18h17c8 0 13 4 13 10 0 4-2 7-6 9 5 2 8 6 8 12 0 8-6 13-16 13H22V18Zm12 12v8h5c4 0 6-1 6-4s-2-4-6-4h-5Zm0 17v9h7c4 0 7-2 7-5s-3-4-7-4h-7Z" fill="url(#markGradient)" />
            <path d="M15 50l10-9 8 5 9-15 7 7 8-13" fill="none" stroke="url(#accentGradient)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
            <h1 style="
                color: #ffffff;
                font-size: 2.35rem;
                line-height: 1.1;
                margin: 0;
                font-weight: 700;
                letter-spacing: 0;
            ">Boyler Stock Agent</h1>
            <div style="
                color: #a7b0bf;
                font-size: 0.95rem;
                margin-top: 6px;
                letter-spacing: 0;
            ">Live market dashboard</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.fragment(run_every=30)
def render_risk_section():
    risk_data = load_risk_data()
    risk_timeline = load_risk_timeline()
    momentum_ranking = load_theme_momentum()
    has_momentum = momentum_ranking is not None and not momentum_ranking.empty

    st.subheader("Market Mood")

    if not risk_data:
        st.warning("Market mood is not available right now.")
        return

    def risk_change(symbol):
        return risk_data.get(symbol, {}).get("change", 0)

    def risk_price(symbol):
        return risk_data.get(symbol, {}).get("price", 0)

    def risk_metric(column, symbol, label=None, inverse=False):
        price = risk_price(symbol)
        change = risk_change(symbol)
        delta_color = "inverse" if inverse else "normal"
        if symbol == "^VIX":
            column.metric(label or symbol, f"{price:.2f}", format_percent(change), delta_color=delta_color)
        else:
            column.metric(label or symbol, format_price(price), format_percent(change), delta_color=delta_color)

    spy = risk_change("SPY")
    qqq = risk_change("QQQ")
    iwm = risk_change("IWM")
    hyg = risk_change("HYG")
    tlt = risk_change("TLT")
    vix = risk_change("^VIX")
    vix_price = risk_price("^VIX")

    score, risk_scale = risk_score_from_values(spy, qqq, iwm, hyg, tlt, vix, vix_price)

    if score >= 3:
        regime = "Risk On"
        regime_note = "The wider market looks supportive for stocks today."
        regime_color = "#16a34a"
        regime_background = "rgba(22, 163, 74, 0.16)"
    elif score <= -3:
        regime = "Risk Off"
        regime_note = "The wider market looks more defensive today."
        regime_color = "#ef4444"
        regime_background = "rgba(239, 68, 68, 0.16)"
    else:
        regime = "Mixed"
        regime_note = "The wider market is sending mixed signals today."
        regime_color = "#f59e0b"
        regime_background = "rgba(245, 158, 11, 0.16)"

    signal_col, momentum_col = st.columns([1, 1.35])
    signal_col.markdown(
        f"""
        <div style="
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
            gap: 5px;
            height: 72px;
            box-sizing: border-box;
            padding: 14px 18px;
            margin: 2px 0 18px;
            border-radius: 8px;
            background: {regime_background};
            border: 1px solid {regime_color};
        ">
            <span style="
                color: {regime_color};
                font-size: 0.85rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0;
            ">Market signal</span>
            <div style="
                display: flex;
                align-items: center;
                gap: 12px;
            ">
                <span style="
                    color: #ffffff;
                    font-size: 2rem;
                    line-height: 1;
                    font-weight: 800;
                    letter-spacing: 0;
                ">{regime}</span>
                <span style="
                    color: #ffffff;
                    background: rgba(255, 255, 255, 0.12);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 999px;
                    padding: 4px 10px;
                    font-size: 0.95rem;
                    font-weight: 700;
                    white-space: nowrap;
                ">{risk_scale}/10</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not risk_timeline.empty:
        timeline_table = risk_timeline.tail(24).copy()
        timeline_table["Time"] = pd.to_datetime(timeline_table["Time"]).dt.strftime("%H:%M")
        timeline_table["Score"] = timeline_table["Score"].map(lambda value: f"{value}/10")

    with signal_col.popover("View score timeline", width="stretch"):
        if risk_timeline.empty:
            st.info("The score timeline is not available right now.")
        else:
            st.line_chart(risk_timeline.set_index("Time")["Score"])
            st.dataframe(timeline_table, hide_index=True, width="stretch")

    if has_momentum:
        momentum = momentum_ranking.iloc[0]
        momentum_score = round(min(10, max(1, 5 + momentum["change"])))
        momentum_col.markdown(
            f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 14px;
                height: 72px;
                box-sizing: border-box;
                padding: 14px 18px;
                margin: 2px 0 18px;
                border-radius: 8px;
                background: rgba(56, 189, 248, 0.14);
                border: 1px solid #38bdf8;
                ">
                <div>
                    <div style="
                        color: #38bdf8;
                        font-size: 0.85rem;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 0;
                    ">Momentum</div>
                    <div style="
                        color: #ffffff;
                        font-size: 2rem;
                        line-height: 1.05;
                        font-weight: 800;
                        letter-spacing: 0;
                    ">{momentum["theme"]}</div>
                </div>
                <div style="
                    color: #ffffff;
                    background: rgba(255, 255, 255, 0.12);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 999px;
                    padding: 4px 10px;
                    font-size: 0.95rem;
                    font-weight: 700;
                    white-space: nowrap;
                ">{momentum_score}/10</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sector_table = momentum_ranking.copy()
        sector_table["Score"] = sector_table["change"].map(
            lambda value: f"{round(min(10, max(1, 5 + value)))}/10"
        )
        sector_table["Move"] = sector_table["change"].map(format_percent)
        sector_table = sector_table.rename(
            columns={
                "theme": "Area",
                "symbol": "Tracker",
            }
        )[["Area", "Score", "Move", "Tracker"]]

        with momentum_col.popover("View all sectors", use_container_width=True):
            st.dataframe(sector_table, hide_index=True, width="stretch")
    else:
        momentum_col.info("MOMENTUM is not available right now.")

    st.caption(f"{regime_note} This snapshot refreshes every 30 seconds.")

    if has_momentum:
        momentum_ideas = load_theme_stocks(momentum["theme"]).head(10).copy()
        if not momentum_ideas.empty:
            st.subheader(f"Best to Watch in {momentum['theme']}")
            st.caption(
                "These are the strongest names in the current momentum area right now. Use them as a watchlist, not a buy/sell signal."
            )

            display_ideas = momentum_ideas.copy()
            display_ideas["Price"] = display_ideas["Price"].map(format_price)
            display_ideas["Today"] = display_ideas["Today"].map(format_percent)
            display_ideas["Volume"] = display_ideas["Volume"].map(lambda value: f"{value:,.0f}")
            st.dataframe(display_ideas, hide_index=True, width="stretch")


render_risk_section()


@st.fragment(run_every=60)
def render_stock_ideas():
    st.subheader("Stocks to Watch")
    idea_left, idea_right = st.columns([1, 2])
    theme_name = idea_left.selectbox("Choose an area", list(STOCK_THEMES.keys()))

    with idea_right:
        st.caption(
            "Shows active names in the selected area. This is a watchlist helper, not a buy or sell recommendation."
        )

    ideas = load_theme_stocks(theme_name)

    if ideas.empty:
        st.warning("Stock ideas are not available right now.")
        return

    top_ideas = ideas.head(5).copy()
    cols = st.columns(len(top_ideas))

    for column, row in zip(cols, top_ideas.itertuples(index=False)):
        column.metric(
            row.Ticker,
            format_price(row.Price),
            format_percent(row.Today),
        )
        column.caption(row.Name)

    table_data = top_ideas.copy()
    table_data["Price"] = table_data["Price"].map(format_price)
    table_data["Today"] = table_data["Today"].map(format_percent)
    table_data["Volume"] = table_data["Volume"].map(lambda value: f"{value:,.0f}")

    with st.expander("See the watchlist"):
        st.dataframe(table_data, hide_index=True, width="stretch")


render_stock_ideas()

LIVE_REFRESH_SECONDS = 5

top_left, top_right = st.columns([2, 1])
ticker = top_left.text_input("Stock ticker", value="AAPL").upper().strip()
chart_style = top_right.segmented_control(
    "Chart style",
    ["Line", "Candles"],
    default="Line",
)

st.caption("Default view: 1 Day with 1-minute intraday candles. The chart updates automatically every 5 seconds.")


@st.fragment(run_every=LIVE_REFRESH_SECONDS)
def render_live_chart():
    if not ticker:
        return

    with st.spinner(f"Loading 1-minute data for {ticker}..."):
        history = load_intraday_data(ticker)

    if history.empty:
        st.warning("No intraday data found. Try another ticker symbol or refresh during market hours.")
        return

    chart_data = add_indicators(history)
    latest = chart_data.iloc[-1]
    previous_close = chart_data["Close"].iloc[-2] if len(chart_data) > 1 else latest["Close"]
    price_change = latest["Close"] - previous_close
    price_change_pct = (price_change / previous_close) * 100 if previous_close else 0

    price_col, vwap_col, ema9_col, ema21_col = st.columns(4)
    price_col.metric(
        "Current price",
        format_price(latest["Close"]),
        f"{price_change:+.2f} ({price_change_pct:+.2f}%)",
    )

    for column, label in [
        (vwap_col, "VWAP"),
        (ema9_col, "EMA 9"),
        (ema21_col, "EMA 21"),
    ]:
        relation, delta = format_relation(latest["Close"], latest[label])
        column.metric(label, format_price(latest[label]), f"{relation} {delta}")

    st.subheader(f"{ticker} live intraday chart")

    if chart_style == "Candles":
        st.altair_chart(build_candlestick_chart(chart_data), use_container_width=True)
    else:
        st.altair_chart(build_line_chart(chart_data), use_container_width=True)

    status_items = []
    for label in ["VWAP", "EMA 9", "EMA 21"]:
        relation, delta = format_relation(latest["Close"], latest[label])
        status_items.append(f"{relation} {label} ({delta})")

    st.info("Current price is " + ", ".join(status_items) + ".")
    st.caption(f"Last candle loaded: {latest['Time']}. Auto-refresh: every {LIVE_REFRESH_SECONDS} seconds.")

    with st.expander("Show latest intraday data"):
        st.dataframe(
            chart_data[
                ["Time", "Open", "High", "Low", "Close", "Volume", "VWAP", "EMA 9", "EMA 21"]
            ].tail(100),
            width="stretch",
        )


render_live_chart()
