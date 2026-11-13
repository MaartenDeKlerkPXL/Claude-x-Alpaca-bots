#!/bin/bash
# Laat de cryptotrend-bot automatisch draaien: elke dag om 12:17, ook in het weekend (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="17 12 * * * cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:cryptotrend"
( crontab -l 2>/dev/null | grep -v '# bot:cryptotrend' ; echo "$LINE" ) | crontab -
echo "cryptotrend gepland: elke dag om 12:17, ook in het weekend."
echo "Resultaten in bots/cryptotrend/bot.log. Stoppen kan met: bots/cryptotrend/schedule_off.sh"
