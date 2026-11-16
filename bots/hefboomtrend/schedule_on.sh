#!/bin/bash
# Laat de hefboomtrend-bot automatisch draaien: elke werkdag om 20:40 en 21:40, vlak voor de beurs sluit (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="40 20,21 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:hefboomtrend"
( crontab -l 2>/dev/null | grep -v '# bot:hefboomtrend' ; echo "$LINE" ) | crontab -
echo "hefboomtrend gepland: elke werkdag om 20:40 en 21:40, vlak voor de beurs sluit."
echo "Resultaten in bots/hefboomtrend/bot.log. Stoppen kan met: bots/hefboomtrend/schedule_off.sh"
