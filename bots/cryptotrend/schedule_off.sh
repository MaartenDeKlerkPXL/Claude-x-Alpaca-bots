#!/bin/bash
# Haalt de cryptotrend-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:cryptotrend' | crontab -
echo "cryptotrend draait niet meer automatisch."
