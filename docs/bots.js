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
  }
];
