# -*- coding: utf-8 -*-
"""Ugandan women who held public office, and which of them Wikipedia covers.

Office comes from Wikidata P39 rather than from job title, so a woman appears
here because a position is recorded against her; seniority is read from the
position's label.
"""

from render import (tab_bar, eyebrow, section_heading, note, callout,
                    page_footer, stat_tiles, bars, chip, plain_table, mini_bar,
                    wikidata_link, filter_controls, data_table, td, attr,
                    esc, fmt, join)

NO_P27_TITLE = ('No Ugandan citizenship recorded in Wikidata: either a '
                'missing statement or a foreign envoy posted to Uganda')


def _person_name(w):
    """The name, linked to whichever article exists.

    Two different situations wear the no-P27 marker: a Ugandan office holder
    whose citizenship statement is missing, and a foreign envoy posted to
    Kampala. The positions column is what tells them apart.
    """
    lang = 'en' if w['enTitle'] else ('lg' if w['lgTitle'] else None)
    title = w['enTitle'] or w['lgTitle']
    if lang:
        url = f'https://{lang}.wikipedia.org/wiki/{title.replace(" ", "_")}'
        name = (f'<a href="{esc(url)}" target="_blank" rel="noopener">'
                f'{esc(w["label"])}</a>')
    else:
        name = esc(w['label'])
    if not w['citizen']:
        name += (f' <span class="noflag" title="{esc(NO_P27_TITLE)}">'
                 f'no P27</span>')
    return name


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>Ugandan women who held public office, and which of them '
        'Wikipedia has written about</h1>',
        f'<p class="lede">Wikidata records {fmt(d["nOffice"])} women in '
        'Ugandan public office: in parliament, the cabinet, the courts, the '
        'civil service, the diplomatic service and local government. '
        f'{fmt(d["nWith"])} have an article somewhere. <strong>'
        f'{fmt(d["nNone"])} have none in any language.</strong> Only '
        f'{fmt(d["nTranslate"])} need translating into Luganda, which is the '
        'finding that should redirect the work.</p>',
        '<p class="stamp"><strong>Office comes from Wikidata P39, not from '
        'job title.</strong> A woman counts here because a position is '
        "recorded against her, and seniority is read from the position's "
        'label. Academic, corporate and ceremonial roles are excluded, which '
        f'is why {fmt(d["nOtherRole"])} more women with a P39 of some kind '
        'sit outside the count and are marked '
        f'&ldquo;{esc(d["otherTierLabel"])}&rdquo; in the list below.</p>',
        '</header>',
    ])


def _tier_table(tiers):
    head = ('<tr><th>Level of office</th><th class="num">Women</th>'
            '<th class="num">With article</th><th class="num">With none</th>'
            '<th class="num">Covered</th><th>&nbsp;</th></tr>')
    body = [
        f'<tr><td>{esc(t["label"])}</td>'
        f'<td class="num">{fmt(t["holders"])}</td>'
        f'<td class="num">{fmt(t["withArticle"])}</td>'
        f'<td class="num">{fmt(t["none"])}</td>'
        f'<td class="num">{esc(t["coveredText"])}%</td>'
        f'<td>{mini_bar(t["covered"])}</td></tr>'
        for t in tiers
    ]
    return ('<table class="plain">\n<thead>' + head + '</thead>\n<tbody>\n'
            + join(body) + '\n</tbody>\n</table>')


def _row(w, i):
    return (td(i + 1, 'num', 'dim')
            + td(_person_name(w))
            + td(esc(w['description']), 'dim')
            + td(esc(w['positions']), 'dim')
            + td(chip(f't-{w["tier"]}', w['tierLabel']))
            + td(chip(f's-{w["status"]}', w['statusLabel']))
            + td(fmt(w['sitelinks']), 'num')
            + td(fmt(w['statements']), 'num', 'dim')
            + td(wikidata_link(w['qitem']), 'mono'))


def render(d):
    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),

        section_heading('The headline'),
        stat_tiles([
            {'k': 'Women in public office', 'v': d['nOffice'],
             'd': f'across {fmt(d["positionsSeen"])} distinct recorded positions'},
            {'k': 'No article anywhere', 'v': d['nNone'], 'alarm': True,
             'd': f'{esc(d["noneShare"])}% of them, and this is where the work is'},
            {'k': 'Needs Luganda translation', 'v': d['nTranslate'],
             'd': f'{fmt(d["nBoth"])} already have both English and Luganda'},
            {'k': 'Best and worst covered', 'raw': True,
             'v': f'{esc(d["best"]["coveredText"])}% / '
                  f'{esc(d["worst"]["coveredText"])}%',
             'd': f'{esc(d["best"]["label"])} against {esc(d["worst"]["label"])}'},
        ]),

        section_heading(
            'The three groups',
            'These are the three questions this page was built to answer. '
            f'Percentages are of the {fmt(d["nOffice"])} women in public '
            'office; the translation group is a subset of those who already '
            'have an article, not a fourth category.'),
        plain_table(
            columns=[{'label': 'Group'}, {'label': 'Women', 'num': True},
                     {'label': 'Share', 'num': True},
                     {'label': 'What the work is'}],
            rows=[[{'text': g['label'], 'strong': True},
                   {'text': fmt(g['count']), 'strong': True},
                   {'text': f'{g["share"]}%', 'dim': True},
                   {'text': g['work'], 'dim': True}] for g in d['groups']]),

        callout(
            '<strong>The translation backlog for office holders is '
            f'finished.</strong> {fmt(d["nBoth"])} of the {fmt(d["nWith"])} '
            'women with an article have one in both English and Luganda, '
            f'leaving {fmt(d["nTranslate"])} to translate. A campaign framed '
            'as &ldquo;translate women politicians into Luganda&rdquo; has '
            f'almost nothing left to do. The {fmt(d["nNone"])} women with no '
            'article at all need writing from sources instead, which is '
            'different work needing different partners.'),

        section_heading(
            'Coverage by level of office',
            'Coverage tracks how visible the office is rather than how much '
            f'power it carries. {esc(d["best"]["label"])} is at '
            f'{esc(d["best"]["coveredText"])}%; {esc(d["worst"]["label"])} is '
            f'at {esc(d["worst"]["coveredText"])}%.'),
        _tier_table(d['tiers']),

        section_heading(
            'Which offices are missing the most women',
            'Ranked by how many holders of each position have no article '
            'anywhere, so a campaign can be aimed at one office at a time.'),
        bars([{'label': o['label'], 'value': o['noArticle'],
               'display': f'{fmt(o["noArticle"])} of {fmt(o["holders"])}'}
              for o in d['worstOffices']]),
        note('Read as: of everyone recorded in that position, this many have '
             'no article in any language. A woman who held several offices is '
             'counted under each.'),

        callout(
            f'<strong>{fmt(d["nMissingP27"])} women hold a Ugandan office '
            'with no citizenship statement in Wikidata.</strong> They are '
            'MPs, ministers and judges whose <code>P27</code> is simply '
            'missing, which means every analysis keyed on citizenship, '
            "including this project's own women's worklists, silently omits "
            'them. Adding one statement each fixes that. Separately, '
            f'{fmt(d["nForeign"])} of the diplomats listed here represent '
            'other countries in Kampala rather than Uganda abroad; both '
            'groups carry a <span class="noflag">no P27</span> marker in the '
            'list.'),

        section_heading(
            'Every office holder',
            f'All {fmt(d["total"])} women with a position recorded against '
            'them, most senior office first, then by how much Wikidata '
            'already knows about each one, because that is the order in which '
            'the missing articles are easiest to source. Names link to the '
            'article where one exists, and the item column links to Wikidata, '
            'which is where the sourcing starts when it does not.'),

        filter_controls(
            total=d['total'],
            count_noun='women',
            search_label='Filter office holders',
            search_placeholder=(f'Filter {fmt(d["total"])} women by name, '
                                f'description or office'),
            groups=[
                {'key': 'group', 'label': 'Filter by article status',
                 'allLabel': 'Every status',
                 'options': [{'value': g['key'], 'label': g['label'],
                              'count': g['count']} for g in d['groupFilters']]},
                {'key': 'tier', 'label': 'Filter by level of office',
                 'allLabel': 'Every office',
                 'options': [{'value': t['key'], 'label': t['label'],
                              'count': t['holders']} for t in d['tiers']]
                            + [{'value': 'other',
                                'label': d['otherTierLabel'],
                                'count': d['nOtherRole']}]},
            ]),

        data_table(
            rows=d['women'],
            row_attrs=lambda w: {'data-tier': w['tier'], 'data-group': w['group']},
            columns=[
                {'label': '#', 'num': True}, {'label': 'Name'},
                {'label': 'Wikidata description'},
                {'label': 'Positions recorded'}, {'label': 'Level'},
                {'label': 'Article status'},
                {'label': 'Editions', 'num': True},
                {'label': 'Statements', 'num': True}, {'label': 'Item'},
            ],
            render_row=_row),

        page_footer([
            '<strong>Method.</strong> Two Wikidata retrieval branches are '
            'unioned: women with Ugandan citizenship who have any '
            '<code>P39</code> position, and women holding a position whose '
            'jurisdiction or country is Uganda, which catches office holders '
            'with no citizenship statement. Seniority is assigned by matching '
            'the position label against ordered keyword lists in '
            '<code>src_data/config.py</code>, so &ldquo;Justice Minister of '
            'Uganda&rdquo; reads as cabinet rather than as a court, and '
            '&ldquo;permanent representative&rdquo; as a diplomat rather than '
            'an MP. The matching is approximate and the label lists are '
            'visible in that file.',

            "<strong>What this cannot tell you.</strong> Wikidata's record of "
            'who held which Ugandan office is itself incomplete, so absence '
            'here is not proof that a woman never held office. Term dates are '
            'recorded for only a minority of positions, so the page does not '
            'separate current holders from former ones. Structured data from '
            'Wikidata (CC0); article titles from Wikipedia (CC BY-SA). '
            'Rebuild with <code>python src_data/office_analysis.py</code>, '
            'then <code>python src_viz/export_data.py</code> and '
            '<code>python src_viz/build_pages.py</code>.',
        ]),
        '</div>',
    ]
    return join(parts)
