# Claude x Alpaca bots

Simpele tradingbots voor een **Alpaca paper account** (nepgeld), gemaakt samen met Claude, met een dashboard op GitHub Pages.

> Alles hier handelt alleen op paper trading. De scripts hebben het paper-adres vast in de code staan en kunnen geen echt geld gebruiken.

## Wat zit erin

| Map | Wat |
|---|---|
| `bots/trendbot/` | Koopt SPY en QQQ als de koers boven het 200-daags gemiddelde staat, verkoopt eronder. Draait elk uur. |
| `bots/scalper/` | Koopt korte oplevingen in IWM met winst-order (+0,20%) en stop-loss (-0,15%). Draait doorlopend tijdens de beurs. |
| `docs/` | Het dashboard (GitHub Pages). De botlijst staat in `docs/bots.js`. |
| `setup.sh` | Slaat je API-sleutels op in `keys.env` (komt nooit op GitHub). |

## Installeren op je Mac

```bash
git clone https://github.com/MaartenDeKlerkPXL/Claude-x-Alpaca-bots.git
cd Claude-x-Alpaca-bots
./setup.sh                          # sleutels van je PAPER account invullen
bots/trendbot/schedule_on.sh        # trendbot elk uur automatisch
bots/scalper/scalp_on.sh            # scalper elke werkdag vanaf 15:35
```

Uitzetten kan met `bots/trendbot/schedule_off.sh` en `bots/scalper/scalp_off.sh`. Je Mac moet tijdens de beurs (15:30 tot 22:00) aanstaan.

## Dashboard

Open de GitHub Pages-link van deze repo en vul daar de sleutels van je paper account in. Ze worden alleen in je eigen browser bewaard. Het dashboard leest alleen en kan niets kopen of verkopen.

## Een nieuwe bot toevoegen

Open Claude met deze repo en vraag bijvoorbeeld: *"maak een nieuwe bot die koopt bij een dip in AAPL"*. Claude volgt de stappen in `CLAUDE.md`: een eigen map in `bots/`, eigen aandelen, en een regel in `docs/bots.js` zodat hij op het dashboard verschijnt.
