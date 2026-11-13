#!/bin/bash
# Haalt de benchmark-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:benchmark' | crontab -
echo "benchmark draait niet meer automatisch."
