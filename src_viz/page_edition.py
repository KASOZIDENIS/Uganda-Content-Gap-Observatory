# -*- coding: utf-8 -*-
"""Every Uganda article in whichever edition holds the most of them.

The page follows the ranking rather than naming an edition in advance, so the
language code is read from the view model and printed throughout.
"""

from render import (tab_bar, eyebrow, section_heading, note, page_footer,
                    stat_tiles, bars, chip, wiki_link, filter_controls,
                    data_table, td, esc, fmt, join)

WEAK_TITLE = ('Reached only by a weak retrieval strategy, so its link to '
              'Uganda may be incidental')


def _header(d, code):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        f'<h1>All {fmt(d["total"])} Uganda articles in {esc(code)}wiki, and '
        f'what they are about</h1>',
        f'<p class="lede">{esc(code)}wiki holds more Uganda articles than any '
        f'other Wikipedia edition, including English. {fmt(d["people"])} of '
        f'them {esc(d["peopleWord"])}. This page lists every one so that claim '
        f'can be checked rather than taken on trust.</p>',
        '<p class="stamp"><strong>Every row is generated from the same '
        'database as the dashboard.</strong> The edition shown is whichever '
        'one ranks first this cycle, so this page follows the ranking rather '
        'than naming an edition in advance. Back to the '
        f'<a href="{esc(d["dashboardHref"])}">findings</a>.</p>',
        '</header>',
    ])


def _row(item, i, code):
    title = wiki_link(code, item['title'])
    if not item['core']:
        title += (f' <span class="weak" title="{esc(WEAK_TITLE)}">'
                  f'weak link</span>')
    label = (esc(item['label']) if item['label']
             else '<span class="nolabel">no English label</span>')
    return (td(i + 1, 'num', 'dim')
            + td(title)
            + td(label, 'dim')
            + td(esc(item['types']), 'dim')
            + td(fmt(item['sitelinks']), 'num')
            + td(chip(item['bucket'], item['bucketLabel']))
            + td(esc(item['qitem']), 'dim', 'mono'))


def render(d):
    code = d['languagecode']
    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d, code),

        section_heading('The shape of it'),
        stat_tiles([
            {'k': 'Uganda articles', 'v': d['total'],
             'd': esc(d['shareOfEdition'])},
            {'k': 'Biographies', 'v': d['people'], 'alarm': True,
             'd': f'{esc(d["peopleShare"])}% of the Uganda articles'},
            {'k': 'Places &amp; nature', 'v': d['places'],
             'd': f'{esc(d["placesShare"])}% of the Uganda articles'},
            {'k': 'Commonest single type', 'v': d['topTypeCount'],
             'd': esc(d['topType'])},
        ]),

        section_heading(
            'What the articles are about',
            "Counted on each item's first Wikidata type. A collection "
            'dominated by streams, hills and sub-counties is the signature of '
            'bot generation from a geographic registry, not of editors '
            'choosing what to write about.'),
        bars(d['typeBars']),
    ]

    tail = d.get('typeTail')
    if tail:
        parts.append(note(
            f'These {fmt(tail["kinds"])} types account for '
            f'{fmt(tail["shown"])} of {fmt(d["total"])} articles '
            f'({esc(tail["share"])}%). The remaining {fmt(tail["rest"])} are '
            f'spread over {fmt(tail["restKinds"])} further types.'))

    parts += [
        section_heading(
            'Every article',
            'Sorted so the biographies come first, then by how many language '
            f'editions carry the topic. Titles link to {esc(code)}wiki. '
            f'{fmt(d["weakOnly"])} of these reached the corpus only through a '
            'weak retrieval strategy and are marked accordingly: they are why '
            'a Uganda list can contain a country or a head of state who is '
            f'not Ugandan. {fmt(d["unlabelled"])} of them carry no English '
            'label in Wikidata at all, which is its own signal of how they '
            'were created.'),

        filter_controls(
            total=d['total'],
            count_noun='articles',
            search_label='Filter articles',
            search_placeholder=(f'Filter {fmt(d["total"])} articles by title, '
                                f'English label or type'),
            groups=[{
                'key': 'bucket',
                'label': 'Filter by category',
                'allLabel': 'All',
                'options': [{'value': b['key'], 'label': b['label'],
                             'count': b['count']} for b in d['buckets']],
            }]),

        data_table(
            rows=d['items'],
            row_attrs=lambda it: {'data-bucket': it['bucket']},
            columns=[
                {'label': '#', 'num': True},
                {'label': f'{code}wiki title'},
                {'label': 'English label'},
                {'label': 'Wikidata type'},
                {'label': 'Editions', 'num': True},
                {'label': 'Category'},
                {'label': 'Item'},
            ],
            render_row=lambda it, i: _row(it, i, code)),

        page_footer([
            '<strong>Method.</strong> The corpus is Wikidata items about '
            'Uganda carrying at least one Wikipedia sitelink; this page is '
            f'the subset with a sitelink to {esc(code)}wiki. Category is '
            "assigned by substring-matching the item's Wikidata type labels, "
            'which is approximate: an airport lands in &ldquo;everything '
            'else&rdquo; rather than in institutions, for instance. Counts '
            'here match the dashboard because both use the same rule.',

            'Article text and titles from Wikipedia (CC BY-SA), structured '
            'data from Wikidata (CC0). Rebuild with '
            '<code>python src_viz/export_data.py</code> then '
            '<code>python src_viz/build_pages.py</code>.',
        ]),
        '</div>',
    ]
    return join(parts)
