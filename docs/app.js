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

  if (typeof module !== 'undefined') {
    module.exports = { flattenOrders: flattenOrders, botStats: botStats, recentTrades: recentTrades };
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

  // ---------- Opmaak ----------
  var usd = new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol' });
  var signed = new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol', signDisplay: 'exceptZero' });
  var qtyFmt = new Intl.NumberFormat('nl-NL', { maximumFractionDigits: 4 });
  var timeFmt = new Intl.DateTimeFormat('nl-NL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  var clockFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', hour: '2-digit', minute: '2-digit' });

  function $(sel) { return document.querySelector(sel); }
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

  function renderSummary(stats, account) {
    var total = r2(stats.reduce(function (t, s) { return t + s.total; }, 0));
    var realized = r2(stats.reduce(function (t, s) { return t + s.realized; }, 0));
    var open = r2(stats.reduce(function (t, s) { return t + s.value; }, 0));
    var trades = stats.reduce(function (t, s) { return t + s.trades; }, 0);
    setMoney('#sum-total', total, true);
    setMoney('#sum-open', open, false);
    $('#sum-trades').textContent = String(trades);
    setMoney('#acct-value', Number(account.portfolio_value), false);
    setMoney('#acct-today', r2(Number(account.equity) - Number(account.last_equity)), true);
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
        renderBots(stats);
        renderTrades(recentTrades(bots, rows, 30));
        $('#updated').textContent = 'Bijgewerkt om ' + new Date().toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' });
        show('ready');
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
    $('#retry').addEventListener('click', function () { load(true); });
    $('#logout').addEventListener('click', function () { clearKeys(); show('keys'); });
    load(true);
    timer = setInterval(function () { if (!document.hidden) load(false); }, REFRESH_MS);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) load(false); });
  }

  document.addEventListener('DOMContentLoaded', start);
})();
