#!/bin/bash
# Laat de sectorrotatie-bot automatisch draaien: elke werkdag om 15:45 (wisselt alleen 1x per maand) (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="45 15 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:sectorrotatie"
( crontab -l 2>/dev/null | grep -v '# bot:sectorrotatie' ; echo "$LINE" ) | crontab -
echo "sectorrotatie gepland: elke werkdag om 15:45 (wisselt alleen 1x per maand)."
echo "Resultaten in bots/sectorrotatie/bot.log. Stoppen kan met: bots/sectorrotatie/schedule_off.sh"
