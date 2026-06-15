#!/usr/bin/env python3
"""Stock Screener — Flask Backend mit yfinance"""

from flask import Flask, request, jsonify, send_from_directory
import json, os, sys, threading, time
from datetime import datetime, timedelta

app = Flask(__name__, static_folder=".")

# Cache für Screener-Daten (30 Sekunden)
_cache = {}
_cache_lock = threading.Lock()

# ─── HILFSFUNKTIONEN ───────────────────────────────────────────

def safe_num(val, default=None):
    """Sichere Zahlen-Extraktion aus yfinance-Objekten"""
    if val is None:
        return default
    try:
        if hasattr(val, 'item'):
            val = val.item()
        f = float(val)
        if f != f:  # NaN
            return default
        return f
    except (ValueError, TypeError):
        return default

def rsi_from_history(hist):
    """Einfachen RSI-14 aus Kursdaten berechnen"""
    if hist is None or len(hist) < 15:
        return None
    closes = hist['Close'].values
    deltas = []
    for i in range(1, len(closes)):
        deltas.append(float(closes[i] - closes[i-1]))
    gains = [d if d > 0 else 0 for d in deltas[-14:]]
    losses = [-d if d < 0 else 0 for d in deltas[-14:]]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


# ─── SCREENER: EINZELAKTIE ANALYSIEREN ─────────────────────────

def analyze_ticker(ticker_str):
    """Holt alle relevanten Daten für einen Ticker"""
    import yfinance as yf
    try:
        t = yf.Ticker(ticker_str.strip().upper())
        info = t.info or {}
        if not info or info.get('regularMarketPrice') is None and info.get('currentPrice') is None:
            return {"error": f"Keine Daten für {ticker_str}", "ticker": ticker_str.upper()}

        price = safe_num(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose'))
        prev_close = safe_num(info.get('previousClose'), price)
        change_pct = None
        if price and prev_close and prev_close != 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        # RSI aus 6-Monats-Historie
        rsi = None
        try:
            hist = t.history(period="6mo")
            rsi = rsi_from_history(hist)
        except:
            pass

        # Zielkurs
        target = safe_num(info.get('targetMeanPrice'))
        target_upside = None
        if target and price and price > 0:
            target_upside = round((target - price) / price * 100, 1)

        result = {
            "ticker": ticker_str.strip().upper(),
            "name": info.get('shortName') or info.get('longName', ''),
            "sector": info.get('sector', ''),
            "industry": info.get('industry', ''),
            "price": price,
            "change_pct": change_pct,
            "change": safe_num(info.get('regularMarketChange')),
            "market_cap": safe_num(info.get('marketCap')),
            "pe_forward": safe_num(info.get('forwardPE')),
            "pe_trailing": safe_num(info.get('trailingPE')),
            "eps": safe_num(info.get('trailingEps')),
            "dividend_yield": safe_num(info.get('dividendYield')),
            "beta": safe_num(info.get('beta')),
            "52w_high": safe_num(info.get('fiftyTwoWeekHigh')),
            "52w_low": safe_num(info.get('fiftyTwoWeekLow')),
            "rsi_14": rsi,
            "target_price": target,
            "target_upside": target_upside,
            "recommendation": info.get('recommendationKey', '').upper(),
            "num_analysts": info.get('numberOfAnalystOpinions'),
            "volume": safe_num(info.get('volume')),
            "avg_volume": safe_num(info.get('averageVolume')),
            "currency": info.get('currency', 'USD'),
            "exchange": info.get('exchange', ''),
            "country": info.get('country', ''),
        }
        return result
    except Exception as e:
        return {"error": str(e), "ticker": ticker_str.upper()}


# ─── API-ROUTEN ─────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Einzelne oder mehrere Ticker analysieren"""
    data = request.get_json() or {}
    tickers = data.get("tickers", [])
    if not tickers:
        return jsonify({"error": "Keine Ticker angegeben"}), 400

    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(",") if t.strip()]
    if not tickers:
        return jsonify({"error": "Keine gültigen Ticker"}), 400

    results = []
    for tkr in tickers[:20]:  # max 20 pro Request
        results.append(analyze_ticker(tkr))
    return jsonify({"results": results, "timestamp": datetime.now().isoformat()})

@app.route("/api/screen", methods=["POST"])
def api_screen():
    """Screener: Beliebte Aktien analysieren + filtern

    Formatiert für einen Katalog von ~80 beliebten Aktien, dann Filter anwenden.
    """
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

    # Watchlist (80+ beliebte Ticker aus verschiedenen Sektoren)
    watchlist = [
        # Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "AVGO", "CRM",
        "ADBE", "ORCL", "CSCO", "IBM", "QCOM", "TXN", "MU", "MRVL", "AMAT", "NOW",
        "SNOW", "PLTR", "NET", "DDOG", "MDB", "CRWD", "ZS", "PANW", "FTNT", "TEAM",
        # Consumer
        "TSLA", "NFLX", "DIS", "NKE", "SBUX", "MCD", "HD", "LOW", "TGT", "COST",
        "WMT", "AMZN", "BKNG", "UBER", "ABNB",
        # Finance
        "JPM", "GS", "MS", "BAC", "WFC", "C", "V", "MA", "AXP", "BLK",
        "SCHW", "BRK-B",
        # Healthcare
        "JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "ISRG", "TMO", "DHR", "ABT",
        # Energy
        "XOM", "CVX", "COP", "EOG", "SLB", "OXY",
        # Industrial
        "CAT", "DE", "BA", "LMT", "GE", "HON", "RTX", "UPS",
        # Communication
        "T", "VZ", "TMUS", "CMCSA",
        # Utilities
        "NEE", "DUK", "SO",
        # Real Estate
        "AMT", "PLD", "SPG",
        # Materials
        "LIN", "FCX", "NEM",
    ]

    results = []
    for i, tkr in enumerate(watchlist):
        try:
            r = analyze_ticker(tkr)
            if "error" in r:
                continue

            # Filter anwenden
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
                results.append(r)
        except:
            continue

    # Sortieren
    sort_key = filters["sort_by"]
    reverse = filters["sort_dir"] == "desc"
    def sort_fn(r):
        val = r.get(sort_key)
        return val if val is not None else (float('-inf') if reverse else float('inf'))
    results.sort(key=sort_fn, reverse=reverse)

    return jsonify({
        "results": results,
        "count": len(results),
        "filters": {k: v for k, v in filters.items() if v not in (None, "", 0)},
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/sectors", methods=["GET"])
def api_sectors():
    """Verfügbare Sektoren zurückgeben (statisch, aus yfinance-Kategorisierung)"""
    sectors = [
        "Technology", "Consumer Cyclical", "Financial Services", "Healthcare",
        "Energy", "Industrials", "Communication Services", "Utilities",
        "Real Estate", "Basic Materials", "Consumer Defensive"
    ]
    return jsonify({"sectors": sectors})

@app.route("/api/market", methods=["GET"])
def api_market():
    """Markt-Übersicht (SPY, VIX, QQQ, IWM)"""
    results = {}
    etfs = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100",
        "IWM": "Russell 2000",
        "DIA": "Dow Jones"
    }
    for tkr, name in etfs.items():
        r = analyze_ticker(tkr)
        r["description"] = name
        results[tkr] = r

    # VIX separat
    try:
        vix = analyze_ticker("^VIX")
        results["VIX"] = vix
    except:
        results["VIX"] = {"error": "VIX nicht verfügbar"}

    return jsonify({"indices": results, "timestamp": datetime.now().isoformat()})


# ─── START ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("TOOL_PORT", "5120"))
    print(f"Stock Screener läuft auf Port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
