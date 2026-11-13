/* Dashboard voor de Claude x Alpaca bots.
   Leest alleen (GET) van je Alpaca PAPER account. De sleutels blijven in deze browser. */
(function () {
  'use strict';

  var API = 'https://paper-api.alpaca.markets'; // vast: dit dashboard kan nooit bij een echt-geld-account
  var STORE = 'cab-keys';
  var REFRESH_MS = 60000;

  // ---------- Rekenwerk (los van de pagina, zodat het te testen is) ----------
  // Alpaca schrijft crypto als 'BTC/USD' bij orders en 'BTCUSD' bij posities: gelijk trekken.
  function norm(sym) { return String(sym || '').replace('/', '').toUpperCase(); }
  function flattenOrders(orders) {
    var rows = [];
    orders.forEach(function (o) {
      [o].concat(o.legs || []).forEach(function (x) {
        rows.push({
          id: x.id, symbol: x.symbol, side: x.side, type: x.type, role: x.group_role || '',
          status: x.status, filled_qty: Number(x.filled_qty || 0),
          price: x.filled_avg_price == null ? null : Number(x.filled_avg_price),
          filled_at: x.filled_at || null
        });
      });
    });
    return rows;
  }

  function fills(rows) {
    return rows
      .filter(function (r) { return r.filled_qty > 0 && r.price !== null && r.filled_at; })
      .sort(function (a, b) { return a.filled_at < b.filled_at ? -1 : a.filled_at > b.filled_at ? 1 : 0; });
  }

  // Per aandeel: gemiddelde aankoopprijs bijhouden, winst/verlies bij elke verkoop.
  function perSymbol(fillRows) {
    var per = {};
    fillRows.forEach(function (f) {
      var s = per[norm(f.symbol)] || (per[norm(f.symbol)] = { qty: 0, cost: 0, realized: 0, trip: 0, trips: 0, wins: 0, entries: 0, last: null });
      s.last = f.filled_at;
      if (f.side === 'buy') {
        if (s.qty < 1e-9) s.entries++;
        s.qty += f.filled_qty; s.cost += f.filled_qty * f.price;
      } else {
        var avg = s.qty > 0 ? s.cost / s.qty : f.price;
        var sold = Math.min(f.filled_qty, s.qty);
        var pnl = (f.price - avg) * sold;
        s.realized += pnl; s.trip += pnl; s.cost -= avg * sold; s.qty -= sold;
        if (s.qty < 1e-6) { s.trips++; if (s.trip > 0) s.wins++; s.trip = 0; s.qty = 0; s.cost = 0; }
      }
    });
    return per;
  }

  function r2(x) { return Math.round(x * 100) / 100; }

  function botStats(bots, positions, orderRows) {
    var per = perSymbol(fills(orderRows));
    return bots.map(function (b) {
      var t = { realized: 0, unrealized: 0, value: 0, invested: 0, trips: 0, wins: 0, entries: 0, last: null };
      b.symbols.forEach(function (sym) {
        var s = per[norm(sym)];
        if (s) {
          t.realized += s.realized; t.trips += s.trips; t.wins += s.wins; t.entries += s.entries;
          if (s.last && (!t.last || s.last > t.last)) t.last = s.last;
        }
        positions.filter(function (p) { return norm(p.symbol) === norm(sym); }).forEach(function (p) {
          t.unrealized += Number(p.unrealized_pl); t.value += Number(p.market_value); t.invested += Number(p.cost_basis);
        });
      });
      return {
        bot: b, realized: r2(t.realized), unrealized: r2(t.unrealized), total: r2(t.realized + t.unrealized),
        value: r2(t.value), invested: r2(t.invested), trades: t.entries, closed: t.trips, wins: t.wins,
        winrate: t.trips ? Math.round((t.wins / t.trips) * 100) : null, inPosition: t.value > 0, last: t.last
      };
    });
  }

  function recentTrades(bots, orderRows, n) {
    function botOf(sym) {
      for (var i = 0; i < bots.length; i++) if (bots[i].symbols.map(norm).indexOf(norm(sym)) >= 0) return bots[i];
      return null;
    }
    return fills(orderRows).reverse().slice(0, n).map(function (f) {
      return {
        time: f.filled_at, bot: botOf(f.symbol), symbol: f.symbol, side: f.side,
        kind: f.role === 'take_profit' ? 'Winst nemen' : f.role === 'stop_loss' ? 'Stop-loss' : f.type === 'market' ? 'Markt' : f.type,
        qty: f.filled_qty, price: f.price, value: r2(f.filled_qty * f.price)
      };
    });
  }

  // Eerste uitgevoerde trade van een van de bots: vanaf dan tellen de bots.
  function firstFill(bots, orderRows) {
    var syms = {};
    bots.forEach(function (b) { b.symbols.forEach(function (s) { syms[norm(s)] = true; }); });
    var f = fills(orderRows).filter(function (r) { return syms[norm(r.symbol)]; })[0];
    return f ? f.filled_at : null;
  }

  // Hoe lang geleden, in gewone woorden: '1 dag', '3 weken', '4 maanden', '1 jaar en 2 maanden'.
  function age(fromIso, now) {
    var a = new Date(fromIso), b = now ? new Date(now) : new Date();
    var days = Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate()) - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / 864e5);
    if (days < 1) return 'minder dan een dag';
    if (days < 14) return days === 1 ? '1 dag' : days + ' dagen';
    if (days < 61) return Math.floor(days / 7) + ' weken';
    var months = (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()) - (b.getDate() < a.getDate() ? 1 : 0);
    if (months < 12) return months + ' maanden';
    var y = Math.floor(months / 12), m = months % 12;
    return y + ' jaar' + (m ? ' en ' + m + (m === 1 ? ' maand' : ' maanden') : '');
  }

  // Portfoliogeschiedenis van Alpaca -> [{t, v}] zonder lege dagen (voor het account bestond),
  // met de huidige waarde als laatste punt zodat de grafiek altijd tot nu loopt.
  function cleanHistory(h, nowValue, nowMs) {
    var out = [];
    (h && h.timestamp || []).forEach(function (ts, i) {
      var v = h.equity[i];
      if (v !== null && v > 0) out.push({ t: ts * 1000, v: v });
    });
    if (nowValue > 0) {
      var t = nowMs || Date.now();
      if (out.length && t - out[out.length - 1].t < 60000) out[out.length - 1] = { t: t, v: nowValue };
      else out.push({ t: t, v: nowValue });
    }
    return out;
  }
  function change(series) {
    if (series.length < 2) return 0;
    return r2(series[series.length - 1].v - series[0].v);
  }

  if (typeof module !== 'undefined') {
    module.exports = { flattenOrders: flattenOrders, botStats: botStats, recentTrades: recentTrades, firstFill: firstFill, age: age, cleanHistory: cleanHistory, change: change };
    return;
  }

  // ---------- Alpaca ophalen ----------
  function getKeys() {
    try { return JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { return null; }
  }
  function setKeys(k) { try { localStorage.setItem(STORE, JSON.stringify(k)); } catch (e) { /* privémodus */ } }
  function clearKeys() { try { localStorage.removeItem(STORE); } catch (e) { /* niets */ } }

  function get(path, keys) {
    return fetch(API + path, {
      headers: { 'APCA-API-KEY-ID': keys.id, 'APCA-API-SECRET-KEY': keys.secret }
    }).then(function (res) {
      if (res.status === 401 || res.status === 403) { var e = new Error('auth'); e.auth = true; throw e; }
      if (!res.ok) throw new Error('Alpaca gaf code ' + res.status);
      return res.json();
    });
  }

  function allOrders(keys) {
    var all = [];
    function page(until, n) {
      var q = '/v2/orders?status=all&limit=500&nested=true&direction=desc' + (until ? '&until=' + encodeURIComponent(until) : '');
      return get(q, keys).then(function (list) {
        all = all.concat(list);
        if (list.length >= 500 && n < 10) return page(list[list.length - 1].submitted_at, n + 1);
        return all;
      });
    }
    return page(null, 1);
  }

  // ---------- Periodes ----------
  var PERIODS = {
    '24u': { label: '24 uur', ms: 864e5, timeframe: '15Min' },
    '7d': { label: '7 dagen', ms: 7 * 864e5, timeframe: '1H' },
    '30d': { label: '30 dagen', ms: 30 * 864e5, timeframe: '1H' },
    '1j': { label: '1 jaar', period: '1A', timeframe: '1D' },
    'alles': { label: 'Alles' }
  };
  var PERIOD_KEY = 'cab-period';
  var selected = (function () { try { return localStorage.getItem(PERIOD_KEY) || '7d'; } catch (e) { return '7d'; } })();
  var histories = {};

  function historyQuery(key, firstIso) {
    var p = PERIODS[key], now = Date.now();
    if (key === 'alles') {
      var from = firstIso ? new Date(firstIso).getTime() - 864e5 : now - 365 * 864e5;
      p = now - from <= 29 * 864e5 ? { ms: now - from, timeframe: '1H' } : { start: from, timeframe: '1D' };
    }
    if (p.period) return 'period=' + p.period + '&timeframe=' + p.timeframe;
    var start = new Date(p.start || now - p.ms).toISOString().replace(/\.\d+Z$/, 'Z');
    var q = 'start=' + encodeURIComponent(start) + '&timeframe=' + p.timeframe;
    if (p.timeframe !== '1D') q += '&intraday_reporting=continuous&pnl_reset=no_reset';
    return q;
  }

  function allHistories(keys, firstIso, nowValue) {
    var names = Object.keys(PERIODS);
    return Promise.all(names.map(function (k) {
      return get('/v2/account/portfolio/history?' + historyQuery(k, firstIso), keys)
        .then(function (h) { return cleanHistory(h, nowValue); })
        .catch(function () { return null; });
    })).then(function (list) {
      var out = {};
      names.forEach(function (k, i) { out[k] = list[i]; });
      return out;
    });
  }

  // ---------- Opmaak ----------
  var usd = new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol' });
  var signed = new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol', signDisplay: 'exceptZero' });
  var qtyFmt = new Intl.NumberFormat('nl-NL', { maximumFractionDigits: 4 });
  var timeFmt = new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  var clockFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', hour: '2-digit', minute: '2-digit' });

  // Bestaat een element niet (bijv. een oudere pagina uit de cache), dan schrijven we naar een
  // los, onzichtbaar element in plaats van vast te lopen.
  function $(sel) {
    var n = document.querySelector(sel);
    if (!n) { console.warn('Dashboard: element ontbreekt', sel); n = document.createElement('div'); }
    return n;
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function tone(node, v) {
    node.classList.toggle('is-pos', v > 0);
    node.classList.toggle('is-neg', v < 0);
  }
  function setMoney(sel, v, isSigned) {
    var n = $(sel);
    n.textContent = (isSigned ? signed : usd).format(v);
    if (isSigned) tone(n, v);
  }

  // ---------- Beurstijden ----------
  // De kalender van Alpaca geeft tijden in New Yorkse tijd; omrekenen naar de tijd van de lezer.
  function nyToDate(dateStr, hm) {
    var d = dateStr.split('-').map(Number), t = hm.split(':').map(Number);
    var guess = Date.UTC(d[0], d[1] - 1, d[2], t[0], t[1]);
    var parts = {};
    new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
      .formatToParts(new Date(guess)).forEach(function (x) { parts[x.type] = x.value; });
    var shown = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute);
    return new Date(guess + (guess - shown));
  }
  function nyToday(offsetDays) {
    var d = new Date(Date.now() + (offsetDays || 0) * 864e5);
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' }).format(d);
  }
  var hmFmt = new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' });
  var dayFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
  function span(ms) {
    var m = Math.max(0, Math.round(ms / 60000)), h = Math.floor(m / 60);
    return h ? h + ' u ' + (m % 60) + ' min' : m + ' min';
  }
  function dayLabel(dateStr) {
    var today = nyToday(0), tomorrow = nyToday(1);
    if (dateStr === today) return 'vandaag';
    if (dateStr === tomorrow) return 'morgen';
    return dayFmt.format(new Date(dateStr + 'T00:00:00Z'));
  }

  function renderMarket(calendar, clock) {
    var now = Date.now();
    var sessions = calendar.map(function (c) {
      return { date: c.date, open: nyToDate(c.date, c.open), close: nyToDate(c.date, c.close), short: c.close !== '16:00' };
    });
    var cur = sessions.filter(function (s) { return s.close.getTime() > now; })[0];
    var chip = $('#market');
    chip.dataset.open = clock.is_open ? 'yes' : 'no';
    var state = $('#mkt-state'), line = $('#mkt-line');
    if (!cur) { state.textContent = clock.is_open ? 'Open' : 'Dicht'; line.textContent = ''; chip.textContent = 'Beurs ' + state.textContent.toLowerCase(); return; }
    var range = hmFmt.format(cur.open) + ' tot ' + hmFmt.format(cur.close);
    if (clock.is_open) {
      state.textContent = 'Open';
      line.textContent = 'Vandaag van ' + range + '. Sluit over ' + span(cur.close - now) + '.';
      chip.textContent = 'Beurs open tot ' + hmFmt.format(cur.close);
    } else {
      state.textContent = 'Dicht';
      line.textContent = 'Opent ' + dayLabel(cur.date) + ' om ' + hmFmt.format(cur.open) + ' (over ' + span(cur.open - now) + ') en is dan open tot ' + hmFmt.format(cur.close) + '.';
      chip.textContent = 'Beurs dicht, opent ' + dayLabel(cur.date) + ' ' + hmFmt.format(cur.open);
    }
    state.dataset.open = clock.is_open ? 'yes' : 'no';

    // komende handelsdagen, inclusief feestdagen (doordeweekse dagen die niet in de kalender staan)
    var list = $('#mkt-days');
    list.replaceChildren();
    var byDate = {};
    sessions.forEach(function (s) { byDate[s.date] = s; });
    var start = new Date(cur.date + 'T00:00:00Z'), shown = 0;
    for (var i = 0; shown < 5 && i < 14; i++) {
      var d = new Date(start.getTime() + i * 864e5), key = d.toISOString().slice(0, 10), wd = d.getUTCDay();
      if (wd === 0 || wd === 6) continue;
      var li = el('li');
      li.append(el('span', 'mkt-day', dayLabel(key)));
      var s = byDate[key];
      if (s) {
        li.append(el('span', 'mkt-hours', hmFmt.format(s.open) + ' tot ' + hmFmt.format(s.close)));
        if (s.short) { li.append(el('span', 'mkt-note', 'korte dag')); }
      } else {
        li.className = 'is-closed';
        li.append(el('span', 'mkt-hours', 'gesloten'), el('span', 'mkt-note', 'feestdag'));
      }
      list.append(li);
      shown++;
    }
  }

  // ---------- Schermen ----------
  function show(state) {
    document.body.dataset.state = state; // 'keys' | 'loading' | 'ready' | 'error'
  }

  var axisFmt = {
    '24u': new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' }),
    '7d': new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric' }),
    '30d': new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'short' }),
    '1j': new Intl.DateTimeFormat('nl-NL', { month: 'short', year: '2-digit' }),
    'alles': new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'short' })
  };
  var tipFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  var tipDayFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

  function renderPeriods() {
    Object.keys(PERIODS).forEach(function (k) {
      var node = document.querySelector('[data-change="' + k + '"]');
      var series = histories[k];
      if (!series) { node.textContent = '—'; node.classList.remove('is-pos', 'is-neg'); return; }
      var c = change(series);
      node.textContent = signed.format(c);
      tone(node, c);
    });
    document.querySelectorAll('.period').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.period === selected ? 'true' : 'false');
    });
    drawChart();
  }

  var SVG = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs) {
    var n = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach(function (a) { n.setAttribute(a, attrs[a]); });
    return n;
  }

  function drawChart() {
    var box = $('#chart');
    var series = histories[selected] || [];
    box.querySelectorAll('svg, .tip').forEach(function (n) { n.remove(); });
    var empty = $('#chart-empty');
    if (series.length < 2) { empty.hidden = false; return; }
    empty.hidden = true;

    var W = box.clientWidth, H = box.clientHeight;
    var styles = getComputedStyle(document.documentElement);
    var c = change(series);
    var color = c < 0 ? styles.getPropertyValue('--neg').trim() : c > 0 ? styles.getPropertyValue('--pos').trim() : styles.getPropertyValue('--ink').trim();
    var base = series[0].v;
    var vals = series.map(function (p) { return p.v; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var pad = Math.max((hi - lo) * 0.15, 1);
    lo -= pad; hi += pad;

    // marge links op basis van de breedste y-label
    var yTicks = [];
    for (var i = 0; i <= 3; i++) yTicks.push(lo + (hi - lo) * i / 3);
    var probe = svgEl('svg', { width: 0, height: 0 }); probe.classList.add('axis'); box.append(probe);
    var tw = 0;
    yTicks.forEach(function (v) { var t = svgEl('text'); t.textContent = usd.format(v); probe.append(t); tw = Math.max(tw, t.getComputedTextLength()); });
    probe.remove();
    var m = { l: Math.ceil(tw) + 10, r: 8, t: 10, b: 24 };
    var iw = Math.max(10, W - m.l - m.r), ih = Math.max(10, H - m.t - m.b);
    var t0 = series[0].t, t1 = series[series.length - 1].t;
    function x(t) { return m.l + (t1 === t0 ? 0 : (t - t0) / (t1 - t0) * iw); }
    function y(v) { return m.t + (hi - v) / (hi - lo) * ih; }

    var svg = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img',
      'aria-label': 'Accountwaarde over ' + PERIODS[selected].label + ': van ' + usd.format(series[0].v) + ' naar ' + usd.format(series[series.length - 1].v) });
    var defs = svgEl('defs'), grad = svgEl('linearGradient', { id: 'fill', x1: 0, y1: 0, x2: 0, y2: 1 });
    grad.append(svgEl('stop', { offset: '0%', 'stop-color': color, 'stop-opacity': 0.22 }), svgEl('stop', { offset: '100%', 'stop-color': color, 'stop-opacity': 0 }));
    defs.append(grad); svg.append(defs);

    var grid = svgEl('g', { 'class': 'grid' }), axis = svgEl('g', { 'class': 'axis' });
    yTicks.forEach(function (v) {
      grid.append(svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }));
      var t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }); t.textContent = usd.format(v); axis.append(t);
    });
    // x-labels: begin, midden, eind (zonder overlap)
    var xf = axisFmt[selected];
    [0, 0.5, 1].forEach(function (f, idx) {
      var tt = t0 + (t1 - t0) * f;
      var t = svgEl('text', { x: x(tt), y: H - 6, 'text-anchor': idx === 0 ? 'start' : idx === 2 ? 'end' : 'middle' });
      t.textContent = xf.format(new Date(tt)); axis.append(t);
    });
    svg.append(grid, axis);
    svg.append(svgEl('line', { 'class': 'base', x1: m.l, x2: W - m.r, y1: y(base), y2: y(base) }));

    var d = series.map(function (p, i) { return (i ? 'L' : 'M') + x(p.t).toFixed(1) + ' ' + y(p.v).toFixed(1); }).join(' ');
    svg.append(svgEl('path', { d: d + ' L' + x(t1).toFixed(1) + ' ' + (m.t + ih) + ' L' + x(t0).toFixed(1) + ' ' + (m.t + ih) + ' Z', fill: 'url(#fill)' }));
    var line = svgEl('path', { d: d, fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
    svg.append(line);

    var cross = svgEl('line', { y1: m.t, y2: m.t + ih, stroke: 'currentColor', 'stroke-opacity': 0.25, visibility: 'hidden' });
    var dot = svgEl('circle', { r: 4.5, fill: color, stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden' });
    svg.append(cross, dot);
    box.append(svg);

    var tip = el('div', 'tip'); tip.hidden = true; box.append(tip);
    var daily = selected === '1j' || (selected === 'alles' && t1 - t0 > 29 * 864e5);
    function show(clientX) {
      var r = svg.getBoundingClientRect();
      var px = (clientX - r.left) / r.width * W;
      var tt = t0 + Math.min(1, Math.max(0, (px - m.l) / iw)) * (t1 - t0);
      var best = series[0];
      series.forEach(function (p) { if (Math.abs(p.t - tt) < Math.abs(best.t - tt)) best = p; });
      var cx = x(best.t), cy = y(best.v);
      cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility', 'visible');
      dot.setAttribute('cx', cx); dot.setAttribute('cy', cy); dot.setAttribute('visibility', 'visible');
      tip.replaceChildren();
      var diff = r2(best.v - base);
      var head = el('span', 'muted', (daily ? tipDayFmt : tipFmt).format(new Date(best.t)));
      var val = el('b', null, usd.format(best.v));
      var ch = el('span', null, signed.format(diff) + ' sinds begin periode'); tone(ch, diff);
      tip.append(head, val, ch);
      tip.hidden = false;
      var left = cx / W * r.width, half = tip.offsetWidth / 2;
      tip.style.left = Math.min(r.width - half, Math.max(half, left)) + 'px';
    }
    function hide() { cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); tip.hidden = true; }
    svg.addEventListener('pointermove', function (e) { show(e.clientX); });
    svg.addEventListener('pointerdown', function (e) { show(e.clientX); });
    svg.addEventListener('pointerleave', hide);

    if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches && !drawChart.done) {
      var len = line.getTotalLength();
      line.style.strokeDasharray = len; line.style.strokeDashoffset = len;
      line.getBoundingClientRect();
      line.style.transition = 'stroke-dashoffset 700ms cubic-bezier(0, 0, 0.2, 1)';
      line.style.strokeDashoffset = 0;
      drawChart.done = true;
    }
  }

  var longDate = new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' });
  function renderSince(first) {
    var since = $('#sum-since'), dur = $('#sum-age');
    if (!first) { since.textContent = 'nog niet'; dur.textContent = 'nog geen trades'; return; }
    since.textContent = longDate.format(new Date(first));
    dur.textContent = age(first);
  }

  function renderSummary(stats, account) {
    var total = r2(stats.reduce(function (t, s) { return t + s.total; }, 0));
    var realized = r2(stats.reduce(function (t, s) { return t + s.realized; }, 0));
    var open = r2(stats.reduce(function (t, s) { return t + s.value; }, 0));
    var trades = stats.reduce(function (t, s) { return t + s.trades; }, 0);
    setMoney('#sum-total', total, true);
    setMoney('#sum-open', open, false);
    $('#sum-trades').textContent = String(trades);
    setMoney('#acct-value', Number(account.portfolio_value), false);
    setMoney('#sum-realized', realized, true);
  }

  function renderBots(stats) {
    var wrap = $('#bot-list');
    wrap.replaceChildren();
    if (!stats.length) {
      wrap.append(el('p', 'empty', 'Nog geen bots in de botlijst (docs/bots.js).'));
      return;
    }
    stats.forEach(function (s, i) {
      var b = s.bot;
      var card = el('article', 'bot');
      card.style.setProperty('--bot', b.color || '#888');
      card.style.setProperty('--i', i);

      var top = el('header', 'bot-top');
      top.append(el('h3', 'bot-name', b.name));
      var chip = el('span', 'status', s.inPosition ? 'In positie' : 'Wacht op signaal');
      chip.dataset.on = s.inPosition ? 'yes' : 'no';
      top.append(chip);
      card.append(top);

      card.append(el('p', 'bot-desc', b.strategy));

      var res = el('div', 'bot-result');
      var big = el('span', 'num-xl', signed.format(s.total));
      tone(big, s.total);
      res.append(big, el('span', 'muted small', 'resultaat sinds de start'));
      card.append(res);

      var dl = el('dl', 'stats');
      function stat(label, value, v) {
        var w = el('div');
        var dd = el('dd', null, value);
        if (v !== undefined) tone(dd, v);
        w.append(el('dt', null, label), dd);
        dl.append(w);
      }
      stat('Open positie', usd.format(s.value));
      stat('Gerealiseerd', signed.format(s.realized), s.realized);
      stat('Trades', String(s.trades));
      stat('Winrate', s.winrate === null ? 'nog geen' : s.winrate + '% (' + s.wins + '/' + s.closed + ')');
      card.append(dl);

      var pct = b.budget ? Math.min(100, (s.invested / b.budget) * 100) : 0;
      var bud = el('div', 'budget');
      var bar = el('div', 'bar');
      bar.setAttribute('role', 'img');
      bar.setAttribute('aria-label', Math.round(pct) + '% van het budget zit in de markt');
      var fill = el('span');
      bar.append(fill);
      bud.append(bar, el('span', 'muted small', usd.format(s.invested) + ' van ' + usd.format(b.budget) + ' budget in de markt'));
      card.append(bud);
      requestAnimationFrame(function () { fill.style.width = pct + '%'; });

      var meta = el('p', 'bot-meta muted small');
      meta.textContent = 'Handelt in: ' + b.symbols.join(', ') + '. Draait ' + b.schedule + '.' +
        (s.last ? ' Laatste trade: ' + timeFmt.format(new Date(s.last)) + '.' : '');
      card.append(meta);
      wrap.append(card);
    });
  }

  function renderTrades(trades) {
    var body = $('#trade-rows');
    body.replaceChildren();
    if (!trades.length) {
      var tr = el('tr'); var td = el('td', 'empty', 'Nog geen trades. Zodra een bot koopt of verkoopt, staat het hier.');
      td.colSpan = 8; tr.append(td); body.append(tr);
      return;
    }
    trades.forEach(function (t) {
      var tr = el('tr');
      tr.append(el('td', null, timeFmt.format(new Date(t.time))));
      var botTd = el('td');
      var tag = el('span', 'bot-tag', t.bot ? t.bot.name : 'Handmatig');
      tag.style.setProperty('--bot', t.bot && t.bot.color ? t.bot.color : '#888');
      botTd.append(tag);
      tr.append(botTd);
      tr.append(el('td', null, t.symbol));
      var side = el('td'); var sp = el('span', 'side', t.side === 'buy' ? 'Koop' : 'Verkoop'); sp.dataset.side = t.side; side.append(sp);
      tr.append(side);
      tr.append(el('td', null, t.kind));
      tr.append(el('td', 'num', qtyFmt.format(t.qty)));
      tr.append(el('td', 'num', usd.format(t.price)));
      tr.append(el('td', 'num', usd.format(t.value)));
      body.append(tr);
    });
  }

  var timer = null;
  var busy = false;

  function load(first) {
    var keys = getKeys();
    if (!keys) { show('keys'); return; }
    if (busy) return;
    busy = true;
    if (first) show('loading');
    document.body.classList.add('is-refreshing');
    Promise.all([get('/v2/account', keys), get('/v2/positions', keys), allOrders(keys), get('/v2/clock', keys),
      get('/v2/calendar?start=' + nyToday(0) + '&end=' + nyToday(14), keys)])
      .then(function (r) {
        var bots = window.BOTS || [];
        var rows = flattenOrders(r[2]);
        var stats = botStats(bots, r[1], rows);
        renderMarket(r[4], r[3]);
        renderSummary(stats, r[0]);
        renderSince(firstFill(bots, rows));
        renderBots(stats);
        renderTrades(recentTrades(bots, rows, 30));
        $('#updated').textContent = 'Bijgewerkt om ' + new Date().toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
        show('ready');
        // grafiekdata pas na het tonen ophalen, zodat de pagina niet hoeft te wachten
        return allHistories(keys, firstFill(bots, rows), Number(r[0].equity)).then(function (h) {
          histories = h;
          renderPeriods();
        });
      })
      .catch(function (e) {
        if (e.auth) {
          clearKeys();
          $('#key-error').hidden = false;
          show('keys');
        } else if (document.body.dataset.state === 'ready') {
          $('#updated').textContent = 'Bijwerken mislukt, probeert het zo opnieuw';
        } else {
          $('#error-text').textContent = e.message === 'Failed to fetch'
            ? 'Geen verbinding met Alpaca. Check je internet en probeer het opnieuw.'
            : e.message;
          show('error');
        }
      })
      .then(function () { busy = false; document.body.classList.remove('is-refreshing'); });
  }

  function start() {
    $('#key-form').addEventListener('submit', function (ev) {
      ev.preventDefault();
      var id = $('#key-id').value.trim();
      var secret = $('#key-secret').value.trim();
      if (!id || !secret) return;
      setKeys({ id: id, secret: secret });
      $('#key-form').reset();
      $('#key-error').hidden = true;
      load(true);
    });
    $('#refresh').addEventListener('click', function () { load(false); });
    document.querySelectorAll('.period').forEach(function (b) {
      b.addEventListener('click', function () {
        selected = b.dataset.period;
        try { localStorage.setItem(PERIOD_KEY, selected); } catch (e) { /* niets */ }
        renderPeriods();
      });
    });
    var rt = null;
    window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(drawChart, 150); });
    $('#retry').addEventListener('click', function () { load(true); });
    $('#logout').addEventListener('click', function () { clearKeys(); show('keys'); });
    load(true);
    timer = setInterval(function () { if (!document.hidden) load(false); }, REFRESH_MS);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) load(false); });
  }

  document.addEventListener('DOMContentLoaded', start);
})();
