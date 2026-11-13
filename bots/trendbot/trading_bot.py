"""
Simpele trend-bot voor een Alpaca PAPER account.

Strategie (1 regel):
  - Staat de koers BOVEN het gemiddelde van de laatste 200 dagen?  -> kopen/vasthouden
  - Staat de koers ONDER dat gemiddelde?                           -> verkopen, in cash blijven

Draait elk uur terwijl de Amerikaanse beurs open is
(15:30-22:00 Nederlandse tijd; rond de zomer/wintertijdwissel een uur eerder).

Benodigd: alleen Python 3 (geen extra pakketten).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

# ============ INSTELLINGEN (pas deze aan) ============
BUDGET = 1000.00            # Max. bedrag in dollars dat de bot ooit gebruikt
SYMBOLS = ["SPY", "QQQ"]    # SPY = S&P 500 ETF, QQQ = Nasdaq-100 ETF
SMA_DAYS = 200              # Aantal dagen voor het gemiddelde
BUFFER = 0.01               # 1% marge rond het gemiddelde, voorkomt heen-en-weer kopen/verkopen
DRY_RUN = False             # True = alleen laten zien wat hij zou doen. Zet op False om echt (paper) te handelen.

# API-keys van je PAPER account (Alpaca dashboard -> API Keys -> Generate).
# Liefst als omgevingsvariabele, anders hier invullen. Deel deze nooit.
KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
# =====================================================

TRADE_URL = "https://paper-api.alpaca.markets"   # Bewust vast: dit script kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades_log.csv")


def api(method, url, body=None):
    """Doe een verzoek naar Alpaca en geef het JSON-antwoord terug (None bij 404)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "APCA-API-KEY-ID": KEY_ID,
        "APCA-API-SECRET-KEY": SECRET,
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


def closing_prices(symbol):
    """Haal de slotkoersen van ongeveer het laatste anderhalf jaar op."""
    start = (date.today() - timedelta(days=SMA_DAYS * 2)).isoformat()
    url = (f"{DATA_URL}/v2/stocks/{symbol}/bars?timeframe=1Day&start={start}"
           f"&limit=1000&adjustment=all&feed=iex")
    bars = (api("GET", url) or {}).get("bars") or []
    return [b["c"] for b in bars]


def decide(prices, position_value, target):
    """Bepaal de actie. Geeft (actie, bedrag, uitleg) terug."""
    if len(prices) < SMA_DAYS:
        return "wacht", 0, f"te weinig data ({len(prices)} dagen)"
    sma = sum(prices[-SMA_DAYS:]) / SMA_DAYS
    price = prices[-1]
    uitleg = f"koers {price:.2f} vs {SMA_DAYS}-daags gemiddelde {sma:.2f}"
    if price > sma * (1 + BUFFER):
        tekort = target - position_value
        if tekort > target * 0.10:          # pas bijkopen bij >10% verschil, scheelt onnodige trades
            return "koop", round(tekort, 2), uitleg + " -> trend omhoog"
        return "houd", 0, uitleg + " -> trend omhoog, positie is al goed"
    if price < sma * (1 - BUFFER):
        if position_value > 0:
            return "verkoop", position_value, uitleg + " -> trend omlaag"
        return "cash", 0, uitleg + " -> trend omlaag, blijf in cash"
    return "houd", 0, uitleg + " -> vlak bij het gemiddelde, niets doen"


def log(symbol, actie, bedrag, uitleg):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,bedrag,dry_run,uitleg\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M},{symbol},{actie},{bedrag},{DRY_RUN},\"{uitleg}\"\n")


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys gevonden. Vul ALPACA_KEY_ID en ALPACA_SECRET in.")

    account = api("GET", f"{TRADE_URL}/v2/account")
    print(f"Paper account: cash ${float(account['cash']):,.2f}, "
          f"waarde ${float(account['portfolio_value']):,.2f}")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock["is_open"] and not DRY_RUN:
        print("Beurs is dicht, niets gedaan.")
        return

    target = BUDGET / len(SYMBOLS)
    for symbol in SYMBOLS:
        pos = api("GET", f"{TRADE_URL}/v2/positions/{symbol}")
        position_value = float(pos["market_value"]) if pos else 0.0
        actie, bedrag, uitleg = decide(closing_prices(symbol), position_value, target)
        print(f"{symbol}: {actie.upper()} {f'${bedrag:,.2f}' if bedrag else ''} ({uitleg})")

        if not DRY_RUN:
            if actie == "koop":
                api("POST", f"{TRADE_URL}/v2/orders", {
                    "symbol": symbol, "notional": f"{bedrag:.2f}",
                    "side": "buy", "type": "market", "time_in_force": "day",
                })
            elif actie == "verkoop":
                api("DELETE", f"{TRADE_URL}/v2/positions/{symbol}")
        log(symbol, actie, bedrag, uitleg)

    if DRY_RUN:
        print("\n(DRY_RUN staat aan: er is niets gekocht of verkocht.)")


if __name__ == "__main__":
    main()
