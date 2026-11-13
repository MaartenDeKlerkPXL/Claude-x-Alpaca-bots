// De botlijst van het dashboard.
// Een nieuwe bot toevoegen = hieronder een blok bij, met een eigen kleur.
// Regel: elke bot handelt in EIGEN aandelen. Zo weet het dashboard bij welke bot een trade hoort.
window.BOTS = [
  {
    name: 'Trendbot',
    folder: 'bots/trendbot',
    symbols: ['SPY', 'QQQ'],
    budget: 1000,
    color: '#3D5AFE',
    strategy: 'Koopt als de koers boven het 200-daags gemiddelde staat en verkoopt als hij er duidelijk onder zakt.',
    schedule: 'elk uur van 15:45 tot 21:45 op werkdagen'
  },
  {
    name: 'Scalper',
    folder: 'bots/scalper',
    symbols: ['IWM'],
    budget: 1000,
    color: '#E0631D',
    strategy: 'Koopt korte oplevingen (EMA 9 kruist EMA 21 boven de VWAP) en verkoopt bij +0,20% winst of -0,15% verlies.',
    schedule: 'doorlopend van 15:35 tot 21:45 op werkdagen'
  },
  {
    name: 'Benchmark',
    folder: 'bots/benchmark',
    symbols: ['VOO'],
    budget: 1000,
    color: '#7A8599',
    strategy: 'De meetlat: koopt 1 keer voor $1.000 een S&P 500-indexfonds en houdt dat vast. Doen de andere bots het beter?',
    schedule: 'elke werkdag om 15:45 tot hij gekocht heeft'
  },
  {
    name: 'Dip-koper',
    folder: 'bots/dipkoper',
    symbols: ['DIA'],
    budget: 1000,
    color: '#0E9F8E',
    strategy: 'Koopt na een flinke dip (RSI-2 onder 10) als de trend omhoog is, en verkoopt bij herstel, 5% verlies of na 10 dagen.',
    schedule: 'elke werkdag om 20:45 en 21:45'
  },
  {
    name: 'Sector-rotatie',
    folder: 'bots/sectorrotatie',
    symbols: ['XLK', 'XLE', 'XLF', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC'],
    budget: 1000,
    color: '#9C4DCC',
    strategy: 'Zet 1x per maand het geld in de 2 sectoren die de afgelopen 3 maanden het hardst stegen (alleen als ze echt stegen).',
    schedule: 'elke werkdag om 15:45, wisselt 1x per maand'
  },
  {
    name: 'Crypto-trend',
    folder: 'bots/cryptotrend',
    symbols: ['BTC/USD'],
    budget: 1000,
    color: '#D99A00',
    strategy: 'Houdt bitcoin vast als de koers duidelijk boven het 50-daags gemiddelde staat, anders cash.',
    schedule: 'elke dag om 12:17, ook in het weekend'
  }
];
