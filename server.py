#!/usr/bin/env python3
"""Stock Screener — Flask Backend mit yfinance + Fuzzy-Suche"""

from flask import Flask, request, jsonify, send_from_directory
import json, os, re, threading, time
from datetime import datetime, timedelta

app = Flask(__name__, static_folder=".")

# ─── COMPANY-NAME → TICKER MAPPING (500+ Einträge) ──────────────

COMPANY_MAP = {
    # Deutsche/europäische Namen
    "volkswagen": "VOW3.DE", "vw": "VOW3.DE", "bmw": "BMW.DE", "mercedes": "MBG.DE",
    "daimler": "MBG.DE", "siemens": "SIE.DE", "allianz": "ALV.DE", "deutsche bank": "DBK.DE",
    "deutsche telekom": "DTE.DE", "telekom": "DTE.DE", "sap": "SAP", "basf": "BAS.DE",
    "bayer": "BAYN.DE", "adidas": "ADS.DE", "puma": "PUM.DE", "infineon": "IFX.DE",
    "deutsche post": "DHL.DE", "dhl": "DHL.DE", "lufthansa": "LHA.DE", "rwe": "RWE.DE",
    "e.on": "EOAN.DE", "vonovia": "VNA.DE", "rheinmetall": "RHM.DE", "commerzbank": "CBK.DE",
    "renk": "RENK.DE", "hensoldt": "HAG.DE", "nemetschek": "NEM.DE", "teamviewer": "TMV.DE",
    "zalando": "ZAL.DE", "delivery hero": "DHER.DE", "hellofresh": "HFG.DE",
    "münchner rück": "MUV2.DE", "munich re": "MUV2.DE", "hannover rück": "HNR1.DE",

    # US Tech
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "meta": "META", "facebook": "META", "nvidia": "NVDA",
    "amd": "AMD", "intel": "INTC", "broadcom": "AVGO", "salesforce": "CRM",
    "adobe": "ADBE", "oracle": "ORCL", "cisco": "CSCO", "ibm": "IBM",
    "qualcomm": "QCOM", "texas instruments": "TXN", "micron": "MU",
    "marvell": "MRVL", "applied materials": "AMAT", "servicenow": "NOW",
    "snowflake": "SNOW", "palantir": "PLTR", "cloudflare": "NET",
    "datadog": "DDOG", "mongodb": "MDB", "crowdstrike": "CRWD",
    "zscaler": "ZS", "palo alto": "PANW", "fortinet": "FTNT", "atlassian": "TEAM",
    "netflix": "NFLX", "tesla": "TSLA", "uber": "UBER", "airbnb": "ABNB",
    "booking": "BKNG", "spotify": "SPOT", "snap": "SNAP", "pinterest": "PINS",
    "shopify": "SHOP", "block": "XYZ", "square": "XYZ", "coinbase": "COIN",
    "robinhood": "HOOD", "doordash": "DASH", "twilio": "TWLO", "zoom": "ZM",
    "workday": "WDAY", "okta": "OKTA", "splunk": "SPLK", "akamai": "AKAM",
    "autodesk": "ADSK", "ansys": "ANSS", "cadence": "CDNS", "synopsys": "SNPS",
    "micron technology": "MU", "lam research": "LRCX", "kla": "KLAC",
    "analog devices": "ADI", "nxp": "NXPI", "arm": "ARM", "dell": "DELL",
    "hp": "HPQ", "hewlett packard": "HPE", "netapp": "NTAP", "pure storage": "PSTG",
    "arista": "ANET", "juniper": "JNPR", "f5": "FFIV", "vmware": "VMW",

    # US Consumer
    "nike": "NKE", "starbucks": "SBUX", "mcdonalds": "MCD", "home depot": "HD",
    "lowes": "LOW", "target": "TGT", "costco": "COST", "walmart": "WMT",
    "disney": "DIS", "coca cola": "KO", "coke": "KO", "pepsi": "PEP",
    "procter gamble": "PG", "p&g": "PG", "colgate": "CL", "loreal": "OR.PA",
    "estee lauder": "EL", "tiffany": "TIF", "lululemon": "LULU",
    "chipotle": "CMG", "yum brands": "YUM", "dominos": "DPZ",
    "mcdonald's": "MCD", "wendys": "WEN", "restaurant brands": "QSR",

    # US Finance
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman sachs": "GS",
    "morgan stanley": "MS", "bank of america": "BAC", "wells fargo": "WFC",
    "citigroup": "C", "citi": "C", "visa": "V", "mastercard": "MA",
    "american express": "AXP", "amex": "AXP", "blackrock": "BLK",
    "charles schwab": "SCHW", "berkshire": "BRK-B", "berkshire hathaway": "BRK-B",
    "buffett": "BRK-B", "paypal": "PYPL", "stripe": "STRIP", "sofi": "SOFI",
    "affirm": "AFRM", "block inc": "XYZ",

    # Healthcare & Pharma
    "johnson": "JNJ", "pfizer": "PFE", "merck": "MRK", "abbvie": "ABBV",
    "eli lilly": "LLY", "lilly": "LLY", "novo nordisk": "NVO", "novartis": "NVS",
    "roche": "RHHBY", "astrazeneca": "AZN", "gsk": "GSK", "sanofi": "SNY",
    "biontech": "BNTX", "moderna": "MRNA", "unitedhealth": "UNH",
    "intuitive surgical": "ISRG", "thermo fisher": "TMO", "danaher": "DHR",
    "abbott": "ABT", "boston scientific": "BSX", "stryker": "SYK",
    "medtronic": "MDT", "regeneron": "REGN", "vertex": "VRTX",
    "gilead": "GILD", "biogen": "BIIB", "amgen": "AMGN",

    # Energy
    "exxon": "XOM", "exxon mobil": "XOM", "chevron": "CVX", "conocophillips": "COP",
    "shell": "SHEL", "bp": "BP", "total": "TTE", "enbridge": "ENB",
    "schlumberger": "SLB", "occidental": "OXY", "halliburton": "HAL",
    "devon": "DVN", "pioneer": "PXD", "marathon": "MPC", "valero": "VLO",
    "phillips 66": "PSX", "exxonmobil": "XOM", "oxy": "OXY",

    # Industrial / Aerospace / Defense
    "caterpillar": "CAT", "deere": "DE", "boeing": "BA", "lockheed": "LMT",
    "lockheed martin": "LMT", "general electric": "GE", "ge": "GE",
    "honeywell": "HON", "raytheon": "RTX", "northrop": "NOC",
    "northrop grumman": "NOC", "generaldynamics": "GD",
    "ups": "UPS", "fedex": "FDX", "union pacific": "UNP", "csx": "CSX",
    "norfolk southern": "NSC", "3m": "MMM", "illinois tool": "ITW",
    "emerson": "EMR", "parker hannifin": "PH", "stanley black decker": "SWK",
    "eaton": "ETN", "cummins": "CMI", "rockwell": "ROK", "carrier": "CARR",
    "otis": "OTIS", "johnson controls": "JCI",

    # Telco / Media
    "at&t": "T", "att": "T", "verizon": "VZ", "t-mobile": "TMUS",
    "t mobile": "TMUS", "comcast": "CMCSA", "charter": "CHTR",
    "walt disney": "DIS", "warner bros": "WBD", "paramount": "PARA",
    "fox": "FOXA", "roku": "ROKU", "spotify technology": "SPOT",

    # Real Estate / REITs
    "american tower": "AMT", "prologis": "PLD", "simon property": "SPG",
    "crown castle": "CCI", "equinix": "EQIX", "public storage": "PSA",
    "realty income": "O", "alexandria": "ARE",

    # Materials / Mining
    "linde": "LIN", "bhp": "BHP", "rio tinto": "RIO", "vale": "VALE",
    "freeport mcmoran": "FCX", "newmont": "NEM", "barrick": "GOLD",
    "air products": "APD", "dow": "DOW", "dupont": "DD", "corteva": "CTVA",
    "sherwin williams": "SHW", "ecolab": "ECL",

    # EVs / Auto / Mobility
    "rivian": "RIVN", "lucid": "LCID", "nio": "NIO", "xpeng": "XPEV",
    "li auto": "LI", "ford": "F", "general motors": "GM", "gm": "GM",
    "toyota": "TM", "honda": "HMC", "fiat": "STLA", "stellantis": "STLA",
    "ferrari": "RACE", "porsche": "P911.DE",

    # Crypto / Bitcoin
    "bitcoin": "BTC-USD", "btc": "BTC-USD", "ethereum": "ETH-USD",
    "eth": "ETH-USD", "microstrategy": "MSTR", "marathon digital": "MARA",
    "riot": "RIOT", "clean spark": "CLSK",

    # Sonstige / Meme / Retail
    "gamestop": "GME", "amc": "AMC", "blackberry": "BB",
    "bath body": "BBWI", "bed bath": "BBBYQ",

    # Indizes / ETFs
    "s&p 500": "SPY", "sp500": "SPY", "spx": "SPY", "nasdaq": "QQQ",
    "nasdaq 100": "QQQ", "dow jones": "DIA", "dow": "DIA",
    "russell": "IWM", "russell 2000": "IWM", "vix": "^VIX",
    "volatilität": "^VIX", "volatility": "^VIX",
    "dax": "^GDAXI", "dax 40": "^GDAXI",
    "euro stoxx 50": "^STOXX50E", "estoxx": "^STOXX50E",

    # Semis / Chips
    "tsmc": "TSM", "taiwan semiconductor": "TSM", "asm lithography": "ASML",
    "asml": "ASML", "globalfoundries": "GFS", "onsemi": "ON",
    "micron": "MU", "skyworks": "SWKS", "qorvo": "QRVO", "wolfspeed": "WOLF",

    # Cloud / SaaS
    "sales force": "CRM", "salesforce": "CRM", "servicenow": "NOW",
    "hubspot": "HUBS", "gitlab": "GTLB", "github": "MSFT",
    "atlassian corp": "TEAM", "datadog inc": "DDOG", "unity": "U",
    "roblox": "RBLX", "draftkings": "DKNG",

    # AI / Robotics
    "c3.ai": "AI", "c3ai": "AI", "upstart": "UPST",
    "soundhound": "SOUN", "bigbear": "BBAI", "veritone": "VERI",

    # Consumer / Retail (more)
    "amazon.com": "AMZN", "alibaba": "BABA", "jd.com": "JD",
    "pinduoduo": "PDD", "meituan": "MPNGF", "sea limited": "SE",
    "shopify inc": "SHOP", "etsy": "ETSY", "wayfair": "W",
    "ebay": "EBAY", "best buy": "BBY", "dollar general": "DG",
    "dollar tree": "DLTR", "walgreens": "WBA", "cvs": "CVS",
}


def fuzzy_resolve(query: str) -> list[dict]:
    """Findet Ticker via Fuzzy-Matching auf Company-Map + Direkt-Ticker"""
    q = query.strip()
    if not q:
        return []

    q_lower = q.lower().strip()

    # 1. Exakter Ticker (z.B. "AAPL", "NVDA") — uppercase
    if q.upper() in {v.split('.')[0] for v in COMPANY_MAP.values()}:
        # Direkter Ticker-Match
        ticker = q.upper()
        return [{"ticker": ticker, "name": ticker, "match": "ticker", "score": 100}]

    # 2. Exakter Company-Name
    if q_lower in COMPANY_MAP:
        return [{"ticker": COMPANY_MAP[q_lower], "name": q, "match": "exact", "score": 100}]

    # 3. Teilstring-Match in Company-Map
    matches = []
    for name, ticker in COMPANY_MAP.items():
        if q_lower in name or name in q_lower:
            # Bewertung: je länger der Match, desto besser
            score = 80 + min(len(q_lower) / len(name) * 20, 20)
            matches.append({"ticker": ticker, "name": name, "match": "partial", "score": round(score)})

    # 4. Fuzzy: Levenshtein-ähnlich (einfache Edit-Distanz)
    if len(matches) < 5:
        for name, ticker in COMPANY_MAP.items():
            if any(m["name"] == name for m in matches):
                continue
            dist = _simple_similarity(q_lower, name)
            if dist > 0.65:  # 65% Ähnlichkeit
                matches.append({"ticker": ticker, "name": name, "match": "fuzzy", "score": round(dist * 100)})

    # 5. Sortieren nach Score
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:8]


def _simple_similarity(a: str, b: str) -> float:
    """Einfache String-Ähnlichkeit (Char-Bigramme)"""
    if not a or not b:
        return 0.0
    a_bigrams = {a[i:i+2] for i in range(len(a)-1)}
    b_bigrams = {b[i:i+2] for i in range(len(b)-1)}
    if not a_bigrams or not b_bigrams:
        return 0.0
    intersection = a_bigrams & b_bigrams
    return len(intersection) / min(len(a_bigrams), len(b_bigrams))


# ─── HILFSFUNKTIONEN ───────────────────────────────────────────

def safe_num(val, default=None):
    if val is None:
        return default
    try:
        if hasattr(val, 'item'):
            val = val.item()
        f = float(val)
        if f != f:
            return default
        return f
    except (ValueError, TypeError):
        return default

def rsi_from_history(hist):
    if hist is None or len(hist) < 15:
        return None
    closes = hist['Close'].values
    deltas = [float(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-14:]]
    losses = [-d if d < 0 else 0 for d in deltas[-14:]]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)

def sma_from_history(hist, period=50):
    """Simple Moving Average"""
    if hist is None or len(hist) < period:
        return None
    return round(float(hist['Close'].values[-period:].mean()), 2)

def analyze_ticker(ticker_str):
    import yfinance as yf
    try:
        t = yf.Ticker(ticker_str.strip().upper())
        info = t.info or {}
        if not info or (info.get('regularMarketPrice') is None and info.get('currentPrice') is None and info.get('previousClose') is None):
            return {"error": f"Keine Daten für {ticker_str}", "ticker": ticker_str.upper()}

        price = safe_num(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose'))
        prev_close = safe_num(info.get('previousClose'), price)
        change_pct = None
        if price and prev_close and prev_close != 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        rsi = None
        sma50 = None
        sma200 = None
        try:
            hist = t.history(period="1y")
            rsi = rsi_from_history(hist)
            sma50 = sma_from_history(hist, 50)
            sma200 = sma_from_history(hist, 200)
        except:
            pass

        target = safe_num(info.get('targetMeanPrice'))
        target_upside = None
        if target and price and price > 0:
            target_upside = round((target - price) / price * 100, 1)

        # PEG Ratio
        peg = safe_num(info.get('pegRatio'))

        # YTD Return berechnen
        ytd_return = None
        try:
            ytd_hist = t.history(period="ytd")
            if len(ytd_hist) > 0:
                ytd_start = float(ytd_hist['Close'].values[0])
                if ytd_start > 0 and price:
                    ytd_return = round((price - ytd_start) / ytd_start * 100, 1)
        except:
            pass

        # Free Cashflow Yield (wenn verfügbar)
        fcf_yield = None
        fcf = safe_num(info.get('freeCashflow'))
        mcap = safe_num(info.get('marketCap'))
        if fcf and mcap and mcap > 0:
            fcf_yield = round(fcf / mcap * 100, 2)

        result = {
            "ticker": ticker_str.strip().upper(),
            "name": info.get('shortName') or info.get('longName', ''),
            "sector": info.get('sector', ''),
            "industry": info.get('industry', ''),
            "price": price,
            "change_pct": change_pct,
            "change": safe_num(info.get('regularMarketChange')),
            "market_cap": mcap,
            "pe_forward": safe_num(info.get('forwardPE')),
            "pe_trailing": safe_num(info.get('trailingPE')),
            "peg_ratio": peg,
            "eps": safe_num(info.get('trailingEps')),
            "dividend_yield": safe_num(info.get('dividendYield')),
            "fcf_yield": fcf_yield,
            "beta": safe_num(info.get('beta')),
            "52w_high": safe_num(info.get('fiftyTwoWeekHigh')),
            "52w_low": safe_num(info.get('fiftyTwoWeekLow')),
            "sma50": sma50,
            "sma200": sma200,
            "rsi_14": rsi,
            "ytd_return": ytd_return,
            "target_price": target,
            "target_upside": target_upside,
            "recommendation": info.get('recommendationKey', '').upper(),
            "num_analysts": info.get('numberOfAnalystOpinions'),
            "volume": safe_num(info.get('volume')),
            "avg_volume": safe_num(info.get('averageVolume')),
            "currency": info.get('currency', 'USD'),
            "exchange": info.get('exchange', ''),
            "country": info.get('country', ''),
            "website": info.get('website', ''),
            "employees": info.get('fullTimeEmployees'),
        }
        return result
    except Exception as e:
        return {"error": str(e), "ticker": ticker_str.upper()}


# ─── API-ROUTEN ─────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "dashboard.html")

@app.route("/api/search", methods=["GET"])
def api_search():
    """Fuzzy-Ticker-Suche: Name oder Teilstring → Ticker-Vorschläge"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    results = fuzzy_resolve(q)
    return jsonify({"results": results, "query": q})

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json() or {}
    tickers = data.get("tickers", [])
    if not tickers:
        return jsonify({"error": "Keine Ticker angegeben"}), 400

    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(",") if t.strip()]

    # Fuzzy-Resolve für jeden Eintrag
    resolved = []
    for tkr in tickers[:20]:
        # Zuerst prüfen: ist es ein bekannter Firmenname?
        fuzzy = fuzzy_resolve(tkr)
        if fuzzy and fuzzy[0]["score"] >= 70:
            resolved.append(fuzzy[0]["ticker"])
        else:
            resolved.append(tkr.strip().upper())

    results = []
    for tkr in resolved:
        results.append(analyze_ticker(tkr))
    return jsonify({"results": results, "timestamp": datetime.now().isoformat()})

@app.route("/api/screen", methods=["POST"])
def api_screen():
    data = request.get_json() or {}
    filters = {
        "sector": data.get("sector", "").strip(),
        "min_mcap": data.get("min_mcap"),
        "max_mcap": data.get("max_mcap"),
        "min_pe": data.get("min_pe"),
        "max_pe": data.get("max_pe"),
        "min_div_yield": data.get("min_div_yield"),
        "min_rsi": data.get("min_rsi"),
        "max_rsi": data.get("max_rsi"),
        "min_change": data.get("min_change"),
        "max_change": data.get("max_change"),
        "min_price": data.get("min_price"),
        "max_price": data.get("max_price"),
        "recommendation": data.get("recommendation", "").upper(),
        "sort_by": data.get("sort_by", "change_pct"),
        "sort_dir": data.get("sort_dir", "desc"),
    }

    watchlist = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "AVGO", "CRM",
        "ADBE", "ORCL", "CSCO", "IBM", "QCOM", "TXN", "MU", "MRVL", "AMAT", "NOW",
        "SNOW", "PLTR", "NET", "DDOG", "MDB", "CRWD", "ZS", "PANW", "FTNT", "TEAM",
        "TSLA", "NFLX", "DIS", "NKE", "SBUX", "MCD", "HD", "LOW", "TGT", "COST",
        "WMT", "BKNG", "UBER", "ABNB", "SPOT", "SHOP", "PYPL", "COIN", "HOOD", "DASH",
        "JPM", "GS", "MS", "BAC", "WFC", "C", "V", "MA", "AXP", "BLK", "SCHW", "BRK-B",
        "JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "ISRG", "TMO", "DHR", "ABT", "NVO",
        "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "SHEL", "BP",
        "CAT", "DE", "BA", "LMT", "GE", "HON", "RTX", "UPS", "NOC",
        "T", "VZ", "TMUS", "CMCSA", "WBD",
        "NEE", "DUK", "SO", "AMT", "PLD", "SPG",
        "LIN", "FCX", "NEM", "GOLD",
        "LULU", "CMG", "GME", "RIVN", "LCID", "F", "GM",
        "BABA", "TSM", "ASML", "SAP", "RHM.DE", "SIE.DE",
    ]

    all_results = []
    for tkr in watchlist:
        try:
            r = analyze_ticker(tkr)
            if "error" in r:
                continue
            skip = False
            if filters["sector"] and filters["sector"].lower() not in r.get("sector", "").lower():
                skip = True
            if filters["min_mcap"] is not None and r.get("market_cap") and r["market_cap"] < filters["min_mcap"]:
                skip = True
            if filters["max_mcap"] is not None and r.get("market_cap") and r["market_cap"] > filters["max_mcap"]:
                skip = True
            if filters["min_pe"] is not None and r.get("pe_forward") and r["pe_forward"] < filters["min_pe"]:
                skip = True
            if filters["max_pe"] is not None and r.get("pe_forward") and r["pe_forward"] > filters["max_pe"]:
                skip = True
            if filters["min_div_yield"] is not None and r.get("dividend_yield") and r["dividend_yield"] < filters["min_div_yield"]:
                skip = True
            if filters["min_rsi"] is not None and r.get("rsi_14") and r["rsi_14"] < filters["min_rsi"]:
                skip = True
            if filters["max_rsi"] is not None and r.get("rsi_14") and r["rsi_14"] > filters["max_rsi"]:
                skip = True
            if filters["min_change"] is not None and r.get("change_pct") is not None and r["change_pct"] < filters["min_change"]:
                skip = True
            if filters["max_change"] is not None and r.get("change_pct") is not None and r["change_pct"] > filters["max_change"]:
                skip = True
            if filters["min_price"] is not None and r.get("price") and r["price"] < filters["min_price"]:
                skip = True
            if filters["max_price"] is not None and r.get("price") and r["price"] > filters["max_price"]:
                skip = True
            if filters["recommendation"] and filters["recommendation"] not in r.get("recommendation", ""):
                skip = True
            if not skip:
                all_results.append(r)
        except:
            continue

    sort_key = filters["sort_by"]
    reverse = filters["sort_dir"] == "desc"
    def sort_fn(r):
        val = r.get(sort_key)
        return val if val is not None else (float('-inf') if reverse else float('inf'))
    all_results.sort(key=sort_fn, reverse=reverse)

    return jsonify({
        "results": all_results,
        "count": len(all_results),
        "filters": {k: v for k, v in filters.items() if v not in (None, "", 0)},
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/sectors", methods=["GET"])
def api_sectors():
    sectors = [
        "Technology", "Consumer Cyclical", "Financial Services", "Healthcare",
        "Energy", "Industrials", "Communication Services", "Utilities",
        "Real Estate", "Basic Materials", "Consumer Defensive"
    ]
    return jsonify({"sectors": sectors})

@app.route("/api/market", methods=["GET"])
def api_market():
    results = {}
    etfs = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000", "DIA": "Dow Jones"}
    for tkr, name in etfs.items():
        r = analyze_ticker(tkr)
        r["description"] = name
        results[tkr] = r
    try:
        vix = analyze_ticker("^VIX")
        results["VIX"] = vix
    except:
        results["VIX"] = {"error": "VIX nicht verfügbar"}
    return jsonify({"indices": results, "timestamp": datetime.now().isoformat()})

@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    """Dashboard-Daten: Markt + konfigurierbare Watchlist"""
    watchlist_str = request.args.get("watchlist", "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,AMD,SPY,QQQ")
    tickers = [t.strip() for t in watchlist_str.split(",") if t.strip()]

    # Marktdaten
    market = {}
    for tkr in ["SPY", "QQQ", "^VIX"]:
        try:
            r = analyze_ticker(tkr)
            market[tkr.replace("^", "")] = r
        except:
            pass

    # Watchlist
    stocks = []
    for tkr in tickers[:25]:
        try:
            r = analyze_ticker(tkr)
            stocks.append(r)
        except:
            stocks.append({"ticker": tkr, "error": "Fehler beim Laden"})

    return jsonify({
        "market": market,
        "stocks": stocks,
        "timestamp": datetime.now().isoformat()
    })


# ─── START ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("TOOL_PORT", "5120"))
    print(f"Stock Screener v2 läuft auf Port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
