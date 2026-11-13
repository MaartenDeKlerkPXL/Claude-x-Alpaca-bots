#!/bin/bash
# Draait de cryptotrend-bot 1 keer. Wordt ook door de planning gebruikt.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
if [ -f keys.env ]; then source keys.env
elif [ -f ../../keys.env ]; then source ../../keys.env
else echo "Geen keys.env gevonden. Draai eerst ./setup.sh in de hoofdmap"; exit 1; fi
echo "===== $(date '+%Y-%m-%d %H:%M') ====="
python3 cryptotrend.py
