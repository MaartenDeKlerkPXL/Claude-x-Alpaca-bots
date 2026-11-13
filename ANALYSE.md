# Analyse van de bots (voor Claude)

Gebruik dit als Maarten vraagt om "de analyse" of als de maandelijkse geplande taak draait.

**Alleen lezen.** Plaats nooit orders, sluit geen posities en verander geen accountinstellingen.

## 1. Data verzamelen
- Via de Alpaca Paper Trading-connector: `get_account_info`, `get_all_positions`, `get_orders` (status all, nested true, direction desc, limit 500; pagineer met `until` tot alles binnen is). Zo nodig `get_stock_bars` / `get_crypto_bars` voor koersen.
- Welke bot welke aandelen heeft staat in `docs/bots.js`. Crypto heet `BTC/USD` bij orders en `BTCUSD` bij posities: behandel dat als hetzelfde.
- Zet de data in bestanden en reken in code, niet uit het hoofd. De rekenregels van het dashboard staan in `docs/app.js` (`botStats`).

## 2. Per bot uitrekenen
- Totaal resultaat (gerealiseerd + open) en rendement op het budget van $1.000
- Aantal trades, winrate, gemiddelde winst en verlies per trade, grootste verlies
- Sinds wanneer actief
- **Vergelijken met de Benchmark-bot** (VOO kopen en vasthouden) over dezelfde periode

## 3. Controleren
- Klopt elke trade met de regels in het script van de bot?
- Dagen dat een bot had moeten draaien maar niets deed (bijv. Mac in slaap)?
- Dubbele of vreemde orders?

## 4. Rapport
- `rapporten/JJJJ-MM.md`: tabel per bot naast de benchmark, wat goed ging, wat niet, en per bot hoogstens 2 verbetervoorstellen met onderbouwing uit de data.
- Eerlijk zijn: onder ongeveer 20 trades is een resultaat vooral toeval. Geen beloftes over toekomstige winst.
- Alleen het rapport naar `main` pushen.

## 5. Verbeteringen
- Nooit direct op `main`. Branch `verbetering/JJJJ-MM`, code volgens `CLAUDE.md`, beslisregels testen met nepkoersen, pull request met uitleg. Maarten beslist of hij merget.
- Daarna: `git pull` op de Mac is genoeg, de planning hoeft niet opnieuw.

## 6. Samenvatting voor Maarten
3 tot 5 regels: resultaat per bot tegenover de benchmark, de belangrijkste les, links naar het rapport en de pull request.
