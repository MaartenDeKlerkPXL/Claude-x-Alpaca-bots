"""
MOMENTUM-JAGER voor een Alpaca PAPER account.  ** HOOG RISICO **

Zet het geld in de 3 snelste stijgers uit een lijst beweeglijke groeiaandelen
(chips, AI, crypto-bedrijven, tech). Weinig spreiding, grote uitslagen: precies wat nodig is
om in een goede maand op 10%+ te mikken, en ook de reden dat hij hard onderuit kan gaan.

Regels:
  - 1x per week (eerste run van de week) opnieuw kiezen:
      de 3 aandelen met het hoogste rendement over de laatste 20 handelsdagen (~1 maand),
      alleen als ze gestegen zijn EN boven hun 50-daags gemiddelde staan. Elk 1/3 van het budget.
  - Marktfilter: staat de hele markt (SPY, alleen als signaal) onder zijn 200-daags gemiddelde,
    dan alles verkopen en in cash wachten.
  - Noodrem: elke dag; een aandeel dat 12% onder de aankoopprijs staat wordt verkocht
    en die week niet opnieuw gekocht.

Draait elke werkdag 1x.
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
TOP_N = 3
UNIVERSE = [                 # eigen aandelen: geen andere bot handelt hierin
    "NVDA", "AMD", "AVGO", "TSLA", "PLTR", "COIN", "MSTR", "META",
    "NFLX", "SHOP", "CRWD", "ANET", "HOOD", "APP", "UBER",
]
MARKET = "SPY"               # alleen als marktfilter (wordt niet gekocht)
MOMENTUM_DAYS = 20
TREND_DAYS = 50
MARKET_DAYS = 200
STOP_LOSS = 0.12
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "momentumjager_log.csv")
STATE_FILE = os.path.join(HERE, "state.json")


def api(method, url, body=None, fatal=True):
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
        msg = f"Alpaca-fout {e.code} bij {url}: {e.read().decode()}"
        if fatal:
            raise SystemExit(msg)
        print("  " + msg)
        return None


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def all_closes():
    start = (date.today() - timedelta(days=int(MARKET_DAYS * 1.6))).isoformat()
    out, token = {}, None
    while True:
        params = {"symbols": ",".join(UNIVERSE + [MARKET]), "timeframe": "1Day", "start": start,
                  "limit": 10000, "adjustment": "all", "feed": "iex"}
        if token:
            params["page_token"] = token
        res = api("GET", f"{DATA_URL}/v2/stocks/bars?{urllib.parse.urlencode(params)}") or {}
        for sym, bars in (res.get("bars") or {}).items():
            out.setdefault(sym, []).extend(b["c"] for b in bars)
        token = res.get("next_page_token")
        if not token:
            return out


def market_ok(spy):
    if len(spy) < MARKET_DAYS:
        return True, "te weinig marktdata, filter overgeslagen"
    sma = sum(spy[-MARKET_DAYS:]) / MARKET_DAYS
    return spy[-1] > sma, f"markt (SPY) {spy[-1]:.2f} vs 200d-gem. {sma:.2f}"


def pick(closes, blocked=()):
    """De TOP_N sterkste aandelen: hoogste 20-dagenrendement, gestegen en boven 50d-gemiddelde."""
    scored = []
    for sym in UNIVERSE:
        c = closes.get(sym, [])
        if len(c) <= max(MOMENTUM_DAYS, TREND_DAYS) or sym in blocked:
            continue
        mom = c[-1] / c[-1 - MOMENTUM_DAYS] - 1
        sma = sum(c[-TREND_DAYS:]) / TREND_DAYS
        if mom > 0 and c[-1] > sma:
            scored.append((sym, mom))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return scored[:TOP_N]


def stops(positions):
    """Posities die meer dan STOP_LOSS onder de aankoopprijs staan."""
    out = []
    for p in positions:
        if p["symbol"] in UNIVERSE:
            loss = 1 - float(p["current_price"]) / float(p["avg_entry_price"])
            if loss >= STOP_LOSS:
                out.append((p["symbol"], loss))
    return out


def log(actie, sym, detail):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,dry_run,detail\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{sym},{actie},{DRY_RUN},\"{detail}\"\n")


def sell(sym, why):
    print(f"VERKOOP {sym}: {why}")
    if not DRY_RUN:
        api("DELETE", f"{TRADE_URL}/v2/positions/{sym}", fatal=False)
    log("verkoop", sym, why)


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock["is_open"] and not DRY_RUN:
        print("Beurs is dicht, niets gedaan.")
        return

    state = load_state()
    week = date.today().strftime("%G-W%V")
    if state.get("week") != week:
        state["geblokkeerd"] = []          # nieuwe week: noodrem-blokkades vervallen

    positions = [p for p in (api("GET", f"{TRADE_URL}/v2/positions") or []) if p["symbol"] in UNIVERSE]
    held = {p["symbol"] for p in positions}

    # 1. Noodrem (elke dag)
    for sym, loss in stops(positions):
        sell(sym, f"noodrem: {loss:.0%} onder de aankoopprijs")
        held.discard(sym)
        state.setdefault("geblokkeerd", []).append(sym)

    closes = all_closes()

    # 2. Marktfilter (elke dag)
    ok, info = market_ok(closes.get(MARKET, []))
    print(info + (" -> markt gezond" if ok else " -> markt zwak, alles naar cash"))
    if not ok:
        for sym in sorted(held):
            sell(sym, "marktfilter: hele markt onder 200d-gemiddelde")
        save_state(state)
        return

    # 3. Wekelijks opnieuw kiezen (of meteen als er nog niets in zit)
    if state.get("week") == week and held:
        print(f"Deze week al gekozen. In bezit: {', '.join(sorted(held))}.")
        save_state(state)
        return

    top = pick(closes, blocked=set(state.get("geblokkeerd", [])))
    print("Sterkste stijgers (20 dagen):", ", ".join(f"{s} {m:+.1%}" for s, m in top) or "geen")
    target = {s for s, _ in top}
    for sym in sorted(held - target):
        sell(sym, "niet meer bij de sterkste stijgers")
    if target:
        bedrag = BUDGET / TOP_N
        for sym, mom in top:
            if sym in held:
                continue
            print(f"KOOP {sym} voor ${bedrag:,.2f} ({mom:+.1%} in 20 dagen)")
            if not DRY_RUN:
                api("POST", f"{TRADE_URL}/v2/orders", {
                    "symbol": sym, "notional": f"{bedrag:.2f}",
                    "side": "buy", "type": "market", "time_in_force": "day",
                }, fatal=False)
            log("koop", sym, f"{mom:+.1%} in 20 dagen")
    state["week"] = week
    if not DRY_RUN:
        save_state(state)


if __name__ == "__main__":
    main()
