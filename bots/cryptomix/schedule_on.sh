#!/bin/bash
# Laat de cryptomix-bot automatisch draaien: elke dag om 12:47, ook in het weekend (Mac moet aanstaan).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="47 12 * * * cd \"$DIR\" && ./run.sh >> bot.log 2>&1 # bot:cryptomix"
( crontab -l 2>/dev/null | grep -v '# bot:cryptomix' ; echo "$LINE" ) | crontab -
echo "cryptomix gepland: elke dag om 12:47, ook in het weekend."
echo "Resultaten in bots/cryptomix/bot.log. Stoppen kan met: bots/cryptomix/schedule_off.sh"
