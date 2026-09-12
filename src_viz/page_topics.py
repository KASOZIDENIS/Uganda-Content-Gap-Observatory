# -*- coding: utf-8 -*-
"""Topic areas: last year's readership joined to this year's coverage.

The page the previous cycle's analysis was one join away from. It keeps their
topic axis and their demand figures, corrects the collection, and adds the
half they could not see: whether Uganda's own language has the article.
"""

import charts
from render import (bars, callout, data_table, esc, eyebrow, filter_controls,
                    fmt, join, note, page_footer, plain_table, section_heading,
                    stat_tiles, tab_bar, td, wiki_link)


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>What Uganda&rsquo;s readers look for, and what Luganda does not '
        'have</h1>',
        f'<p class="lede">Last year&rsquo;s analysis ranked {fmt(d["nTopics"])} '
        f'Uganda articles on English Wikipedia by how much they are read, and '
        f'published a top ten per topic area. It never asked whether any of '
        f'those topics exist in Uganda&rsquo;s own language. '
        f'<strong>{d["unservedShare"]}% of the readership it measured, once '
        f'the collection is corrected, is on topics with no Luganda '
        f'article.</strong></p>',
        f'<p class="stamp"><strong>Their topic areas, our coverage.</strong> '
        f'The eleven areas and the view figures come from the previous '
        f'cycle&rsquo;s exports in <code>training data/</code>, which is the '
        f'one thing this project had no equivalent of: a reader-facing topic '
        f'axis rather than a Wikidata type. Everything about coverage comes '
        f'from this cycle&rsquo;s database, which knows all 343 editions '
        f'rather than English alone. Back to the '
        f'<a href="{esc(d["hrefs"]["dashboard"])}">findings</a>.</p>',
        '</header>',
    ])


def _correction(d):
    """The precision problem in their collection, stated with its numbers."""
    rows = [[
        {'text': a['label']},
        {'text': fmt(a['topics'])},
        {'text': fmt(a['reportedViews'])},
        {'text': fmt(a['structuralViews']), 'strong': True},
        {'text': a['offTopicText'] + '%', 'dim': True},
    ] for a in sorted(d['areas'], key=lambda a: -a['offTopicViews'])]
    return join([
        section_heading(
            'First, a correction',
            'Their categories were built from Wikipedia category membership, '
            'which sweeps in topics that have no structural link to Uganda at '
            'all. Every topic here was re-checked against Wikidata for the '
            'test this project&rsquo;s own worklists use: country, a location '
            'inside Uganda, Ugandan citizenship, or birth or death there.'),
        plain_table(
            [{'label': 'Area'}, {'label': 'Topics', 'num': True},
             {'label': 'Views reported', 'num': True},
             {'label': 'Of those, Ugandan', 'num': True},
             {'label': 'Off-topic', 'num': True}],
            rows),
        callout(
            f'<strong>Their single largest entry is Elizabeth II, at 8,605,054 '
            f'views in the &ldquo;Governance in Uganda&rdquo; export.</strong> '
            f'That one row is 62% of all the readership their analysis '
            f'measured, and their write-up attributes the dominance of '
            f'Governance to Idi Amin and Museveni instead, who sit in a '
            f'different file and account for 2.1 million between them. She '
            f'reaches this project&rsquo;s corpus too, by title keyword, and '
            f'is held off every worklist for exactly this reason. Mount Kenya, '
            f'Ngorongoro, Mount Meru, Amboseli and Virunga are all filed under '
            f'Geography of Uganda as well. Of the '
            f'{fmt(d["reportedViews"])} views reported, '
            f'{fmt(d["structuralViews"])} are on topics with a structural link '
            f'to Uganda; the remaining {fmt(d["offTopicViews"])} '
            f'({d["offTopicShare"]}%) are not.'),
    ])


def _areas(d):
    rows = [[
        {'text': a['label']},
        {'text': fmt(a['coreTopics'])},
        {'text': fmt(a['inLuganda'])},
        {'text': fmt(a['missing']), 'strong': True},
        {'text': fmt(a['unserved'])},
        {'text': a['coveredText'] + '%', 'dim': True},
    ] for a in d['areas']]
    return join([
        section_heading(
            'Where the unserved demand is',
            'Structurally Ugandan topics only, ordered by how much measured '
            'readership sits on the ones Luganda does not have. That last '
            'number is the one worth aiming a campaign at: it is reader '
            'interest that Uganda&rsquo;s own Wikipedia cannot currently '
            'answer.'),
        plain_table(
            [{'label': 'Area'}, {'label': 'Topics', 'num': True},
             {'label': 'In Luganda', 'num': True},
             {'label': 'Missing', 'num': True},
             {'label': 'Unserved views', 'num': True},
             {'label': 'Covered', 'num': True}],
            rows),
        '<div class="spacer"></div>',
        bars([{'label': a['label'], 'value': a['unserved'],
               'display': fmt(a['unserved'])} for a in d['areas']
              if a['unserved']]),
        note('Bars are unserved views per area. Geography carries the most by '
             'a wide margin, which is the same conclusion the action plan '
             'reached from the other direction: Luganda has Ugandan people and '
             'not Ugandan places.'),
    ])


def _worklist(d):
    columns = [
        {'label': '#', 'num': True}, {'label': 'Topic'},
        {'label': 'Area'}, {'label': 'Views', 'num': True},
        {'label': 'Editions', 'num': True}, {'label': 'English article'},
    ]

    def row(t, i):
        return join([
            td(str(i + 1), 'num', 'dim'),
            td(f'<strong>{esc(t["title"])}</strong>'),
            td(esc(t['area'])
               + (f' <span class="alsoin">also in '
                  f'{esc(", ".join(a for a in t["areas"].split(", ") if a != t["area"]))}'
                  f'</span>' if ', ' in t['areas'] else ''), 'dim'),
            td(fmt(t['theirViews']), 'num'),
            td(fmt(t['editions']), 'num', 'dim'),
            td(wiki_link('en', t['enTitle']) if t['enTitle']
               else '<span class="dim">not in English either</span>'),
        ])

    areas = sorted({t['area'] for t in d['worklist']})
    counts = {}
    for t in d['worklist']:
        counts[t['area']] = counts.get(t['area'], 0) + 1
    return join([
        section_heading(
            'The worklist their ranking was one join away from',
            f'The {fmt(d["nWorklistTopics"])} structurally Ugandan topics in '
            f'their areas that have no Luganda article, most-read first. '
            f'Their ranking already knew which topics readers want; adding '
            f'one column from this cycle&rsquo;s database turns it into a list '
            f'of what to write. A topic filed under several areas appears '
            f'under each of them, so the {fmt(d["nWorklistRows"])} rows here '
            f'are memberships rather than distinct topics, and the per-area '
            f'counts match the table above.'),
        filter_controls(
            groups=[{'key': 'area', 'label': 'Filter by topic area',
                     'allLabel': 'Every area',
                     'options': [{'value': a, 'label': a,
                                  'count': counts[a]} for a in areas]}],
            total=d['nWorklistRows'], count_noun='entries',
            search_placeholder=f'Filter {fmt(d["nWorklistRows"])} entries by '
                               f'topic or area',
            search_label='Filter the worklist'),
        data_table(d['worklist'], columns, row,
                   row_attrs=lambda t: {'data-area': t['area']}),
    ])


def _audit(d):
    if not d['verified']:
        return note('Run <code>python src_data/topic_verify.py</code> to '
                    'settle which of their topics this project missed.')
    misses = join(
        f'<li><strong>{esc(t["title"])}</strong>, {esc(t["areas"])}, '
        f'{fmt(t["theirViews"])} views</li>' for t in d['recallMisses'])
    over = join(
        f'<li>{esc(t["title"])} <span class="dim">&middot; '
        f'{esc(t["areas"])} &middot; {fmt(t["theirViews"])} views</span></li>'
        for t in d['overCollected'])
    return join([
        section_heading(
            'Read the other way, this audits us',
            'Their category lists are an independent check on this '
            'project&rsquo;s recall, which the dashboard describes as a floor '
            'rather than an exact count. Every imported topic absent from our '
            'corpus was asked the structural question directly.'),
        '<div class="audit">',
        '<div>',
        f'<h3>{fmt(len(d["recallMisses"]))} we should have caught</h3>',
        '<p>Genuinely Ugandan by the same test the worklists use, and absent '
        'from our corpus. Two in a sample of '
        f'{fmt(d["nTopics"])} is a better recall result than the '
        'dashboard&rsquo;s own caveat implies, and both are worth adding.</p>',
        f'<ul class="startlist">{misses}</ul>',
        '</div>',
        '<div>',
        f'<h3>{fmt(d["nOverCollected"])} their categories over-collected</h3>',
        '<p>No structural link to Uganda. Not errors on their part so much as '
        'the cost of collecting by category rather than by statement, but they '
        'carry most of the reported readership, so a plan built on that '
        'ranking would be aimed largely at other countries. The heaviest '
        'fifteen:</p>',
        f'<ul class="overlist">{over}</ul>',
        '</div>',
        '</div>',
    ])


def render(d):
    return join([
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),
        section_heading('The headline'),
        stat_tiles([
            {'k': 'Topics imported', 'v': d['nTopics'],
             'd': f'across {fmt(d["nAreas"])} topic areas, '
                  f'{fmt(d["nCore"])} of them structurally Ugandan'},
            {'k': 'Unserved readership', 'v': d['unservedViews'], 'alarm': True,
             'd': f'{d["unservedShare"]}% of measured demand on Ugandan '
                  f'topics is on ones Luganda lacks'},
            {'k': 'Covered in Luganda', 'raw': True,
             'v': f'{fmt(d["nInLuganda"])} / {fmt(d["nCore"])}',
             'd': f'{d["coveredShare"]}% of them, and {fmt(d["nStubs"])} of '
                  f'those are under 2&nbsp;KB'},
            {'k': 'Off-topic in their data', 'v': d['offTopicViews'],
             'd': f'{d["offTopicShare"]}% of reported views, on topics with no '
                  f'structural link to Uganda'},
        ]),
        _correction(d),
        _areas(d),
        _worklist(d),
        _audit(d),
        page_footer([
            '<strong>What came from where.</strong> The topic areas, the '
            'article lists and the view figures are the previous '
            'cycle&rsquo;s, imported from <code>training data/</code> by '
            '<code>src_data/topic_import.py</code>. Coverage, edition counts, '
            'article sizes and the structural test are this cycle&rsquo;s, '
            'from <code>uganda_diversity.db</code>. Neither half produces this '
            'page alone.',
            f'<strong>On the view figures.</strong> The window behind them is '
            f'not documented in the source material. For the {fmt(d["nOurViews"])} '
            f'topics this project also measured, theirs run roughly twice '
            f'ours, which covers {d["pageviewMonths"]} complete months, so '
            f'the two are never added together or substituted for one '
            f'another. {fmt(d["nNoViews"])} imported topics carry no view '
            f'figure at all and count as zero demand here, which understates '
            f'them. Use these numbers to rank, not to report as absolute '
            f'readership.',
            '<strong>What was dropped on import.</strong> Of their 2,215 rows, '
            '847 are Wikipedia Categories and 15 are Templates, which are '
            'navigation rather than anything a reader reads; only the 1,353 '
            'article rows are kept. 159 of those are a topic filed under a '
            'second area, so per-area view totals cannot be summed across '
            'areas without double counting, and this page never sums them.',
            f'<strong>Rebuild.</strong> <code>python '
            f'src_data/topic_import.py</code>, then <code>python '
            f'src_data/topic_verify.py</code> for the structural check, then '
            f'<code>python src_viz/export_data.py</code> and <code>python '
            f'src_viz/build_pages.py topics</code>. The import is the only '
            f'step that reads <code>training data/</code>; replacing that '
            f'folder with a fresh export is how this page moves to a new '
            f'cycle.',
        ]),
        '</div>',
    ])
