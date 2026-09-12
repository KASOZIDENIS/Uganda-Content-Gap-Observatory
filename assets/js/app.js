// Behaviour for the pre-rendered pages.
//
// Everything on these pages is real markup before this file runs: the tables,
// the charts and the controls are all rendered by src_viz/build_pages.py, and
// this only wires up the parts that respond to a pointer. Nothing here
// re-renders anything, and no page data is shipped a second time -- what the
// filters match on is already in the document, as data- attributes and as the
// rows' own text.
//
// Loaded with defer, so the DOM is parsed by the time it runs.

(function () {
  'use strict';

  function fmt(n) {
    return Number(n).toLocaleString('en-US');
  }

  // ------------------------------------------------------------------
  // The search box and filter chips.
  //
  // The largest page is 6,765 rows, so the text index is built once and the
  // DOM is never read for text again on subsequent keystrokes. Rows are
  // hidden in place rather than removed, which keeps the table's layout and
  // the browser's own find-in-page working.

  function initFilters(root) {
    var body = document.getElementById(root.dataset.target || 'rows');
    if (!body) return;

    var total = Number(root.dataset.total || 0);
    var noun = root.dataset.noun || 'rows';
    var input = root.querySelector('.find');
    var count = root.querySelector('.count');
    var groups = [].slice.call(root.querySelectorAll('.chipfilters'));

    var rows = [].slice.call(body.querySelectorAll('tr'));
    var index = rows.map(function (row) {
      return row.textContent.toLowerCase();
    });

    var chosen = {};
    groups.forEach(function (group) {
      chosen[group.dataset.key] = 'all';
    });
    var keys = Object.keys(chosen);

    function apply() {
      var needle = (input ? input.value : '').trim().toLowerCase();
      var visible = 0;

      for (var i = 0; i < rows.length; i++) {
        var ok = true;
        for (var k = 0; k < keys.length; k++) {
          var want = chosen[keys[k]];
          if (want !== 'all' && rows[i].dataset[keys[k]] !== want) {
            ok = false;
            break;
          }
        }
        if (ok && needle && index[i].indexOf(needle) === -1) ok = false;
        rows[i].hidden = !ok;
        if (ok) visible++;
      }

      if (count) {
        count.textContent = visible === total
          ? 'showing all ' + fmt(visible) + ' ' + noun
          : 'showing ' + fmt(visible) + ' of ' + fmt(total);
      }
    }

    if (input) {
      input.addEventListener('input', apply);
      // A search input's clear button fires search, not input, in Safari.
      input.addEventListener('search', apply);
    }

    groups.forEach(function (group) {
      group.addEventListener('click', function (event) {
        var button = event.target.closest('.chipfilter');
        if (!button || !group.contains(button)) return;
        chosen[group.dataset.key] = button.dataset.value;
        group.querySelectorAll('.chipfilter').forEach(function (other) {
          other.classList.toggle('active', other === button);
        });
        apply();
      });
    });
  }

  // ------------------------------------------------------------------
  // Chart cards: the Chart/Table toggle, and the hover tooltip.
  //
  // Both views are in the document already -- the table is rendered rather
  // than built on demand, which is what keeps the numbers readable with
  // JavaScript off -- so the toggle only moves the hidden attribute.

  function initToggle(card) {
    var button = card.querySelector('.toggle');
    var chart = card.querySelector('.chart');
    var table = card.querySelector('.tableview');
    if (!button || !chart || !table) return;

    button.addEventListener('click', function () {
      var showTable = table.hidden;
      table.hidden = !showTable;
      chart.hidden = showTable;
      button.textContent = showTable ? 'Chart' : 'Table';
      button.setAttribute('aria-pressed', showTable ? 'true' : 'false');
    });
  }

  // One delegated listener per chart rather than a handler per bar: the
  // tooltip text rides on each shape as data-tip, put there at build time.
  function initTooltip(scope) {
    var chart = scope.querySelector('.chart');
    var tip = scope.querySelector('.tip');
    if (!chart || !tip) return;

    var PAD = 14;

    chart.addEventListener('mousemove', function (event) {
      var shape = event.target.closest('[data-tip]');
      if (!shape) {
        tip.style.opacity = 0;
        return;
      }
      tip.innerHTML = shape.getAttribute('data-tip');
      tip.style.opacity = 1;

      var box = tip.getBoundingClientRect();
      var x = event.clientX + PAD;
      var y = event.clientY + PAD;
      if (x + box.width > window.innerWidth - 8) {
        x = event.clientX - box.width - PAD;
      }
      if (y + box.height > window.innerHeight - 8) {
        y = event.clientY - box.height - PAD;
      }
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
    });

    chart.addEventListener('mouseleave', function () {
      tip.style.opacity = 0;
    });
  }

  document.querySelectorAll('[data-filter]').forEach(initFilters);
  document.querySelectorAll('.card').forEach(function (card) {
    initToggle(card);
    initTooltip(card);
  });
}());
