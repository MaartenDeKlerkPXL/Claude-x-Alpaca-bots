#!/bin/bash
# Haalt de hefboomtrend-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:hefboomtrend' | crontab -
echo "hefboomtrend draait niet meer automatisch."
