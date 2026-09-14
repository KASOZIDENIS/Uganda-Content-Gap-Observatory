# -*- coding: utf-8 -*-
"""Folklore of Uganda, measured on two axes.

Communities down one side under their language family, UNESCO's heritage
domains across the other. The grid is the point: an empty cell is a question
nobody has answered on Wikipedia, and reading the page by row or by column
shows whether the gap belongs to a community or to a whole kind of knowledge.
"""

from render import (bars, callout, esc, eyebrow, fmt, join, note, page_footer,
                    plain_table, section_heading, stat_tiles, tab_bar)


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>Uganda&rsquo;s stone heritage is written down. Its living '
        'heritage is not</h1>',
        f'<p class="lede">Uganda has three tangible World Heritage sites and '
        f'six elements inscribed on UNESCO&rsquo;s intangible heritage lists. '
        f'The three sites carry {fmt(d["tangibleLanguages"])} Wikipedia '
        f'articles between them. The six living traditions carry '
        f'<strong>{fmt(d["ichLanguages"])}</strong>, and '
        f'<strong>{len(d["ichUndocumented"])} of the six have no article in '
        f'any language at all.</strong></p>',
        f'<p class="stamp"><strong>Two axes, so nothing falls through.</strong> '
        f'{d["nGroups"]} ethno-linguistic communities under their four '
        f'language families, against {d["nAspects"]} heritage aspects built on '
        f'UNESCO&rsquo;s domains of intangible cultural heritage. That makes '
        f'{fmt(d["cells"])} cells. '
        f'<strong>{fmt(d["filled"])} of them have a single article or more</strong>, '
        f'which is {d["fillShare"]:.0f}%.</p>',
        '</header>',
    ])


def _anchors(d):
    def row(a):
        cover = ('<strong>none, in any language</strong>' if not a['languages']
                 else f'{fmt(a["languages"])} Wikipedia'
                      + ('s' if a['languages'] != 1 else ''))
        return [
            {'text': a['name']},
            {'text': str(a['year']), 'dim': True},
            {'text': a['listing'], 'dim': True},
            {'html': cover},
            {'text': 'yes' if a['en'] else 'no'},
            {'text': 'yes' if a['lg'] else 'no'},
        ]
    cols = [{'label': 'Inscribed element'}, {'label': 'Year'},
            {'label': 'List'}, {'label': 'Documented in'},
            {'label': 'English'}, {'label': 'Luganda'}]
    return join([
        section_heading(
            'The inscribed elements, and what Wikimedia has of them',
            'Coverage read from Wikidata sitelinks rather than from a search, '
            'so it is exact. Where Wikidata holds two items for one element, '
            'one for the UNESCO inscription and one for the practice, both '
            'are counted.'),
        plain_table(cols, [row(a) for a in d['ich']]),
        note('Barkcloth making is the oldest inscription, from 2008, and the '
             'only Ugandan element on the Representative List rather than the '
             'Urgent Safeguarding List. Its single article is in French. The '
             'English article titled Barkcloth is about the material as a '
             'global craft and is a different Wikidata item; it does not '
             'describe the Ugandan practice.'),
        '<div class="spacer"></div>',
        plain_table(cols, [row(a) for a in d['tangible']]),
        note('The tangible sites for comparison. The contrast is not that the '
             'sites are over-documented. It is that a building can be '
             'photographed and surveyed by people who never met anyone who '
             'uses it, while an oral tradition can only be recorded by '
             'somebody who was told it.'),
    ])


def _matrix(d):
    head = ''.join(
        f'<th class="rot"><span>{esc(a["label"])}</span></th>'
        for a in d['aspects'])
    body, family = [], None
    for r in d['rows']:
        if r['family'] != family:
            family = r['family']
            body.append(f'<tr class="famrow"><th colspan="{len(d["aspects"]) + 2}">'
                        f'{esc(r["familyLabel"])}</th></tr>')
        cells = ''.join(
            f'<td class="cell{" has" if c["n"] else " none"}"'
            f'{f" title=" + chr(34) + esc("; ".join(c["titles"][:6])) + chr(34) if c["n"] else ""}'
            f'>{c["n"] or ""}</td>'
            for c in r['cells'])
        body.append(f'<tr><th class="rowlab">{esc(r["label"])}</th>{cells}'
                    f'<td class="num total">{r["total"] or ""}</td></tr>')
    return join([
        section_heading(
            'The grid',
            'English Wikipedia articles whose title carries the '
            'community&rsquo;s name, sorted into an aspect by vocabulary. '
            'Hover a filled cell to see the articles behind it. An empty cell '
            'is not proof that nothing exists; it is proof that nothing exists '
            'under a title anyone would search for.'),
        '<div class="matrix-scroll">',
        '<table class="matrix"><thead><tr><th class="rowlab"></th>',
        head, '<th class="num">All</th></tr></thead><tbody>',
        join(body), '</tbody></table></div>',
    ])


def _gaps(d):
    parts = [section_heading('Where the holes are')]
    if d['emptyAspects']:
        parts.append(callout(
            f'<strong>{len(d["emptyAspects"])} of the {d["nAspects"]} aspects '
            f'have no article for any community in Uganda:</strong> '
            + esc(', '.join(d['emptyAspects'])) + '. '
            'These are not marginal categories. Traditional craftsmanship and '
            'rituals are two of UNESCO&rsquo;s five domains, and a naming '
            'system is the element Uganda itself nominated in 2013.'))
    if d['emptyGroups']:
        parts.append(note(
            f'<strong>{len(d["emptyGroups"])} communities have no folklore '
            f'article at all under any aspect:</strong> '
            + esc(', '.join(d['emptyGroups'])) +
            '. Several are among the smallest and most pressed communities in '
            'the country, which is the pattern a content gap analysis exists '
            'to find rather than to confirm.'))
    parts.append('<div class="spacer"></div>')
    parts.append(bars([{'label': f['label'],
                        'value': f['articles'],
                        'display': f'{fmt(f["articles"])} across '
                                   f'{f["groups"]} communities'}
                       for f in d['families']]))
    parts.append(note('Articles by language family. The four families are not '
                      'equal in population, so this is a measure of coverage '
                      'and not of importance.'))
    return join(parts)


def _inventories(d):
    rows = [[
        {'html': f'<a href="{esc(i["url"])}" target="_blank" '
                 f'rel="noopener">{esc(i["holder"])}</a>'},
        {'text': i['what']},
        {'text': i['note'], 'dim': True},
    ] for i in d['inventories']]
    return join([
        section_heading(
            'The inventories this should be reconciled against',
            'Named here because they exist and matter, and listed as '
            'outstanding rather than counted as data.'),
        plain_table([{'label': 'Holder'}, {'label': 'What it holds'},
                     {'label': 'Why it matters'}], rows),
        callout(
            '<strong>None of these are loaded.</strong> None publishes a '
            'machine-readable inventory, so nothing on this page comes from '
            'them. They are the next piece of work, and the reconciliation is '
            'the point at which this grid stops being a measure of Wikipedia '
            'and starts being a measure of Uganda: the Ministry&rsquo;s '
            'community inventories already record traditions that have no '
            'article, and matching the two lists is what turns an empty cell '
            'into a named, citable thing to write.'),
    ])


def render(d):
    tiles = [
        {'k': 'Communities', 'v': d['nGroups'],
         'd': 'across four language families'},
        {'k': 'Grid filled', 'raw': True, 'v': f'{d["fillShare"]:.0f}%',
         'd': f'{fmt(d["filled"])} of {fmt(d["cells"])} cells have an article',
         'alarm': True},
        {'k': 'Inscribed, undocumented', 'raw': True,
         'v': f'{len(d["ichUndocumented"])} / {len(d["ich"])}',
         'd': 'UNESCO elements with no article in any language',
         'alarm': True},
        {'k': 'Articles found', 'v': d['nArticles'],
         'd': f'from {fmt(d["nDistinct"])} candidates, '
              f'{fmt(d["nDropped"])} dropped as not heritage'},
    ]
    return join([
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),
        section_heading('The headline'),
        stat_tiles(tiles),
        callout(
            '<strong>Three of Uganda&rsquo;s six UNESCO-inscribed traditions '
            'have no Wikipedia article in any language:</strong> the Lango '
            'male-child cleansing ceremony, the Koogere oral tradition and the '
            'Ma&rsquo;di bowl lyre. All three sit on the Urgent Safeguarding '
            'List, which is the list a tradition reaches when UNESCO judges it '
            'at risk of disappearing. A tradition can be formally recognised '
            'by the world as endangered and still have nowhere on the open web '
            'that describes what it is.'),
        _anchors(d),
        _matrix(d),
        _gaps(d),
        _inventories(d),
        page_footer([
            '<strong>How the grid is built.</strong> For each community, a '
            'search of English Wikipedia for articles whose title carries the '
            'community&rsquo;s name or one of its variants, restricted to '
            'pages about Uganda. Variants matter: the Ganda people are '
            'Baganda, their language Luganda and their kingdom Buganda, and an '
            'article may sit under any of them. Each result is sorted into an '
            'aspect by vocabulary.',

            '<strong>What the grid undercounts.</strong> It only sees articles '
            'whose title names a community, so an article titled for the '
            'practice alone is invisible to it. Empaako and Kasubi Tombs are '
            'both real coverage and neither appears in a cell. Treat every '
            'number as a floor. The inscribed elements above are checked '
            'separately and exactly, through Wikidata sitelinks.',

            '<strong>What was deliberately thrown away.</strong> A community '
            'name in a title does not make an article heritage. Football '
            'clubs, schools, hotels, constituencies and counties carry these '
            'names too, and '
            f'{fmt(d["nDropped"])} of {fmt(d["nDistinct"])} candidates were '
            'dropped for that reason. Acholi Queens FC is not folklore.',

            '<strong>Rebuild.</strong> <code>python '
            'src_data/folklore_matrix.py</code>, then <code>python '
            'src_viz/export_data.py</code> and <code>python '
            'src_viz/build_pages.py folklore</code>. Full exports are in '
            '<code>data/ug_folklore_articles.csv</code>, '
            '<code>data/ug_folklore_matrix.csv</code> and '
            '<code>data/ug_folklore_anchors.csv</code>.',
        ]),
        '</div>',
    ])
