# -*- coding: utf-8 -*-
"""The findings page: nine charts, four worklists and the prose around them.

Every number here is computed in dashboard_view.py and arrives ready to
print, so nothing in this module counts anything.
"""

from render import (tab_bar, section_heading, note, callout, page_footer,
                    stat_tiles, wiki_link, esc, fmt, join)
from charts import chart_from, chart_card, card

WDO_LINK = ('<a href="https://meta.wikimedia.org/wiki/'
            'Wikipedia_Diversity_Observatory" target="_blank" '
            'rel="noopener">Wikipedia Diversity Observatory</a>')


def _chart(d, key, title, subtitle=None, note=None):
    """One chart card, pulling both the series and the table by the same key."""
    return chart_card(
        title=title,
        subtitle=subtitle,
        note=note,
        chart=chart_from(d['charts'][key]),
        table=d['tables'].get(key))


def _worklist(rows):
    """The 'what to write next' tables."""
    if not rows:
        return note('No worklist available: run the pipeline first.')
    body = []
    for i, r in enumerate(rows):
        article = (wiki_link('en', r['enTitle']) if r['enTitle']
                   else '<span class="dim">n/a</span>')
        body.append(
            f'<tr><td class="num">{i + 1}</td>'
            f'<td>{esc(r["label"])}</td>'
            f'<td>{article}</td>'
            f'<td class="num">{fmt(r["sitelinks"])}</td>'
            f'<td class="num">{fmt(r["views"])}</td>'
            f'<td class="num"><strong>{esc(r["priority"])}</strong></td>'
            f'<td class="dim">{esc(r["types"])}</td></tr>')
    return ('<div class="scroller">\n<table class="worklist">\n'
            '<thead><tr><th class="num">#</th><th>Topic</th>'
            '<th>English article</th><th class="num">Editions</th>'
            '<th class="num">Views</th><th class="num">Priority</th>'
            '<th>Type</th></tr></thead>\n<tbody>\n' + join(body)
            + '\n</tbody>\n</table>\n</div>')


def _translate_table(rows):
    if not rows:
        return note('Run <code>women_analysis.py</code> to build this.')
    body = []
    for i, r in enumerate(rows):
        article = (wiki_link('en', r['enTitle']) if r['enTitle']
                   else '<span class="dim">n/a</span>')
        body.append(
            f'<tr><td class="num">{i + 1}</td>'
            f'<td>{esc(r["label"])}</td>'
            f'<td class="dim">{esc(r["field"])}</td>'
            f'<td>{article}</td>'
            f'<td class="num">{fmt(r["sitelinks"])}</td>'
            f'<td class="num">{fmt(r["views"])}</td>'
            f'<td class="dim">{esc(r["occupations"])}</td></tr>')
    return ('<div class="scroller">\n<table class="worklist">\n'
            '<thead><tr><th class="num">#</th><th>Name</th><th>Field</th>'
            '<th>English article</th><th class="num">Editions</th>'
            '<th class="num">Views</th><th>Occupation</th></tr></thead>\n'
            '<tbody>\n' + join(body) + '\n</tbody>\n</table>\n</div>')


def _create_table(rows):
    if not rows:
        return note('Run <code>women_analysis.py</code> to build this.')
    body = [
        f'<tr><td class="num">{i + 1}</td>'
        f'<td>{esc(r["label"])}</td>'
        f'<td class="dim">{esc(r["field"])}</td>'
        f'<td class="num">{fmt(r["statements"])}</td>'
        f'<td class="dim">{esc(r["description"])}</td></tr>'
        for i, r in enumerate(rows)
    ]
    return ('<div class="scroller">\n<table class="worklist">\n'
            '<thead><tr><th class="num">#</th><th>Name</th><th>Field</th>'
            '<th class="num">Wikidata facts</th><th>Described as</th>'
            '</tr></thead>\n<tbody>\n' + join(body) + '\n</tbody>\n</table>\n'
            '</div>')


def _header(d):
    return join([
        '<header class="top">',
        '<p class="eyebrow">Wikipedia content gap analysis &middot; Uganda '
        f'&middot; cycle {esc(d["cycle"])}</p>',
        '<h1>Two different Ugandas exist on Wikipedia, and neither one is '
        'complete</h1>',
        '<p class="lede">A single-territory content gap study modelled on the '
        "Wikipedia Diversity Observatory. Across Wikipedia's "
        f'{fmt(d["editions"])} language editions there are {fmt(d["ccc"])} '
        'Uganda-related topics, but the editions holding the most of them '
        'describe a country of rivers and hills with almost no people in it, '
        'while the one Ugandan-language edition describes people and almost '
        'no country.</p>',
        '</header>',
    ])


def _headline_tiles(d):
    top = d['topEdition']
    if d['topCompPeople'] is None:
        detail = 'articles'
    else:
        detail = f'holds just {fmt(d["topCompPeople"])} biographies'
    return stat_tiles([
        {'k': 'Uganda topics', 'v': d['ccc'],
         'd': 'with an article in at least one language'},
        {'k': 'No article anywhere', 'v': d['wdNoArticle'], 'alarm': True,
         'd': f'{esc(d["wdShare"])}% of Uganda\'s Wikidata items'},
        {'k': 'Largest edition', 'raw': True,
         'v': f'{esc(top["code"])} &middot; {fmt(top["n"])}',
         'd': f'{detail} &middot; <a href="{esc(d["hrefs"]["edition"])}">'
              f'see all {fmt(top["n"])}</a>'},
        {'k': 'Luganda Wikipedia', 'v': d['lgCount'],
         'd': f'{esc(d["lgShare"])}% of that entire {fmt(d["lgArticles"])}'
              f'-article edition is Uganda content'},
    ])


def _local_language_sub(d):
    langs = '; '.join(
        (f'<strong>{esc(lang["names"])}</strong>' if lang.get('strong')
         else esc(lang['names'])) + esc(lang['tail'])
        for lang in d['languages'])
    return ('Luganda Wikipedia is the most Uganda-focused edition in the '
            f'world, and it is still missing {fmt(d["missingLgCount"])} of '
            f'the {fmt(d["ccc"])} topics. It is also Uganda\'s only live '
            f'Wikipedia, but not for much longer: {langs}.')


def _women_section(d, w):
    """The 'Ugandan women, field by field' block, when the data is there."""
    football = d.get('football')
    ahead = ', and in football it is ahead' if football and football.get('ahead') else ''
    football_text = ''
    if football:
        football_text = (f'Luganda carries {fmt(football["inLuganda"])} '
                         f'Ugandan women footballers to English\'s '
                         f'{fmt(football["inEnglish"])}, and ')
    sizes_text = ''
    if d.get('lgSizes'):
        s = d['lgSizes']
        sizes_text = (f'These are not placeholder stubs: across all '
                      f'{fmt(s["measured"])} Luganda women\'s '
                      f'biographies the median length is '
                      f'{fmt(s["medianBytes"])} bytes, and only '
                      f'{esc(s["pctStubs"])}% fall under 2&nbsp;KB against '
                      f'{esc(d["stubRateLg"])}% for Luganda\'s Uganda '
                      f'articles overall. ')

    return join([
        section_heading(
            'Ugandan women, field by field',
            f'Wikidata knows {fmt(w["women"])} Ugandan women. '
            f'{fmt(w["inEnglish"])} have an English article and '
            f'{fmt(w["inLuganda"])} have a Luganda one, near parity. The '
            f'translation backlog is only {fmt(w["enNotLg"])} people. The '
            f'real gap is that {fmt(w["noArticle"])} of them '
            f'({esc(w["noArticleShare"])}%) have no article in any language '
            f'at all.'),

        stat_tiles([
            {'k': 'Ugandan women in Wikidata', 'v': w['women'],
             'd': 'by citizenship'},
            {'k': 'To translate into Luganda', 'v': w['enNotLg'],
             'd': 'English article exists, Luganda does not'},
            {'k': 'To write from scratch', 'v': w['noArticle'], 'alarm': True,
             'd': 'no article in any language'},
            {'k': 'Luganda vs English', 'raw': True,
             'v': f'{fmt(w["inLuganda"])} / {fmt(w["inEnglish"])}',
             'd': f'Luganda is at {esc(w["lgVsEn"])}% of English coverage'},
        ]),

        callout(
            '<strong>For Ugandan women, Luganda Wikipedia has essentially '
            f'caught up with English{ahead}.</strong> {football_text}'
            f'{fmt(d["womenLgOnly"])} Ugandan women have a Luganda article '
            f'and no English one at all. {sizes_text}The pattern is '
            'consistent with a deliberate editing campaign rather than '
            'incidental growth, though this analysis measures the outcome and '
            'not the cause.'),

        _chart(d, 'womenFields', 'Ugandan women by field',
               subtitle='For each field: how many have an English article, a '
                        'Luganda article, and how many have no article '
                        'anywhere. The third bar is the backlog.',
               note='Each woman is counted in one primary field, chosen by '
                    'priority: a specific sport wins over a general role, '
                    'since "politician" is often one of several '
                    'hats a public figure wears. Full occupation lists are '
                    'kept in the CSV exports.'),

        card('Translate into Luganda',
             _translate_table(d['womenTranslate']),
             subtitle=f'All {fmt(w["enNotLg"])} Ugandan women with an English '
                      f'article and no Luganda one, most-read first. This is '
                      f'the entire backlog, not a sample of it.'),

        card('Write from scratch',
             _create_table(d['womenCreate']),
             subtitle=f'Top 25 of {fmt(w["noArticle"])} Ugandan women with no '
                      f'article in any language, ranked by how much Wikidata '
                      f'already records about them: the better documented she '
                      f'is, the easier she is to source.'),
    ])


def _peers(d):
    return join([
        _chart(d, 'peers', 'Uganda next to comparable countries',
               subtitle='Wikidata items about each country holding an article '
                        'in at least one language. Uganda is highlighted.',
               note='A country with a larger diaspora, an older Wikipedia '
                    'community or more aggressive bot imports scores higher '
                    'for reasons unrelated to how well it is actually '
                    'described. Read as an order of magnitude, not a league '
                    'table.'),
        _chart(d, 'peerWomen',
               'Share of women among biographies, by country',
               subtitle='The same peer set measured on gender balance rather '
                        'than volume.'),
    ])


def render(d):
    w = d.get('allWomen')
    top = d['topEdition']
    top_people = ('almost none' if d['topCompPeople'] is None
                  else fmt(d['topCompPeople']))

    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),

        section_heading('The headline'),
        _headline_tiles(d),

        section_heading(
            'The finding',
            'The same corpus looks completely different depending on which '
            'edition you read it in. Cebuano and Swahili hold thousands of '
            'Ugandan streams, hills and sub-counties generated in bulk by '
            'bots. Luganda holds Ugandan people, written by people.'),

        _chart(d, 'composition',
               'What each edition’s Uganda content is made of',
               subtitle='Articles grouped by what the topic <em>is</em>. '
                        'Editions with at least 200 Uganda articles, plus '
                        'English, Luganda and Swahili.',
               note='&ldquo;Places &amp; nature&rdquo; covers settlements, '
                    'administrative units and physical geography; '
                    '&ldquo;everything else&rdquo; is institutions, '
                    'organisations, works and topics. Buckets are matched on '
                    'Wikidata type labels, so a handful of items land in '
                    '&ldquo;everything else&rdquo; simply for having an '
                    'unusual type. Article length says the same thing: '
                    f'{esc(d["stubRateLg"])}% of Luganda&rsquo;s Uganda '
                    'articles are under 2&nbsp;KB, against '
                    f'{esc(d["stubRateSw"])}% of Swahili&rsquo;s, the '
                    'signature of writing versus generation.'),

        callout(
            f'<strong>{esc(top["code"])}wiki holds more Uganda articles than '
            f'English does, and {top_people} of them are about a '
            'Ugandan.</strong> Its Uganda corpus is bot-generated physical '
            f'geography. Luganda Wikipedia, with {fmt(d["lgCount"])} Uganda '
            f'articles and {esc(d["editorsPhrase"])}, is '
            f'{esc(d["lgCompShare"])}% biographies. Article counts alone '
            'cannot tell these two situations apart, which is why counting '
            'articles is not the same as measuring coverage.'),

        _chart(d, 'coverage', 'Uganda articles per Wikipedia edition',
               subtitle=f'Top 20 of {fmt(d["editions"])} editions carrying '
                        'any Uganda content. Editions relevant to Uganda are '
                        'highlighted; <code>(bot)</code> marks those whose '
                        'Uganda content is largely machine-generated.',
               note='Rank here reflects bot policy as much as editorial '
                    'interest. An edition that ran a geography-import bot '
                    'outranks one with an active human community writing '
                    'about the country.'),

        _chart(d, 'spread', 'How far a Uganda topic travels',
               subtitle=f'{esc(d["onlyOneShare"])}% of the corpus exists in '
                        'exactly one edition. A topic in one edition only has '
                        'no translation path and no second reader.'),

        section_heading('The local-language gap', _local_language_sub(d)),

        stat_tiles([
            {'k': 'Missing from Luganda', 'v': d['missingLgCount'],
             'alarm': True, 'd': 'Uganda topics with no Luganda article'},
            {'k': 'Missing from Swahili', 'v': d['missingSwCount'],
             'd': 'Uganda topics with no Swahili article'},
            {'k': 'Luganda stubs', 'v': d['stubLg']['stubs'],
             'd': f'of {fmt(d["stubLg"]["total"])} Uganda articles are under '
                  f'2&nbsp;KB ({esc(d["stubLg"]["rate"])}%)'},
            {'k': 'Ugandan sub-territories', 'raw': True,
             'v': f'{fmt(d["adminLg"])} / {fmt(d["adminTotal"])}',
             'd': f'first-level units in Luganda ({fmt(d["adminEn"])} in '
                  f'English)'},
        ]),

        card('What Luganda Wikipedia should write next',
             _worklist(d['worklists']['lg']),
             subtitle='Top 30 by priority: the mean of two percentile ranks '
                      '(how many editions already carry the topic, and '
                      'English Wikipedia pageviews over the trailing '
                      f'{esc(d["pageviewMonths"])} months). Drawn from the '
                      f'{fmt(d["coreEligible"])} topics with a structural '
                      f'link to Uganda, not the full {fmt(d["ccc"])}.'),

        card('What Swahili Wikipedia should write next',
             _worklist(d['worklists']['sw']),
             subtitle='Same ranking, restricted to Uganda topics with no '
                      'Swahili article.'),

        section_heading(
            'Who the corpus is about',
            f'Of {fmt(d["bios"])} Ugandan biographies, '
            f'{esc(d["womenShare"])}% are women, roughly double '
            "Wikipedia's long-standing global figure of about 20%. This is "
            'the one dimension where Uganda\'s coverage is ahead rather '
            'than behind. Women who held public office are broken out '
            f'separately, with their article status, on the '
            f'<a href="{esc(d["hrefs"]["offices"])}">women in office</a> '
            'page.'),

        _chart(d, 'gender', 'Ugandan biographies by gender',
               subtitle='Men and women with a Ugandan connection, per '
                        'edition. Both counts are direct-labelled; shares are '
                        'in the table view.',
               note='Read with one caveat: Uganda’s biographies are '
                    'heavily contemporary (living politicians, athletes and '
                    'activists), and recent biographies are better balanced '
                    'everywhere on Wikipedia. Some of this lead is a recency '
                    'effect rather than Uganda-specific editorial success. It '
                    'is still a genuinely better ratio than the '
                    'encyclopedia-wide figure.'),
    ]

    if w:
        parts.append(_women_section(d, w))
    if d.get('hasPeers'):
        parts.append(_peers(d))

    parts += [
        section_heading(
            'Method',
            'Seven independent strategies propose items for the corpus; the '
            'number that agree on an item is a confidence signal, the role '
            '<code>num_retrieval_strategies</code> plays in the Diversity '
            'Observatory.'),

        _chart(d, 'strategies', 'Items proposed per retrieval strategy',
               subtitle='Strategies overlap heavily, so the corpus is their '
                        'union, not their sum.'),

        _chart(d, 'wdTypes', 'The structured-data mass, by item type',
               subtitle='Uganda items with no article in any language, beside '
                        'those that have one. These are excluded from the '
                        'corpus above.',
               note='Treating these as a translation backlog would put '
                    'roughly 15,000 primary schools at the top of every '
                    'worklist. Uganda is well described as a database and '
                    'thinly described as an encyclopedia; that is a '
                    'data-quality finding, not a writing task.'),

        page_footer([
            '<strong>How this was built.</strong> The corpus is Wikidata '
            'items about Uganda holding at least one Wikipedia sitelink, '
            'gathered by seven strategies over the Wikidata Query Service, '
            'with article sizes from the MediaWiki API and pageviews from the '
            'Wikimedia REST API.',

            f'<strong>Worklist eligibility.</strong> The corpus of '
            f'{fmt(d["ccc"])} is built for recall; the worklists are built '
            f'for precision. Only the {fmt(d["coreEligible"])} topics with a '
            '<em>structural</em> Wikidata link to Uganda (its country, a '
            'location inside it, Ugandan citizenship, or birth or death '
            'there) are eligible. The weaker signals earn their place in the '
            'corpus but not on a worklist: a cross-border ethnicity pulls in '
            'Kenyan athletes, and an &ldquo;&hellip; in Uganda&rdquo; '
            'redirect pulled in Elizabeth II. Places reached by country must '
            'also be in Uganda <em>and only</em> Uganda, since the Nile '
            'counts Uganda among its countries and was lending a Ugandan '
            'connection to everyone who ever drowned in it. The cost is real '
            'in the other direction too: a genuinely Ugandan topic known only '
            'by keyword, such as the Entebbe raid, sits in the corpus with '
            '<code>is_core=0</code> and off the worklists. Filter '
            '<code>ug_ccc_full_corpus.csv</code> on that column to choose '
            'your own balance.',

            '<strong>Other limits.</strong> Recall is a floor, not an exact '
            'count. Unlike the Diversity Observatory, this pipeline has no '
            'trained classifier, so culturally Ugandan topics with no '
            'Wikidata link to Uganda are under-counted. Pageviews are fetched '
            f'for the top {fmt(d["pageviewTopN"])} topics by edition count, '
            'so demand ranking is reliable at the head of the worklists and '
            'thin in the tail. The bot/human distinction in the coverage '
            'chart is a per-edition judgement, not a per-article test. The '
            'keyword search returns a slightly different set between runs, so '
            'corpus totals move by a few dozen items cycle to cycle.',

            '<strong>Reproduce.</strong> <code>python '
            'src_data/run_all.py</code>, then <code>python '
            'src_viz/export_data.py</code> and <code>python '
            'src_viz/build_pages.py</code>. Stages checkpoint per month, so a '
            'new cycle refreshes everything. Full corpus and every table are '
            'in <code>data/*.csv</code>.',

            '<strong>What to do about it.</strong> This page is the evidence. '
            'The recommendations that follow from it (prioritised, with a '
            '90-day sequence and a baseline to measure against) are on the '
            f'<a href="{esc(d["hrefs"]["plan"])}">action plan</a>.',

            f'Modelled on the {WDO_LINK} by Marc Miquel and David Laniado. '
            'Source data from Wikidata (CC0) and Wikipedia (CC BY-SA).',
        ]),
        '</div>',
    ]
    return join(parts)
