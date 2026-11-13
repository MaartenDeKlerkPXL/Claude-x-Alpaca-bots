#!/bin/bash
# Haalt de automatische planning weer weg.
crontab -l 2>/dev/null | grep -v '# trading-bot' | crontab -
echo "Planning verwijderd. De bot draait niet meer automatisch."
