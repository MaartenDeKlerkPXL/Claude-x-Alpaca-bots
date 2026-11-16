"""
DUAL MOMENTUM voor een Alpaca PAPER account (1x per maand, bekende strategie van Gary Antonacci).

Elke maand kiest hij 1 van 3 plekken voor het hele budget:
  1. Vergelijk het rendement van de afgelopen 12 maanden van
       VTI (aandelen VS)  en  VEU (aandelen rest van de wereld)  -> de sterkste is de kandidaat.
  2. Deed die kandidaat het beter dan kasgeld (BIL, kortlopende staatsobligaties)?
       ja  -> het hele budget in de kandidaat
       nee -> het hele budget in obligaties (BND), veilig wachten tot aandelen weer winnen.

Het idee: meedoen met de sterkste aandelenmarkt, maar bij een langere daling (zoals 2008 of 2022)
op tijd uitstappen naar obligaties.

Draait elke werkdag 1x, maar handelt alleen bij de eerste run van een nieuwe maand.
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
LOOKBACK_DAYS = 252          # ~12 maanden aan handelsdagen
US, WORLD, CASH, BONDS = "VTI", "VEU", "BIL", "BND"
NAMES = {US: "aandelen VS", WORLD: "aandelen rest van de wereld", CASH: "kasgeld (BIL)", BONDS: "obligaties"}
HOLDINGS = (US, WORLD, BONDS)  # waar het geld in kan staan (eigen aandelen: geen andere bot gebruikt deze)
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dualmomentum_log.csv")


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


def closes():
    start = (date.today() - timedelta(days=int(LOOKBACK_DAYS * 1.6))).isoformat()
    out, token = {}, None
    while True:
        params = {"symbols": ",".join([US, WORLD, CASH, BONDS]), "timeframe": "1Day", "start": start,
                  "limit": 10000, "adjustment": "all", "feed": "iex"}
        if token:
            params["page_token"] = token
        res = api("GET", f"{DATA_URL}/v2/stocks/bars?{urllib.parse.urlencode(params)}") or {}
        for sym, bars in (res.get("bars") or {}).items():
            out.setdefault(sym, []).extend(b["c"] for b in bars)
        token = res.get("next_page_token")
        if not token:
            return out


def returns(prices):
    """12-maandsrendement per fonds (None als er te weinig data is)."""
    return {s: (c[-1] / c[-1 - LOOKBACK_DAYS] - 1) if len(c) > LOOKBACK_DAYS else None
            for s, c in prices.items()}


def decide(ret):
    """Geeft (doel, uitleg) terug: waar het hele budget deze maand in moet."""
    if any(ret.get(s) is None for s in (US, WORLD, CASH)):
        return None, "te weinig koersdata voor 12 maanden"
    best = US if ret[US] >= ret[WORLD] else WORLD
    uitleg = (f"12 mnd: VS {ret[US]:+.1%}, wereld {ret[WORLD]:+.1%}, kasgeld {ret[CASH]:+.1%}. "
              f"Sterkste aandelen: {NAMES[best]}")
    if ret[best] > ret[CASH]:
        return best, uitleg + f", beter dan kasgeld -> {best}"
    return BONDS, uitleg + f", niet beter dan kasgeld -> veilig naar {BONDS}"


def traded_this_month():
    first = date.today().replace(day=1).isoformat() + "T00:00:00Z"
    q = urllib.parse.urlencode({"status": "closed", "symbols": ",".join(HOLDINGS), "after": first, "limit": 50})
    return any(float(o.get("filled_qty") or 0) > 0 for o in (api("GET", f"{TRADE_URL}/v2/orders?{q}") or []))


def log(actie, sym, detail):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,dry_run,detail\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{sym},{actie},{DRY_RUN},\"{detail}\"\n")


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock["is_open"] and not DRY_RUN:
        print("Beurs is dicht, niets gedaan.")
        return

    target, uitleg = decide(returns(closes()))
    print(uitleg)
    if target is None:
        return

    positions = api("GET", f"{TRADE_URL}/v2/positions") or []
    held = sorted(p["symbol"] for p in positions if p["symbol"] in HOLDINGS)
    if held == [target]:
        print(f"Staat al in {target} ({NAMES[target]}). Niets te doen.")
        return
    if held and traded_this_month() and not DRY_RUN:
        print("Deze maand al gewisseld. Volgende keer bij de eerste run van volgende maand.")
        return

    for sym in held:
        if sym != target:
            print(f"VERKOOP {sym} ({NAMES[sym]})")
            if not DRY_RUN:
                api("DELETE", f"{TRADE_URL}/v2/positions/{sym}")
            log("verkoop", sym, uitleg)
    if target not in held:
        print(f"KOOP {target} ({NAMES[target]}) voor ${BUDGET:,.2f}")
        if not DRY_RUN:
            api("POST", f"{TRADE_URL}/v2/orders", {
                "symbol": target, "notional": f"{BUDGET:.2f}",
                "side": "buy", "type": "market", "time_in_force": "day",
            })
        log("koop", target, uitleg)


if __name__ == "__main__":
    main()
