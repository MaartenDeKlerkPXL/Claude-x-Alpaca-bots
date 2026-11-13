#!/bin/bash
# Eenmalig: slaat je Alpaca PAPER API-keys op in keys.env (staat in .gitignore)
# en test of ze werken. Alle bots in bots/ gebruiken dit bestand.
cd "$(dirname "$0")" || exit 1

echo "Plak je Alpaca PAPER API Key ID (begint met PK) en druk op Enter:"
read -r KEY
echo "Plak je Alpaca PAPER Secret Key en druk op Enter (je ziet niets verschijnen, dat klopt):"
read -rs SECRET
echo
if [ -z "$KEY" ] || [ -z "$SECRET" ]; then echo "Key of secret is leeg. Probeer opnieuw: ./setup.sh"; exit 1; fi

printf 'export ALPACA_KEY_ID="%s"\nexport ALPACA_SECRET="%s"\n' "$KEY" "$SECRET" > keys.env
chmod 600 keys.env
echo "Keys opgeslagen in keys.env (alleen leesbaar voor jou, gaat nooit naar GitHub)."

CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "APCA-API-KEY-ID: $KEY" -H "APCA-API-SECRET-KEY: $SECRET" https://paper-api.alpaca.markets/v2/account)
if [ "$CODE" = "200" ]; then echo "Verbinding met je paper account werkt."; else echo "Alpaca gaf code $CODE. Kloppen de keys van je PAPER account?"; fi
