# Claude x Alpaca bots

Simpele tradingbots voor een **Alpaca paper account** (nepgeld), gemaakt samen met Claude, met een dashboard op GitHub Pages.

> Alles hier handelt alleen op paper trading. De scripts hebben het paper-adres vast in de code staan en kunnen geen echt geld gebruiken.

## Wat zit erin

| Map | Wat |
|---|---|
| `bots/trendbot/` | Koopt SPY en QQQ als de koers boven het 200-daags gemiddelde staat, verkoopt eronder. Draait elk uur. |
| `bots/scalper/` | Koopt korte oplevingen in IWM met winst-order (+0,20%) en stop-loss (-0,15%). Draait doorlopend tijdens de beurs. |
| `bots/benchmark/` | De meetlat: koopt 1 keer voor $1.000 VOO (S&P 500) en houdt dat vast. |
| `bots/dipkoper/` | Koopt DIA na een flinke dip als de trend omhoog is, verkoopt bij herstel, 5% verlies of na 10 dagen. |
| `bots/sectorrotatie/` | Zet 1x per maand het geld in de 2 sterkste sector-ETF's van de afgelopen 3 maanden. |
| `bots/cryptotrend/` | Houdt bitcoin vast boven het 50-daags gemiddelde, anders cash. Draait ook in het weekend. |
| `docs/` | Het dashboard (GitHub Pages). De botlijst staat in `docs/bots.js`. |
| `setup.sh` | Slaat je API-sleutels op in `keys.env` (komt nooit op GitHub). |

## Installeren op je Mac

```bash
git clone https://github.com/MaartenDeKlerkPXL/Claude-x-Alpaca-bots.git
cd Claude-x-Alpaca-bots
./setup.sh                          # sleutels van je PAPER account invullen
bots/trendbot/schedule_on.sh        # trendbot elk uur automatisch
bots/scalper/scalp_on.sh            # scalper elke werkdag vanaf 15:35
bots/benchmark/schedule_on.sh       # meetlat: koopt 1 keer VOO
bots/dipkoper/schedule_on.sh        # dip-koper: elke werkdag vlak voor sluiting
bots/sectorrotatie/schedule_on.sh   # sector-rotatie: wisselt 1x per maand
bots/cryptotrend/schedule_on.sh     # crypto-trend: elke dag, ook in het weekend
```

Uitzetten kan per bot met het `schedule_off.sh`- of `scalp_off.sh`-script in zijn map. Je Mac moet tijdens de beurs (15:30 tot 22:00) aanstaan.

## Dashboard

Open de GitHub Pages-link van deze repo en vul daar de sleutels van je paper account in. Ze worden alleen in je eigen browser bewaard. Het dashboard leest alleen en kan niets kopen of verkopen.

## Een nieuwe bot toevoegen

Open Claude met deze repo en vraag bijvoorbeeld: *"maak een nieuwe bot die koopt bij een dip in AAPL"*. Claude volgt de stappen in `CLAUDE.md`: een eigen map in `bots/`, eigen aandelen, en een regel in `docs/bots.js` zodat hij op het dashboard verschijnt.
