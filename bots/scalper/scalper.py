"""
Simpele SCALPER voor een Alpaca PAPER account.

Hoe hij werkt (elke minuut):
  - Kijkt naar 1-minuut-koersen van vandaag.
  - KOOP-signaal: de snelle lijn (EMA 9) kruist omhoog door de trage lijn (EMA 21)
    EN de koers staat boven de VWAP (gemiddelde prijs van vandaag).
  - Bij een koop plaatst hij meteen automatisch:
        winst nemen  bij +0,20%
        stop-loss    bij -0,15%
    Alpaca voert die zelf uit, ook als het script even hapert.
  - Veiligheid: max. aantal trades per dag, dagelijkse verliesgrens,
    en 15 minuten voor sluiting alles dicht (nooit 's nachts vasthouden).

Gebruikt andere aandelen dan de trendbot (SPY/QQQ), zodat ze elkaar niet storen.
Start via scalp.sh; hij stopt vanzelf als de beurs sluit.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    sys.exit("Python 3.9 of nieuwer nodig.")

# ============ INSTELLINGEN ============
BUDGET = 1000.00              # Max. bedrag per trade (hele aandelen, dus iets minder)
SYMBOLS = ["IWM"]             # IWM = Russell 2000 ETF. NIET SPY/QQQ gebruiken (die zijn van de trendbot)
TAKE_PROFIT = 0.0020          # +0,20%
STOP_LOSS = 0.0015            # -0,15%
EMA_FAST, EMA_SLOW = 9, 21
MAX_TRADES_PER_DAY = 20
MAX_LOSS_PER_DAY = 20.00      # Stopt voor vandaag als de scalper $20 verloren heeft
CHECK_EVERY_SEC = 60
STOP_BEFORE_CLOSE_MIN = 15
DRY_RUN = False               # True = alleen signalen tonen, niets kopen
# =====================================

KEY_ID = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET", "")
TRADE_URL = "https://paper-api.alpaca.markets"   # Vast: kan geen echt geld gebruiken
DATA_URL = "https://data.alpaca.markets"
NY = ZoneInfo("America/New_York")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scalp_log.csv")


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
        print(f"  Alpaca-fout {e.code}: {e.read().decode()}")
        return None
    except urllib.error.URLError as e:
        print(f"  Netwerkfout: {e}")
        return None


def say(text):
    print(f"{datetime.now():%H:%M:%S} {text}", flush=True)


def log(symbol, actie, detail):
    nieuw = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if nieuw:
            f.write("tijd,symbool,actie,detail\n")
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S},{symbol},{actie},\"{detail}\"\n")


def ema(values, n):
    k = 2 / (n + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def today_open_utc():
    now_ny = datetime.now(NY)
    return now_ny.replace(hour=9, minute=30, second=0, microsecond=0).astimezone(timezone.utc)


def minute_bars(symbol):
    start = today_open_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    q = urllib.parse.urlencode({"timeframe": "1Min", "start": start, "limit": 1000, "feed": "iex"})
    res = api("GET", f"{DATA_URL}/v2/stocks/{symbol}/bars?{q}") or {}
    return res.get("bars") or []


def signal(bars):
    """Geeft (koop?, uitleg, laatste koers) terug."""
    if len(bars) < EMA_SLOW + 2:
        return False, f"wacht op data ({len(bars)} minuten)", None
    closes = [b["c"] for b in bars]
    fast, slow = ema(closes, EMA_FAST), ema(closes, EMA_SLOW)
    vol = sum(b["v"] for b in bars)
    vwap = sum(b["vw"] * b["v"] for b in bars) / vol if vol else closes[-1]
    price = closes[-1]
    kruis_omhoog = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
    uitleg = f"koers {price:.2f}, EMA{EMA_FAST} {fast[-1]:.2f}, EMA{EMA_SLOW} {slow[-1]:.2f}, VWAP {vwap:.2f}"
    return kruis_omhoog and price > vwap, uitleg, price


def todays_orders(symbol):
    after = today_open_utc() - timedelta(hours=6)
    q = urllib.parse.urlencode({"status": "all", "symbols": symbol, "limit": 500,
                                "after": after.strftime("%Y-%m-%dT%H:%M:%SZ"), "nested": "true"})
    top = api("GET", f"{TRADE_URL}/v2/orders?{q}") or []
    flat = []
    for o in top:
        flat.append(o)
        flat.extend(o.get("legs") or [])
    return flat


def day_stats(symbol):
    """Aantal koop-trades vandaag en totale winst/verlies van de scalper vandaag."""
    orders = todays_orders(symbol)
    buys = sells = 0.0
    trades = 0
    for o in orders:
        qty = float(o.get("filled_qty") or 0)
        if qty <= 0:
            continue
        value = qty * float(o["filled_avg_price"])
        if o["side"] == "buy":
            buys += value
            trades += 1
        else:
            sells += value
    pos = api("GET", f"{TRADE_URL}/v2/positions/{symbol}")
    open_value = float(pos["market_value"]) if pos else 0.0
    return trades, sells + open_value - buys, pos is not None


def has_open_orders(symbol):
    q = urllib.parse.urlencode({"status": "open", "symbols": symbol})
    return bool(api("GET", f"{TRADE_URL}/v2/orders?{q}"))


def close_everything(symbol):
    q = urllib.parse.urlencode({"status": "open", "symbols": symbol, "nested": "true"})
    for o in api("GET", f"{TRADE_URL}/v2/orders?{q}") or []:
        api("DELETE", f"{TRADE_URL}/v2/orders/{o['id']}")
    time.sleep(2)
    if api("GET", f"{TRADE_URL}/v2/positions/{symbol}"):
        api("DELETE", f"{TRADE_URL}/v2/positions/{symbol}")
        say(f"{symbol}: positie gesloten voor het einde van de dag")
        log(symbol, "sluit", "einde dag")


def buy(symbol, price):
    qty = int(BUDGET // price)
    if qty < 1:
        say(f"{symbol}: budget te klein voor 1 aandeel ({price:.2f})")
        return
    tp = round(price * (1 + TAKE_PROFIT), 2)
    sl = round(price * (1 - STOP_LOSS), 2)
    detail = f"{qty} st. @ ~{price:.2f}, winst {tp}, stop {sl}"
    if DRY_RUN:
        say(f"{symbol}: [DRY_RUN] zou kopen: {detail}")
        log(symbol, "signaal", detail)
        return
    res = api("POST", f"{TRADE_URL}/v2/orders", {
        "symbol": symbol, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "day", "order_class": "bracket",
        "take_profit": {"limit_price": f"{tp:.2f}"},
        "stop_loss": {"stop_price": f"{sl:.2f}"},
    })
    if res:
        say(f"{symbol}: GEKOCHT {detail}")
        log(symbol, "koop", detail)


def main():
    if not KEY_ID or not SECRET:
        sys.exit("Geen API-keys. Draai eerst ./setup.sh")

    clock = api("GET", f"{TRADE_URL}/v2/clock")
    if not clock or not clock["is_open"]:
        say("Beurs is dicht. Scalper stopt.")
        return
    close_at = datetime.fromisoformat(clock["next_close"]).astimezone(timezone.utc)
    stop_at = close_at - timedelta(minutes=STOP_BEFORE_CLOSE_MIN)
    say(f"Scalper gestart op {', '.join(SYMBOLS)}. Stopt om {stop_at.astimezone():%H:%M}."
        + (" [DRY_RUN]" if DRY_RUN else ""))

    gestopt = set()
    while datetime.now(timezone.utc) < stop_at:
        for symbol in SYMBOLS:
            if symbol in gestopt:
                continue
            trades, pnl, in_trade = day_stats(symbol)
            if pnl <= -MAX_LOSS_PER_DAY:
                say(f"{symbol}: verliesgrens bereikt (${pnl:.2f}). Klaar voor vandaag.")
                log(symbol, "stop", f"verliesgrens, resultaat {pnl:.2f}")
                close_everything(symbol)
                gestopt.add(symbol)
                continue
            if in_trade or has_open_orders(symbol):
                say(f"{symbol}: in trade, resultaat vandaag ${pnl:+.2f}")
                continue
            if trades >= MAX_TRADES_PER_DAY:
                say(f"{symbol}: max. {MAX_TRADES_PER_DAY} trades bereikt. Klaar voor vandaag.")
                gestopt.add(symbol)
                continue
            koop, uitleg, price = signal(minute_bars(symbol))
            say(f"{symbol}: {'KOOPSIGNAAL' if koop else 'geen signaal'} ({uitleg}) | "
                f"trades {trades}, resultaat ${pnl:+.2f}")
            if koop:
                buy(symbol, price)
        if len(gestopt) == len(SYMBOLS):
            break
        time.sleep(CHECK_EVERY_SEC)

    for symbol in SYMBOLS:
        close_everything(symbol)
        trades, pnl, _ = day_stats(symbol)
        say(f"{symbol}: einde dag. {trades} trades, resultaat ${pnl:+.2f}")
        log(symbol, "einde dag", f"{trades} trades, resultaat {pnl:.2f}")


if __name__ == "__main__":
    main()
