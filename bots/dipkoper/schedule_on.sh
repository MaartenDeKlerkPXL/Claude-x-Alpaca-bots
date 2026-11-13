#!/bin/bash
# Laat de dipkoper-bot automatisch draaien: elke werkdag om 20:45 en 21:45, vlak voor de beurs sluit (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="45 20,21 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:dipkoper"
( crontab -l 2>/dev/null | grep -v '# bot:dipkoper' ; echo "$LINE" ) | crontab -
echo "dipkoper gepland: elke werkdag om 20:45 en 21:45, vlak voor de beurs sluit."
echo "Resultaten in bots/dipkoper/bot.log. Stoppen kan met: bots/dipkoper/schedule_off.sh"
