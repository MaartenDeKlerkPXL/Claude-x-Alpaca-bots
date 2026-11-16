"""
HEFBOOM-TREND voor een Alpaca PAPER account.  ** HOOG RISICO **

Handelt in TQQQ: een fonds dat elke dag 3x zo hard beweegt als de Nasdaq-100.
Stijgt de Nasdaq 1%, dan stijgt TQQQ ongeveer 3%. Daalt hij 1%, dan daalt TQQQ ongeveer 3%.
Zonder geleend geld: de hefboom zit in het fonds zelf.

Regels:
  - Nasdaq-100 (QQQ, alleen als signaal) duidelijk BOVEN zijn 200-daags gemiddelde -> TQQQ kopen/houden
  - Duidelijk ONDER dat gemiddelde -> TQQQ verkopen, in cash.  (Dit ontwijkt de grootste crashes.)
  - Noodrem: staat TQQQ meer dan 25% onder de aankoopprijs -> verkopen en 10 dagen niet opnieuw kopen.

Draait 1x per dag vlak voor de Amerikaanse beurs sluit.
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
SYMBOL = "TQQQ"            # wat hij koopt (eigen aandeel: geen andere bot handelt hierin)
SIGNAL = "QQQ"             # waar hij naar kijkt (alleen koersdata, wordt niet gekocht)
SMA_DAYS = 200
BUFFER = 0.01              # 1% marge rond het gemiddelde
STOP_LOSS = 0.25           # noodrem bij 25% verlies
COOLDOWN_DAYS = 10         # zo lang niet opnieuw kopen na de noodrem
DRY_RUN = False
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "hefboomtrend_log.csv")
STATE_FILE = os.path.join(HERE, "state.json")


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


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def signal_closes():
    start = (date.today() - timedelta(days=SMA_DAYS * 2)).isoformat()
    q = urllib.parse.urlencode({"timeframe": "1Day", "start": start, "limit": 1000,
                                "adjustment": "all", "feed": "iex"})
    bars = (api("GET", f"{DATA_URL}/v2/stocks/{SIGNAL}/bars?{q}") or {}).get("bars") or []
    return [b["c"] for b in bars]


def decide(closes, has_position, loss, cooling):
    """Geeft (actie, uitleg). loss = huidig verlies als fractie (0.3 = 30% verlies)."""
    if has_position and loss is not None and loss >= STOP_LOSS:
        return "noodrem", f"TQQQ staat {loss:.0%} onder de aankoopprijs -> noodrem"
    if len(closes) < SMA_DAYS:
        return "wacht", f"te weinig data ({len(closes)} dagen)"
    sma = sum(closes[-SMA_DAYS:]) / SMA_DAYS
    price = closes[-1]
    info = f"Nasdaq-100 {price:.2f} vs 200d-gem. {sma:.2f} ({price / sma - 1:+.1%})"
    if price > sma * (1 + BUFFER):
        if has_position:
            return "houd", info + " -> trend omhoog, vasthouden"
        if cooling:
            return "wacht", info + " -> trend omhoog, maar noodrem-pauze loopt nog"
        return "koop", info + " -> trend omhoog, TQQQ kopen"
    if price < sma * (1 - BUFFER):
        return ("verkoop", info + " -> trend omlaag, uitstappen") if has_position else ("cash", info + " -> trend omlaag, in cash blijven")
    return "houd", info + " -> vlak bij het gemiddelde, niets doen"


def log(actie, detail):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,dry_run,detail\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{SYMBOL},{actie},{DRY_RUN},\"{detail}\"\n")


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh in de hoofdmap.")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock["is_open"] and not DRY_RUN:
        print("Beurs is dicht, niets gedaan.")
        return

    state = load_state()
    cooling = state.get("pauze_tot", "") > date.today().isoformat()
    pos = api("GET", f"{TRADE_URL}/v2/positions/{SYMBOL}")
    loss = None
    if pos:
        entry, now = float(pos["avg_entry_price"]), float(pos["current_price"])
        loss = max(0.0, 1 - now / entry)

    actie, uitleg = decide(signal_closes(), pos is not None, loss, cooling)
    print(f"{SYMBOL}: {actie.upper()} ({uitleg})")

    if DRY_RUN:
        print("(DRY_RUN staat aan: er is niets gekocht of verkocht.)")
        return
    if actie == "koop":
        api("POST", f"{TRADE_URL}/v2/orders", {
            "symbol": SYMBOL, "notional": f"{BUDGET:.2f}",
            "side": "buy", "type": "market", "time_in_force": "day",
        })
    elif actie in ("verkoop", "noodrem"):
        api("DELETE", f"{TRADE_URL}/v2/positions/{SYMBOL}")
        if actie == "noodrem":
            state["pauze_tot"] = (date.today() + timedelta(days=COOLDOWN_DAYS * 7 // 5)).isoformat()
            save_state(state)
    if actie in ("koop", "verkoop", "noodrem"):
        log(actie, uitleg)


if __name__ == "__main__":
    main()
