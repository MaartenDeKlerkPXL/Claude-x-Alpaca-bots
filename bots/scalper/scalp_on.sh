#!/bin/bash
# Start de scalper automatisch elke werkdag om 15:35 (beurs open om 15:30 NL-tijd).
DIR="$(cd "$(dirname "$0")" && pwd)"
LINE="35 15 * * 1-5 cd \"$DIR\" && ./scalp.sh >> scalp.log 2>&1 # scalper"
( crontab -l 2>/dev/null | grep -v '# scalper' ; echo "$LINE" ) | crontab -
echo "Scalper gepland: elke werkdag vanaf 15:35 tot 15 min voor sluiting."
echo "Live meekijken: tail -f scalp.log   |   Stoppen: ./scalp_off.sh"
