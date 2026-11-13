# Werkafspraken voor Claude in deze repo

Maarten bouwt hier samen met Claude simpele tradingbots voor een Alpaca **paper** account. Antwoord in het Nederlands, houd het simpel en eerlijk (geen beloftes over winst).

## Vaste regels

- Alleen paper trading: `TRADE_URL = "https://paper-api.alpaca.markets"` staat vast in elk botscript. Nooit een live-URL toevoegen.
- Geheimen nooit committen. Sleutels staan in `keys.env` (in `.gitignore`), aangemaakt door `./setup.sh`.
- Alleen Python 3 standaardbibliotheek (geen pip-pakketten), zodat het op een gewone Mac draait.
- Elke bot handelt in **eigen aandelen**. Het dashboard koppelt trades via het aandeel aan een bot, dus twee bots met hetzelfde aandeel geven verkeerde cijfers.
- Elke bot heeft een budget en veiligheidsgrenzen (max. trades per dag en/of dagelijkse verliesgrens).

## Een nieuwe bot toevoegen (stappen)

1. Vraag Maarten wat de bot moet doen, als dat niet duidelijk is. Kies aandelen die nog niet in `docs/bots.js` staan.
2. Maak `bots/<naam>/` met:
   - `<naam>.py` naar het voorbeeld van `bots/trendbot/trading_bot.py` (eenmalig per run) of `bots/scalper/scalper.py` (doorlopende loop). Keys via `ALPACA_KEY_ID` / `ALPACA_SECRET`.
   - `run.sh` dat `keys.env` uit de eigen map of uit `../../keys.env` laadt (zie `bots/trendbot/run.sh`).
   - `schedule_on.sh` / `schedule_off.sh` met een crontab-regel met een eigen tag (`# bot:<naam>`), zodat aan- en uitzetten andere bots niet raakt.
3. Test de beslislogica met nepkoersen (zoals bij de bestaande bots) en controleer de shellscripts met `bash -n`.
4. Voeg de bot toe aan `docs/bots.js` met `name`, `folder`, `symbols`, `budget`, een eigen `color`, `strategy` (één zin) en `schedule`.
5. Commit en push. Het dashboard op GitHub Pages toont de bot daarna vanzelf.
6. Geef Maarten de Terminal-commando's om de bot te starten (`git pull`, daarna het schedule-script).

## Dashboard

`docs/index.html` + `docs/app.js` leest via de Alpaca REST API (alleen GET) account, posities, orders en klok. Rekenwerk staat in `app.js` (`botStats`, `recentTrades`) en is in Node te testen via `module.exports`.

## Analyse

Vraagt Maarten om een analyse van de bots, of draait de maandelijkse geplande taak: volg `ANALYSE.md`. Rapporten komen in `rapporten/`, verbeteringen altijd via een pull request.
