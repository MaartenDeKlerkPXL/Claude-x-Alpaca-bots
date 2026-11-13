#!/bin/bash
# Laat de benchmark-bot automatisch draaien: elke werkdag om 15:45 (koopt 1 keer, daarna niets meer) (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="45 15 * * 1-5 cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:benchmark"
( crontab -l 2>/dev/null | grep -v '# bot:benchmark' ; echo "$LINE" ) | crontab -
echo "benchmark gepland: elke werkdag om 15:45 (koopt 1 keer, daarna niets meer)."
echo "Resultaten in bots/benchmark/bot.log. Stoppen kan met: bots/benchmark/schedule_off.sh"
