#!/bin/bash
# Start de scalper. Hij draait tot 15 min voor beurssluiting en stopt dan vanzelf.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
if [ -f keys.env ]; then source keys.env
elif [ -f ../../keys.env ]; then source ../../keys.env
else echo "Geen keys.env gevonden. Draai eerst ./setup.sh in de hoofdmap"; exit 1; fi
echo "===== $(date '+%Y-%m-%d %H:%M') ====="
# caffeinate houdt de Mac wakker zolang de scalper draait
caffeinate -i python3 scalper.py
