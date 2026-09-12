# -*- coding: utf-8 -*-
"""The horizontal bar chart and the card it sits in.

A port of the renderer the dashboard used to carry, with one change that
matters: fills are CSS custom properties rather than hex values read from a
palette at run time. The old version had to re-draw every chart on a
prefers-color-scheme change; this one is rendered once and the browser
re-resolves var(--s1) itself.

Tooltip text rides on each shape as a data-tip attribute and is picked up by
one delegated listener per chart in assets/js/app.js. Nothing per-row is sent
to the browser as a result: the series exists once, in the markup.
"""

from render import esc, fmt, attr, join

DEFAULT_COLORS = ['var(--s1)', 'var(--s2)', 'var(--s3)']


def _num(value):
    """Trim the trailing .0 that float formatting would leave in path data."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f'{value:.2f}'.rstrip('0').rstrip('.')
    return str(value)


def _bar_path(x, y, w, h, r=4):
    """4px rounded data-end; the baseline end stays square."""
    radius = max(0, min(r, w, h / 2))
    if w <= 0.6:
        return f'M{_num(x)} {_num(y)} L{_num(x)} {_num(y + h)} Z'
    return (f'M{_num(x)} {_num(y)} H{_num(x + w - radius)}'
            f' A{_num(radius)} {_num(radius)} 0 0 1 {_num(x + w)} {_num(y + radius)}'
            f' V{_num(y + h - radius)}'
            f' A{_num(radius)} {_num(radius)} 0 0 1 {_num(x + w - radius)} '
            f'{_num(y + h)} H{_num(x)} Z')


def _series_fill(row, index, series_index, series_count, colors, ordinal):
    if series_count > 1:
        return colors[series_index]
    if ordinal:
        return f'var(--ord{min(index + 1, 5)})'
    if row.get('hi') is False:
        return 'var(--neutral)'
    return 'var(--s1)' if row.get('hi') else colors[0]


def hbar(rows, labelW=96, valueW=78, rowH=30, pad=8, width=780, names=None,
         colors=None, ordinal=False, suffix='', decimals=None,
         aria='bar chart'):
    """Horizontal bars, one to three series grouped per row."""
    if not rows:
        return ''
    names = names or []
    colors = colors or DEFAULT_COLORS

    def value(v):
        return fmt(v) if decimals is None else f'{float(v):.{decimals}f}'

    def name_at(k):
        return esc(names[k]) if k < len(names) else ''

    series_count = len(rows[0]['v']) if isinstance(rows[0]['v'], list) else 1
    plot_w = width - labelW - valueW
    height = pad * 2 + len(rows) * rowH
    max_v = max((max(r['v']) if isinstance(r['v'], list) else r['v'])
                for r in rows) or 1

    def sx(v):
        return max(0.0, (v / max_v) * plot_w)

    nodes = []
    for i, row in enumerate(rows):
        top = pad + i * rowH
        nodes.append(
            f'<text x="{_num(labelW - 10)}" y="{_num(top + rowH / 2)}" '
            f'text-anchor="end" dominant-baseline="central" '
            f'fill="var(--text2)" font-size="12.5">{esc(row["label"])}</text>')

        values = row['v'] if isinstance(row['v'], list) else [row['v']]
        gap = 2
        if series_count == 1:
            bh = 14
        else:
            bh = max(6, (rowH - 10 - gap * (series_count - 1)) // series_count)
        block = bh * series_count + gap * (series_count - 1)

        for k, v in enumerate(values):
            y = top + (rowH - block) / 2 + k * (bh + gap)
            if series_count > 1:
                tip = (f'<b>{fmt(v)}</b> &middot; {name_at(k)}'
                       f'<br>{esc(row["label"])}')
            else:
                tip = f'<b>{value(v)}{suffix}</b><br>{esc(row["label"])}'
            nodes.append(
                f'<path d="{_bar_path(labelW, y, sx(v), bh)}" '
                f'fill="{_series_fill(row, i, k, series_count, colors, ordinal)}" '
                f'data-tip="{esc(tip)}"></path>')

        # Full-width hit band so hairline bars stay hoverable.
        if series_count > 1:
            summary = '<br>'.join(f'{name_at(k)} <b>{fmt(v)}</b>'
                                  for k, v in enumerate(values))
        else:
            summary = f'<b>{value(values[0])}{suffix}</b>'
        nodes.append(
            f'<rect x="{_num(labelW)}" y="{_num(top)}" width="{_num(plot_w)}" '
            f'height="{_num(rowH)}" fill="transparent" '
            f'data-tip="{esc(esc(row["label"]) + "<br>" + summary)}"></rect>')

        # Direct value labels: text ink, never the series colour.
        if series_count > 1:
            text = ' / '.join(fmt(v) for v in values)
        else:
            text = value(values[0]) + suffix
        nodes.append(
            f'<text x="{_num(labelW + max(sx(v) for v in values) + 9)}" '
            f'y="{_num(top + rowH / 2)}" dominant-baseline="central" '
            f'fill="var(--text2)" font-size="12" '
            f'style="font-variant-numeric:tabular-nums">{esc(text)}</text>')

    legend = ''
    if series_count > 1 and names:
        swatches = ''.join(
            f'<span><i class="swatch" style="background:{colors[k]}"></i>'
            f'{esc(name)}</span>' for k, name in enumerate(names))
        legend = f'<div class="legend">{swatches}</div>'

    baseline = (f'<line x1="{_num(labelW)}" y1="{_num(pad - 3)}" '
                f'x2="{_num(labelW)}" y2="{_num(pad + len(rows) * rowH - 3)}" '
                f'stroke="var(--baseline)" stroke-width="1"></line>')
    return (f'{legend}<svg viewBox="0 0 {_num(width)} {_num(height)}" '
            f'role="img" aria-label="{esc(aria)}">'
            f'{baseline}{"".join(nodes)}</svg>')


def chart_from(spec):
    """Render a chart straight from its entry in the view model's charts block."""
    return hbar(**spec)


def _table_view(table):
    """The same numbers as the chart, behind the Chart/Table toggle.

    Rendered rather than built on demand, which is what keeps the numbers
    readable with JavaScript off.
    """
    right = set(table.get('alignRight') or [])
    head = ''.join(f'<th{attr("class", "num" if i in right else None)}>'
                   f'{esc(h)}</th>' for i, h in enumerate(table['headers']))
    body = [
        '<tr>' + ''.join(
            f'<td{attr("class", "num" if j in right else None)}>{esc(cell)}</td>'
            for j, cell in enumerate(cells)) + '</tr>'
        for cells in table['rows']
    ]
    return ('<div class="tableview" hidden><table>\n<thead><tr>' + head
            + '</tr></thead>\n<tbody>\n' + join(body)
            + '\n</tbody>\n</table></div>')


def chart_card(title, chart, subtitle=None, note=None, table=None):
    """One chart card: the chart, the same numbers behind a toggle, the tip.

    subtitle and note are HTML strings rather than plain text: several of them
    carry <em>, <code> and entities that belong in the markup.
    """
    head = [f'<div class="card-head"><div><h3>{esc(title)}</h3>']
    if subtitle:
        head.append(f'<p class="sub">{subtitle}</p>')
    head.append('</div>')
    if table:
        head.append('<button type="button" class="toggle" '
                    'aria-pressed="false">Table</button>')
    head.append('</div>')

    parts = [''.join(head), f'<div class="chart">{chart}</div>']
    if table:
        parts.append(_table_view(table))
    if note:
        parts.append(f'<p class="note">{note}</p>')
    parts.append('<div class="tip" style="opacity:0"></div>')
    return '<section class="card">' + join(parts) + '</section>'


def card(title, body, subtitle=None):
    """A card with no chart in it: the two worklist tables use this."""
    head = [f'<div class="card-head"><div><h3>{esc(title)}</h3>']
    if subtitle:
        head.append(f'<p class="sub">{subtitle}</p>')
    head.append('</div></div>')
    return '<section class="card">' + ''.join(head) + body + '</section>'
