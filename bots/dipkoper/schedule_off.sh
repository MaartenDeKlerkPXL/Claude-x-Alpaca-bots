#!/bin/bash
# Haalt de dipkoper-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:dipkoper' | crontab -
echo "dipkoper draait niet meer automatisch."
