"""
DIP-KOPER voor een Alpaca PAPER account (mean reversion, de bekende "RSI-2"-aanpak).

Strategie:
  KOPEN  als de langetermijntrend omhoog is (koers boven het 200-daags gemiddelde)
         EN de koers de laatste dagen hard is gezakt (RSI over 2 dagen onder 10).
  VERKOPEN zodra een van deze dingen gebeurt:
         - de koers is teruggeveerd boven het 5-daags gemiddelde  (het normale einde)
         - het verlies is groter dan 5%                            (stop-loss)
         - de positie staat er al 10 handelsdagen                  (tijdslimiet)

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
BUDGET = 1000.00        # Max. bedrag per trade in dollars
SYMBOL = "DIA"          # Dow Jones ETF (eigen aandeel: geen andere bot gebruikt dit)
RSI_DAYS = 2
RSI_BUY_BELOW = 10      # Kopen als RSI(2) hieronder zakt
TREND_DAYS = 200        # Alleen kopen boven het 200-daags gemiddelde
EXIT_SMA_DAYS = 5       # Verkopen als de koers boven het 5-daags gemiddelde komt
STOP_LOSS = 0.05        # Verkopen bij meer dan 5% verlies
MAX_HOLD_DAYS = 10      # Verkopen na 10 handelsdagen
DRY_RUN = False         # True = alleen laten zien wat hij zou doen
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dipkoper_log.csv")


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


def daily_bars():
    """Slotkoersen en datums van ongeveer het laatste anderhalf jaar (vandaag = laatste)."""
    start = (date.today() - timedelta(days=TREND_DAYS * 2)).isoformat()
    q = urllib.parse.urlencode({"timeframe": "1Day", "start": start, "limit": 1000,
                                "adjustment": "all", "feed": "iex"})
    bars = (api("GET", f"{DATA_URL}/v2/stocks/{SYMBOL}/bars?{q}") or {}).get("bars") or []
    return [b["c"] for b in bars], [b["t"][:10] for b in bars]


def rsi(closes, n):
    """RSI volgens Wilder. Geeft de laatste waarde (0-100)."""
    if len(closes) < n + 1:
        return None
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_g = sum(gains[:n]) / n
    avg_l = sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        avg_g = (avg_g * (n - 1) + g) / n
        avg_l = (avg_l * (n - 1) + l) / n
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def sma(values, n):
    return sum(values[-n:]) / n


def decide(closes, position, entry_price, days_held):
    """Bepaal de actie. Geeft (actie, uitleg) terug."""
    if len(closes) < TREND_DAYS:
        return "wacht", f"te weinig data ({len(closes)} dagen)"
    price = closes[-1]
    r = rsi(closes, RSI_DAYS)
    trend = sma(closes, TREND_DAYS)
    exit_line = sma(closes, EXIT_SMA_DAYS)
    info = f"koers {price:.2f}, RSI(2) {r:.1f}, 200d-gem. {trend:.2f}, 5d-gem. {exit_line:.2f}"

    if position:
        if price > exit_line:
            return "verkoop", info + " -> teruggeveerd boven het 5-daags gemiddelde"
        if entry_price and price < entry_price * (1 - STOP_LOSS):
            return "verkoop", info + f" -> stop-loss, meer dan {STOP_LOSS:.0%} verlies"
        if days_held is not None and days_held >= MAX_HOLD_DAYS:
            return "verkoop", info + f" -> al {days_held} handelsdagen vast, tijdslimiet"
        return "houd", info + f" -> wacht op opleving (dag {days_held or 0} van max. {MAX_HOLD_DAYS})"

    if price > trend and r < RSI_BUY_BELOW:
        return "koop", info + " -> trend omhoog en flinke dip"
    if price <= trend:
        return "wacht", info + " -> trend omlaag, geen dips kopen"
    return "wacht", info + " -> geen dip"


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

    closes, dates = daily_bars()
    pos = api("GET", f"{TRADE_URL}/v2/positions/{SYMBOL}")
    entry_price = days_held = None
    if pos:
        entry_price = float(pos["avg_entry_price"])
        q = urllib.parse.urlencode({"status": "closed", "symbols": SYMBOL, "side": "buy", "limit": 1})
        last_buy = next((o for o in (api("GET", f"{TRADE_URL}/v2/orders?{q}") or []) if o.get("filled_at")), None)
        if last_buy:
            bought_on = last_buy["filled_at"][:10]
            days_held = sum(1 for d in dates if d > bought_on)

    actie, uitleg = decide(closes, pos is not None, entry_price, days_held)
    print(f"{SYMBOL}: {actie.upper()} ({uitleg})")

    if not DRY_RUN:
        if actie == "koop":
            api("POST", f"{TRADE_URL}/v2/orders", {
                "symbol": SYMBOL, "notional": f"{BUDGET:.2f}",
                "side": "buy", "type": "market", "time_in_force": "day",
            })
        elif actie == "verkoop":
            api("DELETE", f"{TRADE_URL}/v2/positions/{SYMBOL}")
    if actie in ("koop", "verkoop"):
        log(actie, uitleg)
    if DRY_RUN:
        print("(DRY_RUN staat aan: er is niets gekocht of verkocht.)")


if __name__ == "__main__":
    main()
