#!/bin/bash
# Laat de bot elk uur draaien terwijl de Amerikaanse beurs open is (Mac moet aanstaan).
# Tijden (NL): 15:45, 16:45, 17:45, 18:45, 19:45, 20:45, 21:45 op werkdagen.
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="45 15-21 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # trading-bot"

( crontab -l 2>/dev/null | grep -v '# trading-bot' ; echo "$LINE" ) | crontab -
echo "Gepland: elk uur van 15:45 tot 21:45 op werkdagen."
echo "Resultaten komen in bot.log en trades_log.csv. Stoppen kan met: ./schedule_off.sh"
