#!/bin/bash
# Haalt de sectorrotatie-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:sectorrotatie' | crontab -
echo "sectorrotatie draait niet meer automatisch."
