# -*- coding: utf-8 -*-
"""Uganda's official registers, checked against Wikimedia.

The government's own lists of what exists: the census administrative
hierarchy and the Electoral Commission's constituencies and elected members.
Neither has an API, so both were parsed out of the files they publish.
"""

from render import (bars, callout, data_table, esc, eyebrow, filter_controls,
                    fmt, join, note, page_footer, plain_table, section_heading,
                    stat_tiles, tab_bar, td)


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>The government keeps a list of what exists. Wikipedia does not '
        'have most of it</h1>',
        f'<p class="lede">The census counts {fmt(d["total"])} named things '
        f'into being: districts, counties, sub-counties, parishes, the '
        f'constituencies people vote in and the members they elected. '
        f'<strong>{fmt(d["missing"])} of them have no Wikipedia article in '
        f'any language.</strong> These are not obscure places. They are the '
        f'administrative units the state itself organises Uganda into.</p>',
        '<p class="stamp"><strong>Straight from the source, with no API to '
        'help.</strong> The Uganda Bureau of Statistics publishes the 2024 '
        'census as spreadsheets and the Electoral Commission publishes '
        'results as PDFs. Both were parsed directly: an XLSX is a zip of XML, '
        'and the election schedule keeps a marker between its table cells '
        'that makes the columns recoverable. Nothing here is retyped by '
        'hand.</p>',
        '</header>',
    ])


def _coverage(d):
    rows = [[
        {'text': k['label']},
        {'text': k['sourceLabel'], 'dim': True},
        {'text': fmt(k['total'])},
        {'text': fmt(k['described'])},
        {'text': fmt(k['missing']), 'strong': True},
        {'text': f'{k["covered"]:.0f}%', 'dim': True},
    ] for k in d['kinds']]
    return join([
        section_heading(
            'What the registers hold, and what Wikipedia has',
            'Every entry matched against this project&rsquo;s corpus by name. '
            'Each corpus item has at least one article by construction, so a '
            'match means the thing is described somewhere and a miss means no '
            'Wikipedia in any language covers it.'),
        plain_table(
            [{'label': 'Register'}, {'label': 'Source'},
             {'label': 'Entries', 'num': True},
             {'label': 'Described', 'num': True},
             {'label': 'No article', 'num': True},
             {'label': 'Covered', 'num': True}],
            rows),
        '<div class="spacer"></div>',
        bars([{'label': k['label'], 'value': k['missing'],
               'display': fmt(k['missing'])} for k in d['kinds']
              if k['missing']]),
        note('Bars are entries with no article. Parishes and sub-counties '
             'dominate by weight of numbers, but the constituencies and the '
             'members elected in them are the ones a reader is most likely to '
             'look up and not find.'),
    ])


def _worklist(d):
    if not d['rows']:
        return ''
    counts = {}
    for r in d['rows']:
        counts[r['kindLabel']] = counts.get(r['kindLabel'], 0) + 1
    kinds = [k['label'] for k in d['kinds'] if counts.get(k['label'])]

    columns = [
        {'label': '#', 'num': True}, {'label': 'Name'},
        {'label': 'Register'}, {'label': 'District'},
        {'label': 'Within'}, {'label': 'Party', 'num': False},
    ]

    def row(r, i):
        return join([
            td(str(i + 1), 'num', 'dim'),
            td(f'<strong>{esc(r["name"])}</strong>'),
            td(esc(r['kindLabel']), 'dim'),
            td(esc(r['district']), 'dim'),
            td(esc(r['parent']), 'dim'),
            td(esc(r['party']) if r['party'] else '', 'dim'),
        ])

    tail = ''
    if d['omitted']:
        tail = note(
            f'{fmt(d["omitted"])} more are omitted here: sub-counties and '
            f'parishes are sampled at {fmt(d["sampleSize"])} each, because a '
            f'table of ten thousand parishes would be unreadable. Every row '
            f'is in <code>data/ug_register_undocumented.csv</code>.')

    return join([
        section_heading(
            'The undocumented list',
            'Districts, counties, constituencies and members of parliament in '
            'full, sub-counties and parishes sampled. A name here is one the '
            'state uses and no encyclopedia explains.'),
        filter_controls(
            groups=[{'key': 'kind', 'label': 'Filter by register',
                     'allLabel': 'Every register',
                     'options': [{'value': k, 'label': k, 'count': counts[k]}
                                 for k in kinds]}],
            total=len(d['rows']), count_noun='entries',
            search_placeholder=f'Filter {fmt(len(d["rows"]))} entries by name, '
                               f'district or register',
            search_label='Filter the register list'),
        data_table(d['rows'], columns, row,
                   row_attrs=lambda r: {'data-kind': r['kindLabel']}),
        tail,
    ])


def render(d):
    mps = next((k for k in d['kinds'] if k['key'] == 'mp'), None)
    cons = next((k for k in d['kinds'] if k['key'] == 'constituency'), None)
    districts = next((k for k in d['kinds'] if k['key'] == 'district'), None)

    tiles = [
        {'k': 'Register entries', 'v': d['total'],
         'd': 'from the census hierarchy and the election results'},
        {'k': 'No article anywhere', 'v': d['missing'], 'alarm': True,
         'd': f'{100.0 * d["missing"] / d["total"]:.0f}% of everything the '
              f'state lists'},
    ]
    if mps:
        tiles.append({
            'k': 'MPs with no article', 'raw': True,
            'v': f'{fmt(mps["missing"])} / {fmt(mps["total"])}',
            'd': 'elected to the national parliament in 2026'})
    if districts:
        tiles.append({
            'k': 'Districts covered', 'raw': True,
            'v': f'{districts["covered"]:.0f}%',
            'd': f'{fmt(districts["described"])} of {fmt(districts["total"])} '
                 f'have an article'})

    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),
        section_heading('The headline'),
        stat_tiles(tiles),
    ]

    if mps and cons:
        parts.append(callout(
            f'<strong>{fmt(mps["missing"])} of the {fmt(mps["total"])} members '
            f'elected to Uganda&rsquo;s parliament in 2026 have no Wikipedia '
            f'article in any language, and {fmt(cons["missing"])} of the '
            f'{fmt(cons["total"])} constituencies that elected them have '
            f'none either.</strong> Every one of them is a public figure '
            f'holding national office, named in an official schedule of '
            f'results published by the Electoral Commission, which is a '
            f'source in itself. This is the most clearly notable list this '
            f'project has produced.'))

    parts += [
        _coverage(d),
        _worklist(d),
        page_footer([
            '<strong>Where this comes from.</strong> The administrative '
            'hierarchy is the Uganda Bureau of Statistics 2024 census '
            'sub-county profiles, an XLSX in which each row&rsquo;s level is '
            'encoded in the cell style rather than the text. The '
            'constituencies and members are the Electoral Commission&rsquo;s '
            'schedule of results for directly elected members of parliament, '
            '2025/2026, a PDF whose table cells are separated by a font '
            'marker. Winners are the highest-polling candidate in each '
            'constituency.',

            '<strong>One source that could not be used.</strong> The '
            'Commission&rsquo;s 2021 results are published the same way but '
            'render their text one glyph at a time with no field marker, so a '
            'name comes out as &ldquo;O CH ER O J I M BR ICK Y&rdquo; with no '
            'way to tell a kerning gap from a real space. Publishing mangled '
            'names of real people would be worse than publishing none, so '
            'only the 2026 file is used. A PDF library would lift that '
            'restriction and add the earlier parliaments.',

            '<strong>What the matching is.</strong> A name-token comparison '
            'against corpus labels, ignoring words like district, county and '
            'parish that carry no identifying weight. It is deliberately '
            'strict, so an article filed under a different spelling reads as '
            'missing: treat &ldquo;no article&rdquo; as a search result worth '
            'checking, not as proof. Nor does a missing article mean a '
            'missing Wikidata item; Uganda has 58,240 items with no article '
            'in any language, and many of these parishes will be among them.',

            '<strong>Rebuild.</strong> <code>python '
            'src_data/official_registers.py</code>, then <code>python '
            'src_viz/export_data.py</code> and <code>python '
            'src_viz/build_pages.py registers</code>. Full exports are in '
            '<code>data/ug_register_units.csv</code>, '
            '<code>data/ug_register_undocumented.csv</code> and '
            '<code>data/ug_register_mps.csv</code>.',
        ]),
        '</div>',
    ]
    return join(parts)
