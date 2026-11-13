"""
SECTOR-ROTATIE voor een Alpaca PAPER account (momentum, 1x per maand).

Strategie:
  - Bekijk 11 sector-ETF's (tech, energie, zorg, banken, ...).
  - Kies de 2 die de afgelopen 3 maanden (63 handelsdagen) het meest stegen.
  - Alleen sectoren die in die 3 maanden echt gestegen zijn; anders blijft dat deel in cash.
  - Verkoop wat niet meer in de top 2 staat, koop de nieuwe top 2 (elk de helft van het budget).
  - Dit gebeurt 1x per maand: bij de eerste run van een nieuwe maand.

Draait elke werkdag 1x, maar handelt alleen als er deze maand nog niet gehandeld is.
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
TOP_N = 2                 # Aantal sectoren tegelijk
LOOKBACK_DAYS = 63        # ~3 maanden aan handelsdagen
SECTORS = {               # Eigen aandelen: geen andere bot gebruikt deze
    "XLK": "Technologie", "XLE": "Energie", "XLF": "Financieel", "XLV": "Zorg",
    "XLI": "Industrie", "XLY": "Luxe consumptie", "XLP": "Basis consumptie",
    "XLU": "Nutsbedrijven", "XLB": "Grondstoffen", "XLRE": "Vastgoed", "XLC": "Communicatie",
}
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sectorrotatie_log.csv")


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


def closes_per_sector():
    start = (date.today() - timedelta(days=LOOKBACK_DAYS * 2 + 10)).isoformat()
    out, token = {}, None
    while True:
        params = {"symbols": ",".join(SECTORS), "timeframe": "1Day", "start": start,
                  "limit": 10000, "adjustment": "all", "feed": "iex"}
        if token:
            params["page_token"] = token
        res = api("GET", f"{DATA_URL}/v2/stocks/bars?{urllib.parse.urlencode(params)}") or {}
        for sym, bars in (res.get("bars") or {}).items():
            out.setdefault(sym, []).extend(b["c"] for b in bars)
        token = res.get("next_page_token")
        if not token:
            return out


def ranking(closes):
    """Rendement over LOOKBACK_DAYS per sector, hoogste eerst."""
    ret = {}
    for sym, c in closes.items():
        if len(c) > LOOKBACK_DAYS:
            ret[sym] = c[-1] / c[-1 - LOOKBACK_DAYS] - 1
    return sorted(ret.items(), key=lambda kv: kv[1], reverse=True)


def decide(ranked, holdings):
    """Geeft (verkopen, kopen, doel) terug. Alleen sectoren met een positief rendement tellen."""
    target = [sym for sym, r in ranked[:TOP_N] if r > 0]
    sell = sorted(h for h in holdings if h not in target)
    buy = [s for s in target if s not in holdings]
    return sell, buy, target


def traded_this_month():
    first = date.today().replace(day=1).isoformat() + "T00:00:00Z"
    q = urllib.parse.urlencode({"status": "closed", "symbols": ",".join(SECTORS), "after": first, "limit": 50})
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

    ranked = ranking(closes_per_sector())
    print("Top 3 maanden:", ", ".join(f"{s} {SECTORS[s]} {r:+.1%}" for s, r in ranked[:5]))

    if traded_this_month() and not DRY_RUN:
        print("Deze maand al gewisseld. Volgende keer bij de eerste run van volgende maand.")
        return

    positions = api("GET", f"{TRADE_URL}/v2/positions") or []
    holdings = {p["symbol"] for p in positions if p["symbol"] in SECTORS}
    sell, buy, target = decide(ranked, holdings)
    print(f"Nu in bezit: {', '.join(sorted(holdings)) or 'niets'}. Doel: {', '.join(target) or 'cash'}.")
    if not sell and not buy:
        print("Niets te doen: de top staat er al.")
        return

    for sym in sell:
        print(f"VERKOOP {sym} ({SECTORS[sym]}): niet meer in de top {TOP_N}")
        if not DRY_RUN:
            api("DELETE", f"{TRADE_URL}/v2/positions/{sym}")
        log("verkoop", sym, f"niet meer in de top {TOP_N}")
    for sym in buy:
        bedrag = BUDGET / TOP_N
        r = dict(ranked)[sym]
        print(f"KOOP {sym} ({SECTORS[sym]}) voor ${bedrag:,.2f}: {r:+.1%} in 3 maanden")
        if not DRY_RUN:
            api("POST", f"{TRADE_URL}/v2/orders", {
                "symbol": sym, "notional": f"{bedrag:.2f}",
                "side": "buy", "type": "market", "time_in_force": "day",
            })
        log("koop", sym, f"{r:+.1%} in 3 maanden")


if __name__ == "__main__":
    main()
