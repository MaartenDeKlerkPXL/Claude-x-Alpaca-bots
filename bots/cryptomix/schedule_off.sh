#!/bin/bash
# Haalt de cryptomix-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:cryptomix' | crontab -
echo "cryptomix draait niet meer automatisch."
