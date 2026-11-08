#!/usr/bin/env python3
"""Henter kurser og nyheter, beregner signaler/risiko og skriver data.json."""
import json, math, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
POS = ["øker", "stiger", "rekord", "sterk", "oppgang", "hever", "vekst", "overgår", "utbytte",
       "surge", "rise", "bullish", "rally", "approval", "approves", "record", "upgrade", "growth", "gains", "strong", "raises", "beats", "soar"]
NEG = ["faller", "synker", "svak", "nedgang", "tap", "kutter", "advarer", "nedgradering", "gransk",
       "søksmål", "konkurs", "kutt", "falls", "drops", "plunge", "miss", "downgrade", "lawsuit",
       "probe", "warning", "bearish", "crash", "hack", "scam", "stolen", "selloff", "liquidat", "loss", "weak", "slump", "decline", "fears"]


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn)).fillna(50)


def macd_dir(close):
    line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    sig = line.ewm(span=9, adjust=False).mean()
    return 1 if line.iloc[-1] > sig.iloc[-1] else -1


def trend_dir(close):
    n = 200 if len(close) >= 200 else 50
    return 1 if close.iloc[-1] > close.tail(n).mean() else -1


def volatility(close, k=252):
    r = np.log(close / close.shift(1)).dropna()
    return float(r.std() * math.sqrt(k) * 100)


def max_drawdown(close):
    return float(-(close / close.cummax() - 1).min() * 100)


def analyze(close, crypto=False):
    if len(close) < 50:
        raise ValueError("for lite historikk")
    ch = lambda n: round(float((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100), 1)
    extra = {"ch7": ch(7), "ch30": ch(30)} if crypto and len(close) > 31 else {}
    return {
        **extra,
        "p": round(float(close.iloc[-1]), 4 if close.iloc[-1] < 1 else 2),
        "c": round(float((close.iloc[-1] / close.iloc[-2] - 1) * 100), 2),
        "rsi": round(float(rsi(close).iloc[-1])),
        "macd": macd_dir(close),
        "sma": trend_dir(close),
        "vol": round(volatility(close, 365 if crypto else 252)),
        "dd": round(max_drawdown(close)),
        "spark": [round(float(x), 2) for x in close.tail(60)],
    }


def sentiment(title):
    t = title.lower()
    s = sum(w in t for w in POS) - sum(w in t for w in NEG)
    return 1 if s > 0 else -1 if s < 0 else 0


def google_news(name, oslo, kw=None):
    q = urllib.parse.quote(f"{name} {kw}" if kw else (f"{name} aksje" if oslo else f"{name} stock"))
    loc = "hl=no&gl=NO&ceid=NO:no" if oslo else "hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(f"https://news.google.com/rss/search?q={q}&{loc}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    return [{"title": (i.findtext("title") or "").strip(), "url": (i.findtext("link") or "").strip(),
             "source": (i.findtext("source") or "Google Nyheter").strip()} for i in root.iter("item")][:4]


def yahoo_news(tk):
    out = []
    for n in (tk.news or [])[:4]:
        c = n.get("content") or n
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or c.get("link")
        src = (c.get("provider") or {}).get("displayName") or c.get("publisher") or "Yahoo Finance"
        if c.get("title") and url:
            out.append({"title": c["title"].strip(), "url": url, "source": src})
    return out


def collect_news(tk, name, oslo, kw=None):
    items = []
    for fn in (lambda: yahoo_news(tk), lambda: google_news(name, oslo, kw)):
        try:
            items += fn()
        except Exception as e:
            print("  nyheter feilet:", e, file=sys.stderr)
    seen, out = set(), []
    for i in items:
        k = i["title"].lower()
        if k in seen or not i["url"].startswith("https://"):
            continue
        seen.add(k)
        i["sent"] = sentiment(i["title"])
        out.append(i)
    return out[:5]


def fundamentals(tk):
    try:
        info = tk.info
    except Exception:
        info = {}
    pe = info.get("trailingPE") or info.get("forwardPE")
    pe = float(pe) if isinstance(pe, (int, float)) and 0 < pe < 500 else 20.0  # 20 = noytral
    tdy = info.get("trailingAnnualDividendYield")
    dy = tdy * 100 if isinstance(tdy, (int, float)) else (info.get("dividendYield") or 0)
    return round(pe, 1), round(float(dy), 1)


REGIONS = [  # flagg, sprak, land, ceid, soketekst
    ("🇺🇸", "en-US", "US", "US:en", "crypto bitcoin"), ("🇬🇧", "en-GB", "GB", "GB:en", "crypto bitcoin"),
    ("🇳🇴", "no", "NO", "NO:no", "kryptovaluta bitcoin"), ("🇩🇪", "de", "DE", "DE:de", "Kryptowährung Bitcoin"),
    ("🇯🇵", "ja", "JP", "JP:ja", "暗号資産 ビットコイン"), ("🇰🇷", "ko", "KR", "KR:ko", "암호화폐 비트코인"),
    ("🇧🇷", "pt-BR", "BR", "BR:pt-419", "criptomoedas bitcoin"), ("🇮🇳", "en-IN", "IN", "IN:en", "crypto bitcoin"),
]
TOPICS = {
    "ETF": ["etf"], "Regulering og lover": ["regulat", "sec ", "lawmaker", "lovgiv", "forbud", "gesetz", " ban"],
    "Hack og svindel": ["hack", "exploit", "scam", "stolen", "svindel"], "Stablecoins": ["stablecoin", "usdt", "usdc"],
    "Renter og sentralbanker": ["fed ", "interest rate", "rate cut", "renter"],
    "Store institusjoner": ["blackrock", "fidelity", "institution", "treasury", "jpmorgan"],
    "Hvaler og likvidasjoner": ["whale", "liquidat"], "Memecoins": ["meme", "doge", "pepe"],
    "AI": [" ai ", "artificial intelligence"], "Mining og halving": ["halving", "miner", "mining"],
    "Adopsjon": ["adopt", "partnership"], "DeFi og staking": ["defi", "staking", "airdrop", "layer 2"],
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def gnews(q, hl, gl, ceid, limit=3):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl={hl}&gl={gl}&ceid={ceid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    return [{"title": (i.findtext("title") or "").strip(), "url": (i.findtext("link") or "").strip()}
            for i in root.iter("item")][:limit]


def find_topics(items):
    out = []
    for k, words in TOPICS.items():
        hits = [i for i in items if any(w in f" {i['title'].lower()} " for w in words)]
        if len(hits) >= 2:
            out.append({"k": k, "n": len(hits), "url": hits[0]["url"]})
    return sorted(out, key=lambda x: -x["n"])[:5]


def crypto_overview(coin_news):
    res = {"fng": None, "trending": [], "topics": [], "world": []}
    try:
        d = get_json("https://api.alternative.me/fng/?limit=8")["data"]
        res["fng"] = {"value": int(d[0]["value"]), "prev": int(d[-1]["value"])}
    except Exception as e:
        print("fear&greed feilet:", e, file=sys.stderr)
    try:
        res["trending"] = [{"name": c["item"]["name"], "symbol": c["item"]["symbol"]}
                           for c in get_json("https://api.coingecko.com/api/v3/search/trending")["coins"][:7]]
    except Exception as e:
        print("trending feilet:", e, file=sys.stderr)
    world = []
    for flag, hl, gl, ceid, q in REGIONS:
        try:
            for n in gnews(q, hl, gl, ceid):
                if n["url"].startswith("https://"):
                    world.append({**n, "flag": flag})
        except Exception as e:
            print("verdensnyheter feilet", gl, e, file=sys.stderr)
        time.sleep(0.5)
    res["world"] = world[:24]
    res["topics"] = find_topics(world + coin_news)
    return res


def build(yf, t, name, crypto):
    tk = yf.Ticker(t)
    close = tk.history(period="1y", interval="1d")["Close"].dropna()
    s = {"t": t, "n": name, "m": "Krypto" if crypto else ("Oslo" if t.endswith(".OL") else "USA"),
         **analyze(close, crypto)}
    s["pe"], s["dy"] = (0, 0) if crypto else fundamentals(tk)
    s["news"] = collect_news(tk, name, False, "crypto" if crypto else None) if crypto else collect_news(tk, name, s["m"] == "Oslo")
    s["sent"] = round(sum(n["sent"] for n in s["news"]) / len(s["news"]), 2) if s["news"] else 0
    lab = "positiv" if s["sent"] > 0.2 else "negativ" if s["sent"] < -0.2 else "nøytral"
    s["nw"] = f"{len(s['news'])} nyheter vurdert, stemning: {lab}" if s["news"] else "Ingen nyheter funnet"
    return s


def main():
    import yfinance as yf
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site")
    out_dir.mkdir(parents=True, exist_ok=True)
    wl = json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8"))
    stocks = []
    for group, crypto in ((wl["tickers"], False), (wl.get("crypto", {}), True)):
        for t, name in group.items():
            try:
                stocks.append(build(yf, t, name, crypto))
                print("OK", t)
            except Exception as e:
                print("FEIL", t, e, file=sys.stderr)
            time.sleep(0.5)
    if not stocks:
        sys.exit("Ingen aksjer hentet, avbryter")
    coin_news = [n for s in stocks if s["m"] == "Krypto" for n in s["news"]]
    data = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "default": wl.get("default", []), "stocks": stocks, "crypto": crypto_overview(coin_news)}
    (out_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
