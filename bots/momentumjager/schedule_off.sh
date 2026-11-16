#!/bin/bash
# Haalt de momentumjager-bot uit de planning.
crontab -l 2>/dev/null | grep -v '# bot:momentumjager' | crontab -
echo "momentumjager draait niet meer automatisch."
