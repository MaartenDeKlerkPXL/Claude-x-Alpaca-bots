#!/bin/bash
# Laat de momentumjager-bot automatisch draaien: elke werkdag om 15:55, kiest 1x per week opnieuw (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="55 15 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:momentumjager"
( crontab -l 2>/dev/null | grep -v '# bot:momentumjager' ; echo "$LINE" ) | crontab -
echo "momentumjager gepland: elke werkdag om 15:55, kiest 1x per week opnieuw."
echo "Resultaten in bots/momentumjager/bot.log. Stoppen kan met: bots/momentumjager/schedule_off.sh"
