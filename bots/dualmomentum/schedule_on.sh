#!/bin/bash
# Laat de dualmomentum-bot automatisch draaien: elke werkdag om 15:52, wisselt hooguit 1x per maand (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="52 15 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:dualmomentum"
( crontab -l 2>/dev/null | grep -v '# bot:dualmomentum' ; echo "$LINE" ) | crontab -
echo "dualmomentum gepland: elke werkdag om 15:52, wisselt hooguit 1x per maand."
echo "Resultaten in bots/dualmomentum/bot.log. Stoppen kan met: bots/dualmomentum/schedule_off.sh"
