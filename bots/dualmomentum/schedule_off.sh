#!/bin/bash
# Haalt de dualmomentum-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:dualmomentum' | crontab -
echo "dualmomentum draait niet meer automatisch."
