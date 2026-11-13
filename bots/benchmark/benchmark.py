"""
BENCHMARK-BOT voor een Alpaca PAPER account: de eerlijke meetlat.

Strategie (1 regel):
  - Koop 1 keer voor BUDGET dollar VOO (S&P 500 indexfonds) en houd het daarna vast.

Zo zie je op het dashboard of je andere bots het beter doen dan gewoon niets doen.
Draait 1x per werkdag; zodra hij gekocht heeft, doet hij nooit meer iets.

Benodigd: alleen Python 3 (geen extra pakketten).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ============ INSTELLINGEN ============
BUDGET = 1000.00        # Eenmalig bedrag in dollars
SYMBOL = "VOO"          # Vanguard S&P 500 ETF (eigen aandeel: geen andere bot gebruikt dit)
DRY_RUN = False         # True = alleen laten zien wat hij zou doen
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_log.csv")


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


def log(actie, detail):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,detail\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{SYMBOL},{actie},\"{detail}\"\n")


def decide(has_position, ever_bought):
    """Geeft de actie terug: 'koop' alleen als er nog nooit gekocht is."""
    if has_position:
        return "houd", "positie staat er al, niets doen"
    if ever_bought:
        return "klaar", "eerder gekocht en weer verkocht (met de hand?), niet opnieuw kopen"
    return "koop", f"eerste keer: voor ${BUDGET:,.2f} {SYMBOL} kopen"


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock["is_open"] and not DRY_RUN:
        print("Beurs is dicht, niets gedaan.")
        return

    pos = api("GET", f"{TRADE_URL}/v2/positions/{SYMBOL}")
    q = urllib.parse.urlencode({"status": "closed", "symbols": SYMBOL, "side": "buy", "limit": 1})
    bought = [o for o in (api("GET", f"{TRADE_URL}/v2/orders?{q}") or []) if float(o.get("filled_qty") or 0) > 0]

    actie, uitleg = decide(pos is not None, bool(bought))
    if pos:
        uitleg += f" (waarde nu ${float(pos['market_value']):,.2f}, resultaat ${float(pos['unrealized_pl']):+,.2f})"
    print(f"{SYMBOL}: {actie.upper()} ({uitleg})")

    if actie == "koop" and not DRY_RUN:
        api("POST", f"{TRADE_URL}/v2/orders", {
            "symbol": SYMBOL, "notional": f"{BUDGET:.2f}",
            "side": "buy", "type": "market", "time_in_force": "day",
        })
    if actie == "koop":
        log("koop" if not DRY_RUN else "koop (dry run)", uitleg)


if __name__ == "__main__":
    main()
