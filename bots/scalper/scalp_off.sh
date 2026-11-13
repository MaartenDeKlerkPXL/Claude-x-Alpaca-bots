#!/bin/bash
# Haalt de scalper uit de planning en stopt hem als hij nu draait.
crontab -l 2>/dev/null | grep -v '# scalper' | crontab -
pkill -f scalper.py && echo "Draaiende scalper gestopt."
echo "Scalper uit de planning gehaald. (Open posities sluit je in het Alpaca-dashboard.)"
