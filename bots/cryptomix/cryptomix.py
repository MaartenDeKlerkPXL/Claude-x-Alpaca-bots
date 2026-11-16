"""
CRYPTO-MIX voor een Alpaca PAPER account: een mandje coins van verschillende soorten.

Per coin dezelfde regel als de crypto-trend-bot:
  - Koers duidelijk BOVEN het 50-daags gemiddelde  -> die coin kopen/vasthouden
  - Koers duidelijk ONDER het 50-daags gemiddelde  -> die coin verkopen, dat deel in cash
  - 2% marge rond het gemiddelde voorkomt heen-en-weer handelen.
Elke coin krijgt een gelijk deel van het budget en wordt los van de andere beoordeeld.

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
COINS = {                     # Eigen markten: geen andere bot handelt deze coins
    "ETH/USD": "Ethereum - platform voor apps en smart contracts",
    "SOL/USD": "Solana - snel platform voor apps",
    "LINK/USD": "Chainlink - levert echte-wereld-data aan blockchains",
    "AAVE/USD": "Aave - lenen en uitlenen zonder bank (DeFi)",
    "PAXG/USD": "Pax Gold - token gedekt door echt goud",
}
SMA_DAYS = 50
BUFFER = 0.02             # 2% marge rond het gemiddelde
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptomix_log.csv")


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
    """Slotkoersen per coin, oudste eerst."""
    start = (date.today() - timedelta(days=SMA_DAYS * 2)).isoformat()
    out, token = {}, None
    while True:
        params = {"symbols": ",".join(COINS), "timeframe": "1Day", "start": start, "limit": 10000}
        if token:
            params["page_token"] = token
        res = api("GET", f"{DATA_URL}/v1beta3/crypto/us/bars?{urllib.parse.urlencode(params)}") or {}
        for pair, bars in (res.get("bars") or {}).items():
            out.setdefault(pair, []).extend(b["c"] for b in bars)
        token = res.get("next_page_token")
        if not token:
            return out


def decide(prices, position_value, target):
    """Bepaal de actie voor 1 coin. Geeft (actie, bedrag, uitleg) terug."""
    if len(prices) < SMA_DAYS:
        return "wacht", 0, f"te weinig data ({len(prices)} dagen)"
    sma = sum(prices[-SMA_DAYS:]) / SMA_DAYS
    price = prices[-1]
    afstand = price / sma - 1
    uitleg = f"koers {price:,.4g} vs {SMA_DAYS}-daags gemiddelde {sma:,.4g} ({afstand:+.1%})"
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


def log(pair, actie, bedrag, uitleg):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,markt,actie,bedrag,dry_run,uitleg\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{pair},{actie},{bedrag},{DRY_RUN},\"{uitleg}\"\n")


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    prices = closing_prices()
    target = BUDGET / len(COINS)
    for pair, wat in COINS.items():
        position_symbol = pair.replace("/", "")       # Alpaca noemt de positie bijv. "ETHUSD"
        pos = api("GET", f"{TRADE_URL}/v2/positions/{position_symbol}")
        position_value = float(pos["market_value"]) if pos else 0.0
        actie, bedrag, uitleg = decide(prices.get(pair, []), position_value, target)
        print(f"{pair:9} {actie.upper():8} {f'${bedrag:,.2f}' if bedrag else '':>10}  {uitleg}  [{wat.split(' - ')[0]}]")

        if not DRY_RUN:
            if actie == "koop":
                api("POST", f"{TRADE_URL}/v2/orders", {
                    "symbol": pair, "notional": f"{bedrag:.2f}",
                    "side": "buy", "type": "market", "time_in_force": "gtc",
                })
            elif actie == "verkoop":
                api("DELETE", f"{TRADE_URL}/v2/positions/{position_symbol}")
        if actie in ("koop", "verkoop"):
            log(pair, actie, bedrag, uitleg)
    if DRY_RUN:
        print("(DRY_RUN staat aan: er is niets gekocht of verkocht.)")


if __name__ == "__main__":
    main()
