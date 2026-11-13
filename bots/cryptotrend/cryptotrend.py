"""
CRYPTO-TREND voor een Alpaca PAPER account (bitcoin, 7 dagen per week).

Strategie (zelfde idee als de trendbot, maar sneller omdat crypto sneller beweegt):
  - Koers duidelijk BOVEN het 50-daags gemiddelde  -> bitcoin kopen/vasthouden
  - Koers duidelijk ONDER het 50-daags gemiddelde  -> verkopen, in cash blijven
  - 2% marge rond het gemiddelde voorkomt heen-en-weer handelen.

Crypto handelt 24/7, dus deze bot draait elke dag (ook in het weekend) 1x.
Let op: Alpaca rekent bij crypto een kleine handelsfee.
Benodigd: alleen Python 3 (geen extra pakketten).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

# ============ INSTELLINGEN ============
BUDGET = 1000.00
PAIR = "BTC/USD"          # Eigen markt: geen andere bot handelt crypto
SMA_DAYS = 50
BUFFER = 0.02             # 2% marge rond het gemiddelde
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
POSITION_SYMBOL = PAIR.replace("/", "")           # Alpaca noemt de positie "BTCUSD"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptotrend_log.csv")


def api(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "APCA-API-KEY-ID": KEY_ID, "APCA-API-SECRET-KEY": SECRET,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise SystemExit(f"Alpaca-fout {e.code} bij {url}: {e.read().decode()}")


def closing_prices():
    start = (date.today() - timedelta(days=SMA_DAYS * 2)).isoformat()
    q = urllib.parse.urlencode({"symbols": PAIR, "timeframe": "1Day", "start": start, "limit": 1000})
    res = api("GET", f"{DATA_URL}/v1beta3/crypto/us/bars?{q}") or {}
    return [b["c"] for b in (res.get("bars") or {}).get(PAIR, [])]


def decide(prices, position_value, target):
    """Bepaal de actie. Geeft (actie, bedrag, uitleg) terug."""
    if len(prices) < SMA_DAYS:
        return "wacht", 0, f"te weinig data ({len(prices)} dagen)"
    sma = sum(prices[-SMA_DAYS:]) / SMA_DAYS
    price = prices[-1]
    uitleg = f"koers {price:,.0f} vs {SMA_DAYS}-daags gemiddelde {sma:,.0f}"
    if price > sma * (1 + BUFFER):
        tekort = target - position_value
        if tekort > target * 0.10:
            return "koop", round(tekort, 2), uitleg + " -> trend omhoog"
        return "houd", 0, uitleg + " -> trend omhoog, positie is al goed"
    if price < sma * (1 - BUFFER):
        if position_value > 0:
            return "verkoop", position_value, uitleg + " -> trend omlaag"
        return "cash", 0, uitleg + " -> trend omlaag, blijf in cash"
    return "houd", 0, uitleg + " -> vlak bij het gemiddelde, niets doen"


def log(actie, bedrag, uitleg):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,markt,actie,bedrag,dry_run,uitleg\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{PAIR},{actie},{bedrag},{DRY_RUN},\"{uitleg}\"\n")


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    pos = api("GET", f"{TRADE_URL}/v2/positions/{POSITION_SYMBOL}")
    position_value = float(pos["market_value"]) if pos else 0.0
    actie, bedrag, uitleg = decide(closing_prices(), position_value, BUDGET)
    print(f"{PAIR}: {actie.upper()} {f'${bedrag:,.2f}' if bedrag else ''} ({uitleg})")

    if not DRY_RUN:
        if actie == "koop":
            api("POST", f"{TRADE_URL}/v2/orders", {
                "symbol": PAIR, "notional": f"{bedrag:.2f}",
                "side": "buy", "type": "market", "time_in_force": "gtc",
            })
        elif actie == "verkoop":
            api("DELETE", f"{TRADE_URL}/v2/positions/{POSITION_SYMBOL}")
    if actie in ("koop", "verkoop"):
        log(actie, bedrag, uitleg)
    if DRY_RUN:
        print("(DRY_RUN staat aan: er is niets gekocht of verkocht.)")


if __name__ == "__main__":
    main()
