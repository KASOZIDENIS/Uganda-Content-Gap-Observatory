# -*- coding: utf-8 -*-
"""Presentation helpers shared by the page builders.

Kept free of pandas and requests so a page can be rebuilt from the database
alone, with no pipeline dependencies loaded.

These render HTML strings from the view models in data/ui/*.json. Python owns
the numbers and now the markup too: the view models still arrive with every
value ready to print, so nothing here computes anything a page would report.

The two interactive pieces -- the filter controls and the chart cards -- are
pre-rendered complete and then wired up by assets/js/app.js, which reads what
it needs from the DOM. No component state is serialised into the page.
"""

import html


# --------------------------------------------------------------------------
# primitives


def esc(text):
    return html.escape(str(text) if text is not None else '')


def fmt(number):
    """Thousands separators, matching the view models' own formatting."""
    try:
        return f'{int(round(float(number))):,}'
    except (TypeError, ValueError):
        return '-'


def attr(name, value):
    """One attribute, or nothing when the value is absent."""
    if value is None or value is False or value == '':
        return ''
    if value is True:
        return f' {name}'
    return f' {name}="{esc(value)}"'


def cls(*names):
    """Join class names, dropping the empty ones."""
    kept = [n for n in names if n]
    return ' '.join(kept)


def join(parts):
    return '\n'.join(p for p in parts if p)


# --------------------------------------------------------------------------
# page chrome


def tab_bar(nav):
    """The tab bar every page carries, fed by the page list in the view model."""
    tabs = []
    for page in nav['pages']:
        if page['key'] == nav['current']:
            tabs.append(f'<span class="tab active" aria-current="page">'
                        f'{esc(page["label"])}</span>')
        else:
            tabs.append(f'<a class="tab" href="{esc(page["href"])}">'
                        f'{esc(page["label"])}</a>')
    return ('<nav class="tabs" aria-label="Uganda content gap pages">\n'
            + join(tabs) + '\n</nav>')


def eyebrow(inner):
    return f'<p class="eyebrow">{inner}</p>'


def section_heading(title, sub=None):
    """An h2 and its optional standfirst. Both take HTML, not plain text."""
    out = f'<h2>{title}</h2>'
    if sub:
        out += f'\n<p class="h2sub">{sub}</p>'
    return out


def note(inner):
    return f'<p class="note">{inner}</p>'


def callout(inner):
    return f'<div class="callout">{inner}</div>'


def page_footer(paragraphs):
    return '<footer>\n' + join(f'<p>{p}</p>' for p in paragraphs) + '\n</footer>'


def stat_tiles(tiles):
    """The stat tile row.

    A tile's `v` is run through fmt() unless it sets raw, which is how the
    pages that print a ratio or a code keep their own formatting.
    """
    out = ['<div class="tiles">']
    for tile in tiles:
        value = tile['v'] if tile.get('raw') else fmt(tile['v'])
        out.append(f'<div class="{cls("tile", "alarm" if tile.get("alarm") else "")}">'
                   f'<p class="k">{tile["k"]}</p>'
                   f'<div class="v">{value}</div>'
                   f'<p class="d">{tile["d"]}</p></div>')
    out.append('</div>')
    return join(out)


# --------------------------------------------------------------------------
# small shared pieces


def chip(kind, label):
    return f'<span class="{cls("chip", kind)}">{esc(label)}</span>'


def bars(rows):
    """Horizontal bars, widths relative to the largest value.

    The label column width is set per page in CSS, not here.
    """
    top = max((r['value'] for r in rows), default=1) or 1
    out = ['<div class="bars">']
    for row in rows:
        width = 100.0 * row['value'] / top
        display = row.get('display') or fmt(row['value'])
        out.append(f'<div class="bar-row">'
                   f'<div class="bar-label">{esc(row["label"])}</div>'
                   f'<div class="bar-track">'
                   f'<div class="bar-fill" style="width:{width:.1f}%"></div>'
                   f'</div>'
                   f'<div class="bar-val">{esc(display)}</div></div>')
    out.append('</div>')
    return join(out)


def plain_table(columns, rows):
    """The quieter summary tables, as opposed to the big filterable list.

    A cell is a dict: text, plus strong and dim flags. A cell may instead carry
    html, already escaped by the caller, for the one case text cannot cover:
    a link.
    """
    head = join(f'<th{attr("class", "num" if c.get("num") else None)}>'
                f'{esc(c["label"])}</th>' for c in columns)
    body = []
    for cells in rows:
        tds = []
        for i, cell in enumerate(cells):
            num = 'num' if i < len(columns) and columns[i].get('num') else ''
            dim = 'dim' if cell.get('dim') else ''
            text = cell['html'] if 'html' in cell else esc(cell['text'])
            if cell.get('strong'):
                text = f'<strong>{text}</strong>'
            tds.append(f'<td{attr("class", cls(num, dim) or None)}>{text}</td>')
        body.append('<tr>' + ''.join(tds) + '</tr>')
    return ('<table class="plain">\n<thead><tr>' + head + '</tr></thead>\n'
            '<tbody>\n' + join(body) + '\n</tbody>\n</table>')


def wiki_link(lang, title, label=None):
    url = f'https://{lang}.wikipedia.org/wiki/{str(title).replace(" ", "_")}'
    return (f'<a href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(label if label is not None else title)}</a>')


def wikidata_link(qid, class_name=None):
    return (f'<a{attr("class", class_name)} '
            f'href="https://www.wikidata.org/wiki/{esc(qid)}" '
            f'target="_blank" rel="noopener">{esc(qid)}</a>')


def mini_bar(percent):
    """An inline coverage meter, used in the by-tier table on the offices page."""
    return (f'<div class="minibar">'
            f'<div class="minibar-fill" style="width:{percent:.1f}%"></div></div>')


# --------------------------------------------------------------------------
# the big filterable list


def filter_controls(groups=None, total=0, count_noun='rows',
                    search_placeholder=None, search_label='Filter rows',
                    target_id='rows'):
    """The search box and filter chips that drive a data_table().

    Why these are separate from the table: the largest page is 6,765 rows, and
    the controls have to do nothing per row until someone types. They drive
    the table by setting `hidden` on its rows, reading each row's categories
    off its data- attributes and its text off textContent, both already in the
    document. Nothing per-row is sent to the browser a second time.

    Rendered here in its resting state -- every chip inactive but "all", the
    count reading "showing all" -- so the controls look right with JavaScript
    off, even though they cannot then do anything.
    """
    groups = groups or []
    out = [f'<div class="controls" data-filter data-target="{esc(target_id)}" '
           f'data-total="{total}" data-noun="{esc(count_noun)}">']
    out.append(f'<input type="search" class="find" value=""'
               f'{attr("placeholder", search_placeholder)} '
               f'aria-label="{esc(search_label)}">')
    for group in groups:
        out.append(f'<div class="chipfilters" role="group" '
                   f'aria-label="{esc(group["label"])}" '
                   f'data-key="{esc(group["key"])}">')
        out.append(f'<button type="button" class="chipfilter active" '
                   f'data-value="all">{esc(group["allLabel"])} '
                   f'<span class="n">{fmt(total)}</span></button>')
        for option in group['options']:
            out.append(f'<button type="button" class="chipfilter" '
                       f'data-value="{esc(option["value"])}">'
                       f'{esc(option["label"])} '
                       f'<span class="n">{fmt(option["count"])}</span></button>')
        out.append('</div>')
    out.append(f'<p class="count" aria-live="polite">showing all {fmt(total)} '
               f'{esc(count_noun)}</p>')
    out.append('</div>')
    return join(out)


def data_table(rows, columns, render_row, row_attrs=None,
               table_class='itemlist', body_id='rows'):
    """The pre-rendered table the controls act on.

    render_row returns the row's cells; row_attrs returns the data- attributes
    the filter chips match against.
    """
    head = ''.join(f'<th{attr("class", "num" if c.get("num") else None)}>'
                   f'{esc(c["label"])}</th>' for c in columns)
    body = []
    for i, row in enumerate(rows):
        extra = ''
        if row_attrs:
            extra = ''.join(attr(k, v) for k, v in row_attrs(row).items())
        body.append(f'<tr{extra}>{render_row(row, i)}</tr>')
    return (f'<div class="scroller">\n<table class="{esc(table_class)}">\n'
            f'<thead><tr>{head}</tr></thead>\n'
            f'<tbody id="{esc(body_id)}">\n' + join(body)
            + '\n</tbody>\n</table>\n</div>')


def td(inner, *classes):
    return f'<td{attr("class", cls(*classes) or None)}>{inner}</td>'
