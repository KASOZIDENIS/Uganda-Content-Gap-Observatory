# -*- coding: utf-8 -*-
"""Office holders who are not on Wikimedia at all.

The pages that do not start from Wikimedia: the input is a roster of real
appointments, because someone absent from both Wikidata and Wikipedia is
invisible to a query against either.

One renderer, both cohorts. The women's and men's pages are the same page over
different rows of roster_status; the copy that differs arrives in the view
model from COHORT_COPY in export_data.py.
"""

from render import (tab_bar, eyebrow, section_heading, note, callout,
                    page_footer, stat_tiles, chip, plain_table, wikidata_link,
                    filter_controls, data_table, td, esc, fmt, join)


def _status_cell(p):
    """The status chip, plus whatever links do exist for that person."""
    extras = []
    if p['qid']:
        extras.append(wikidata_link(p['qid'], 'mono'))
    for lang, title in (('en', p['enTitle']), ('lg', p['lgTitle'])):
        if title:
            url = f'https://{lang}.wikipedia.org/wiki/{title.replace(" ", "_")}'
            extras.append(f'<a href="{esc(url)}" target="_blank" '
                          f'rel="noopener">{lang}</a>')
    out = chip(f'st-{p["status"]}', p['statusLabel'])
    if extras:
        out += f' <span class="dim">{" &middot; ".join(extras)}</span>'
    return out


def _split_table(rows, first_heading):
    return plain_table(
        columns=[{'label': first_heading},
                 {'label': 'On the roster', 'num': True},
                 {'label': 'Nothing on Wikimedia', 'num': True},
                 {'label': 'Share', 'num': True}],
        rows=[[{'text': r['label']},
               {'text': fmt(r['total'])},
               {'text': fmt(r['absent']), 'strong': True},
               {'text': f'{r["share"]}%', 'dim': True}] for r in rows])


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        f'<h1>{esc(d["heading"])}</h1>',
        f'<p class="lede">{fmt(d["nAbsent"])} of the {fmt(d["total"])} '
        f'{esc(d["noun"])} on this roster {esc(d["lede"])}, and have '
        f'<strong>no Wikidata item and no Wikipedia article in any '
        f'language</strong>. Not a thin article. Nothing.</p>',
        f'<p class="stamp"><strong>This page does not start from '
        f'Wikimedia.</strong> Every other page asks what Wikipedia is missing '
        f'relative to Wikidata, which cannot answer this question: someone '
        f'absent from both is invisible to a query against either. So the '
        f'input is a roster of real appointments gathered from official '
        f'leadership pages and the Ugandan press, covering '
        f'{esc(d["sectors"])}, and each name is then looked up. Every row '
        f'carries its source.</p>',
        '</header>',
    ])


def _how_it_works(labels):
    rows = [
        ('absent', 'No item and no article matched the name',
         'Create, if the sources support it'),
        ('wikidata_only', 'An item covers the name, no article does',
         'Write the article; the item is the scaffold'),
        ('possible_match', 'Something with a similar name exists',
         'Confirm by hand before acting'),
        ('documented', 'An article covers the name', 'Nothing'),
    ]
    body = [f'<tr><td>{chip(f"st-{key}", labels[key])}</td>'
            f'<td>{esc(means)}</td><td>{esc(todo)}</td></tr>'
            for key, means, todo in rows]
    return ('<table class="plain">\n<thead><tr><th>Status</th>'
            '<th>What it means</th><th>What to do</th></tr></thead>\n'
            '<tbody>\n' + join(body) + '\n</tbody>\n</table>')


def _row(p, i):
    if p['sourceUrl']:
        source = (f'<a href="{esc(p["sourceUrl"])}" target="_blank" '
                  f'rel="noopener">source</a>')
    else:
        source = '<span class="dim">none</span>'
    return (td(i + 1, 'num', 'dim')
            + td(f'<strong>{esc(p["name"])}</strong>')
            + td(esc(p['office']), 'dim')
            + td(esc(p['organisation']), 'dim')
            + td(chip(f'rk-{p["rank"]}', p['rankLabel']))
            + td(_status_cell(p))
            + td(source))


def render(d):
    labels = d['statusLabels']
    start_list = ''.join(
        f'<li><strong>{esc(p["name"])}</strong>, {esc(p["office"])}, '
        f'{esc(p["organisation"])}</li>' for p in d['topAbsent'])

    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),

        section_heading('The headline'),
        stat_tiles([
            {'k': 'Nothing on Wikimedia', 'v': d['nAbsent'], 'alarm': True,
             'd': f'{esc(d["absentShare"])}% of the roster, no item and no article'},
            {'k': 'Wikidata only', 'v': d['nWikidataOnly'],
             'd': 'an item exists to hang sources on, but no article'},
            {'k': 'Already covered', 'v': d['nDocumented'],
             'd': f'plus {fmt(d["nPossible"])} where a similar name needs a '
                  f'human check'},
            {'k': 'Roster size', 'v': d['total'],
             'd': f'across {fmt(d["organisations"])} institutions, and nowhere '
                  f'near complete'},
        ]),

        callout(
            f'<strong>Start here.</strong> These {esc(d["noun"])} head their '
            f'institution '
            'outright and have nothing on Wikimedia at all:'
            f'<ul class="startlist">{start_list}</ul>'
            f'{d["calloutTail"]} Offices at this level are documented in '
            f'the national press, in Hansard and in official gazettes, so '
            f'sources exist; nobody has written the articles.'),

        section_heading('Where the gap sits', d['gapReading']),
        _split_table(d['bySector'], 'Sector'),
        '<div class="spacer"></div>',
        _split_table(d['byRank'], 'Level of office'),

        section_heading(
            'How the check works',
            'Each roster name is searched against Wikidata labels and '
            'aliases, then against English and Luganda Wikipedia. Ugandan '
            "naming order varies and Wikidata's search is a prefix match, so "
            'each name is tried several ways: in full, first and last name, '
            'and surname alone. Matching is on name tokens rather than exact '
            'strings, which is why the result is four-valued rather than a '
            'yes or no.'),
        _how_it_works(labels),
        note(f'<strong>A status of &ldquo;{esc(labels["absent"])}&rdquo; is a '
             'statement about a search, not proof that a person is '
             'undocumented.</strong> A name spelled differently on Wikidata, '
             'or recorded under a married or maiden name, will read as absent '
             'here. Check before creating.'),

        section_heading(
            'The roster',
            f'All {fmt(d["total"])} names, those with nothing on Wikimedia '
            'first and the most senior offices before the rest. The source '
            'column is the page the appointment came from, and it is the '
            'first thing to read before writing anything.'),

        filter_controls(
            total=d['total'],
            count_noun='names',
            search_label='Filter the roster',
            search_placeholder=(f'Filter {fmt(d["total"])} names by person, '
                                f'office or institution'),
            groups=[
                {'key': 'status', 'label': 'Filter by Wikimedia status',
                 'allLabel': 'Every status',
                 'options': [{'value': s, 'label': labels[s],
                              'count': d['statusCounts'][s]}
                             for s in d['statusOrder']
                             if d['statusCounts'].get(s)]},
                {'key': 'sector', 'label': 'Filter by sector',
                 'allLabel': 'Every sector',
                 'options': [{'value': r['key'], 'label': r['label'],
                              'count': r['total']} for r in d['bySector']]},
            ]),

        data_table(
            rows=d['people'],
            row_attrs=lambda p: {'data-status': p['status'],
                                 'data-sector': p['sector']},
            columns=[
                {'label': '#', 'num': True}, {'label': 'Name'},
                {'label': 'Office'}, {'label': 'Institution'},
                {'label': 'Level'}, {'label': 'On Wikimedia'},
                {'label': 'Appointment'},
            ],
            render_row=_row),

        page_footer([
            '<strong>Holding a big office is not the same as being '
            'notable.</strong> This is a candidate list, not a to-write list. '
            'Wikipedia needs significant coverage in independent reliable '
            'sources before an article is justified, and a leadership page on '
            "an employer's own website is not that. Wikidata's bar is lower "
            'and most of these names would clear it, which is why the two '
            'statuses are reported separately. Anyone working from this list '
            'should start from the sources, not from the row.',

            '<strong>The roster is the part a human owns.</strong> It lives '
            f'at <code>data/{esc(d["rosterFile"])}</code> with one row per '
            'person: <code>name, office, organisation, sector, rank, '
            'source_url</code>. It was seeded from official leadership pages '
            'and Ugandan press reporting and is deliberately partial: '
            f'{fmt(d["total"])} names across {fmt(d["organisations"])} '
            'institutions is a sample, not a census, and it currently '
            'over-represents the institutions that publish their leadership. '
            'Add rows, re-run <code>python src_data/roster_check.py</code>, '
            'then <code>python src_viz/export_data.py</code> and '
            '<code>python src_viz/build_pages.py</code>, and this page '
            'follows.',

            '<strong>Names and offices are as recorded by the cited source on '
            'the date it was read, and people change jobs.</strong> Nothing '
            'here is personal information: it is the name, the public office '
            'and the source that states it, which is what an editor needs and '
            'no more.',
        ]),
        '</div>',
    ]
    return join(parts)
