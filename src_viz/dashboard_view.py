# -*- coding: utf-8 -*-
"""The dashboard's view model.

Kept in its own module because it is much the largest of them: nine charts,
four worklists and a page of prose whose every number is computed here rather
than in the UI. The derivations are the ones the page has always used; what
changed is that they now land in a dict instead of straight into an f-string.

Chart colours are no longer part of the payload. The bars are pre-rendered SVG
filled with var(--s1) and friends, so a theme change is the browser's problem
rather than something JavaScript has to redraw.
"""

import data_dashboard as bd
import config

CCC_NOTE_LIMIT = 44
OCCUPATION_LIMIT = 38
DESCRIPTION_LIMIT = 52


def _pct(part, whole, digits=1):
    """The page's own percentage helper, which returns a number."""
    return round(100.0 * part / whole, digits) if whole else 0


def _table(headers, rows, align_right=()):
    return {'headers': list(headers), 'rows': rows,
            'alignRight': list(align_right)}


def _worklist(rows):
    """Rows for the two 'what to write next' tables."""
    return [{
        'label': r['label'] or r['en_title'] or '',
        'enTitle': r['en_title'] or '',
        'sitelinks': r['sitelink_count'],
        'views': r['views'],
        'priority': str(r['priority']),
        'types': (r['type_labels'] or '')[:CCC_NOTE_LIMIT],
    } for r in rows]


def view(conn):
    d = bd.load(conn)
    ccc = d['ccc_total']
    per = d['per_wiki']
    wd_total = d['wd_no_article'] + d['wd_with_article']
    spread = bd.bucket_spread(d['spread_raw'])

    comp = d['composition']
    comp_top = [r for r in comp if r['total'] >= 200][:10]
    for lc in config.TARGET_WIKIS:
        if not any(r['languagecode'] == lc for r in comp_top):
            extra = next((r for r in comp if r['languagecode'] == lc), None)
            if extra:
                comp_top.append(extra)
    comp_top.sort(key=lambda r: -r['total'])

    top_edition = d['coverage'][0] if d['coverage'] else {'languagecode': '',
                                                          'n': 0}
    top_comp = next((r for r in comp
                     if r['languagecode'] == top_edition['languagecode']), None)
    lg_comp = next((r for r in comp if r['languagecode'] == 'lg'), None)

    admin = d['admin_units']
    admin_en = sum(1 for r in admin if r.get('in_en'))
    admin_lg = sum(1 for r in admin if r.get('in_lg'))
    stub_lg = d['stubs'].get('lg', {})
    stub_sw = d['stubs'].get('sw', {})
    stub_rate_lg = _pct(stub_lg.get('stubs', 0), stub_lg.get('total', 0), 0)
    stub_rate_sw = _pct(stub_sw.get('stubs', 0), stub_sw.get('total', 0), 0)

    lg_stats = d['edition_stats'].get('lg', {})
    lg_articles = lg_stats.get('articles') or 0
    lg_editors = lg_stats.get('active_editors')

    all_women = next((r for r in d['women_fields']
                      if r['field'] == 'ALL FIELDS'), None)
    football = next((r for r in d['women_fields']
                     if r['field'] == 'Football'), None)
    lg_sizes = d['women_lg_sizes']

    # The three-state language situation, phrased the way the page phrases it.
    approved = config.languages_by_status('approved')
    incubating = config.languages_by_status('incubating')
    no_project = config.languages_by_status('none')
    langs = []
    if approved:
        langs.append({'names': ', '.join(approved), 'strong': True,
                      'tail': ' is approved and awaiting creation by developers'})
    if incubating:
        langs.append({'names': ', '.join(incubating), 'strong': True,
                      'tail': ' has an active Incubator test wiki with a request pending'})
    if no_project:
        langs.append({'names': f'{len(no_project)} more '
                               f'({", ".join(no_project)})',
                      'strong': False, 'tail': ' have no project yet'})

    charts = {
        'composition': {
            'rows': [{'label': r['languagecode'],
                      'v': [r['people'], r['places'],
                            r['institutions'] + r['other']]}
                     for r in comp_top],
            'labelW': 74, 'valueW': 150, 'rowH': 38,
            'names': ['People', 'Places & nature', 'Everything else'],
            'aria': "Composition of each edition’s Uganda content",
        },
        'coverage': {
            'rows': [{'label': r['languagecode']
                      + ('  (bot)' if r['languagecode'] in bd.BOT_HEAVY else ''),
                      'v': r['n'],
                      'hi': r['languagecode'] in config.TARGET_WIKIS}
                     for r in d['coverage']],
            'labelW': 90, 'aria': 'Uganda articles per Wikipedia edition',
        },
        'spread': {
            'rows': [{'label': r['label'], 'v': r['n']} for r in spread],
            'labelW': 132, 'ordinal': True,
            'aria': 'Corpus by number of editions',
        },
        'gender': {
            'rows': [{'label': r['wiki'], 'v': [r['men'], r['women']]}
                     for r in d['gender_by_wiki']],
            'labelW': 96, 'valueW': 116, 'rowH': 34,
            'names': ['Men', 'Women'],
            'aria': 'Ugandan biographies by gender',
        },
        'peers': {
            'rows': [{'label': r['country'], 'v': r['items_with_article'],
                      'hi': r['country'] == 'Uganda'} for r in d['peers']],
            'labelW': 108, 'aria': 'Items with an article, by country',
        },
        'peerWomen': {
            'rows': [{'label': r['country'], 'v': r['pct_women'],
                      'hi': r['country'] == 'Uganda'} for r in d['peers']],
            'labelW': 108, 'valueW': 62, 'suffix': '%', 'decimals': 1,
            'aria': 'Share of women among biographies, by country',
        },
        'womenFields': {
            'rows': [{'label': r['field'],
                      'v': [r['in_english'], r['in_luganda'],
                            r['no_article_anywhere']]}
                     for r in d['women_fields'] if r['field'] != 'ALL FIELDS'],
            'labelW': 168, 'valueW': 152, 'rowH': 40,
            'names': ['In English', 'In Luganda', 'No article anywhere'],
            'aria': 'Ugandan women by field and article status',
        },
        'strategies': {
            'rows': [{'label': r['strategy'], 'v': r['n']}
                     for r in d['strategies']],
            'labelW': 136, 'aria': 'Items proposed per retrieval strategy',
        },
        'wdTypes': {
            'rows': [{'label': r['type_label'],
                      'v': [r['no_article'], r['with_article']]}
                     for r in d['wd_types']],
            'labelW': 172, 'valueW': 128, 'rowH': 34,
            'names': ['No article anywhere', 'Has an article'],
            'colors': ['var(--s2)', 'var(--s1)'],
            'aria': 'Uganda items without an article, by type',
        },
    }

    tables = {
        'composition': _table(
            ['Edition', 'People', 'Places & nature', 'Everything else',
             'Total', '% people'],
            [[r['languagecode'] + 'wiki', f"{r['people']:,}",
              f"{r['places']:,}", f"{r['institutions'] + r['other']:,}",
              f"{r['total']:,}", f"{_pct(r['people'], r['total'])}%"]
             for r in comp_top], (1, 2, 3, 4, 5)),
        'coverage': _table(
            ['Edition', 'Uganda articles', '% of corpus'],
            [[r['languagecode'] + 'wiki', f"{r['n']:,}",
              f"{_pct(r['n'], ccc)}%"] for r in d['coverage']], (1, 2)),
        'spread': _table(
            ['Spread', 'Topics', '% of corpus'],
            [[r['label'], f"{r['n']:,}", f"{_pct(r['n'], ccc)}%"]
             for r in spread], (1, 2)),
        'gender': _table(
            ['Scope', 'Men', 'Women', '% women'],
            [[r['wiki'], f"{r['men']:,}", f"{r['women']:,}",
              f"{_pct(r['women'], r['men'] + r['women'])}%"]
             for r in d['gender_by_wiki']], (1, 2, 3)),
        'womenFields': _table(
            ['Field', 'Women', 'In English', 'In Luganda',
             'English but not Luganda', 'No article anywhere', '% in Luganda'],
            [[r['field'], f"{r['women']:,}", f"{r['in_english']:,}",
              f"{r['in_luganda']:,}", f"{r['en_not_lg']:,}",
              f"{r['no_article_anywhere']:,}", f"{r['pct_in_luganda']}%"]
             for r in d['women_fields']], (1, 2, 3, 4, 5, 6)),
        'strategies': _table(
            ['Strategy', 'Items proposed'],
            [[r['strategy'], f"{r['n']:,}"] for r in d['strategies']], (1,)),
        'wdTypes': _table(
            ['Item type', 'No article anywhere', 'Has an article'],
            [[r['type_label'], f"{r['no_article']:,}",
              f"{r['with_article']:,}"] for r in d['wd_types']], (1, 2)),
    }
    if d['peers']:
        tables['peers'] = _table(
            ['Country', 'With an article', 'In English', 'Biographies',
             '% women'],
            [[r['country'], f"{r['items_with_article']:,}",
              f"{r['in_enwiki']:,}", f"{r['biographies']:,}",
              f"{r['pct_women']}%"] for r in d['peers']], (1, 2, 3, 4))
        tables['peerWomen'] = _table(
            ['Country', 'Biographies', 'Women', '% women'],
            [[r['country'], f"{r['biographies']:,}",
              f"{r['women_biographies']:,}", f"{r['pct_women']}%"]
             for r in d['peers']], (1, 2, 3))

    return {
        'nav': {'current': 'dashboard',
                'pages': [{'key': k, 'label': lb, 'href': h}
                          for k, lb, h in config.PAGES]},
        'cycle': config.cycle_year_month(),
        'title': 'Uganda Content Gap',
        'sheet': 'dashboard.css',
        'components': False,   # the dashboard carries its own full sheet

        'ccc': ccc,
        'editions': d['editions'],
        'wdNoArticle': d['wd_no_article'],
        'wdShare': _pct(d['wd_no_article'], wd_total),
        'topEdition': {'code': top_edition['languagecode'],
                       'n': top_edition['n']},
        'topCompPeople': top_comp['people'] if top_comp else None,
        'lgCount': per.get('lg', 0),
        'swCount': per.get('sw', 0),
        'lgArticles': lg_articles,
        'lgShare': _pct(per.get('lg', 0), lg_articles),
        'lgCompShare': _pct(lg_comp['people'], lg_comp['total']) if lg_comp else 0,
        'editorsPhrase': (f'roughly {lg_editors} active editors' if lg_editors
                          else 'a very small editing community'),
        'missingLgCount': ccc - per.get('lg', 0),
        'missingSwCount': ccc - per.get('sw', 0),
        'stubLg': {'stubs': stub_lg.get('stubs', 0),
                   'total': stub_lg.get('total', 0),
                   'rate': f'{stub_rate_lg:.0f}'},
        'stubRateLg': f'{stub_rate_lg:.0f}',
        'stubRateSw': f'{stub_rate_sw:.0f}',
        'adminLg': admin_lg, 'adminEn': admin_en, 'adminTotal': len(admin),
        'languages': langs,
        'coreEligible': d['core_eligible'],
        'onlyOneShare': _pct(d['only_one'], ccc),
        'bios': d['bios'],
        'womenShare': _pct(d['women'], d['bios']),
        'womenLgOnly': d['women_lg_only'],
        'pageviewMonths': config.PAGEVIEW_MONTHS,
        'pageviewTopN': config.PAGEVIEW_TOP_N,
        'hrefs': {
            'edition': config.page_href('edition'),
            'offices': config.page_href('offices'),
            'plan': config.page_href('plan'),
        },

        'charts': charts,
        'tables': tables,
        'worklists': {
            'lg': _worklist(d.get('missing_lg', [])),
            'sw': _worklist(d.get('missing_sw', [])),
        },
        'allWomen': ({
            'women': all_women['women'],
            'inEnglish': all_women['in_english'],
            'inLuganda': all_women['in_luganda'],
            'enNotLg': all_women['en_not_lg'],
            'noArticle': all_women['no_article_anywhere'],
            'noArticleShare': _pct(all_women['no_article_anywhere'],
                                   all_women['women']),
            'lgVsEn': _pct(all_women['in_luganda'], all_women['in_english']),
        } if all_women else None),
        'football': ({'inLuganda': football['in_luganda'],
                      'inEnglish': football['in_english'],
                      'ahead': football['in_luganda'] > football['in_english']}
                     if football else None),
        'lgSizes': ({'measured': lg_sizes.get('measured'),
                     'medianBytes': lg_sizes.get('median_bytes'),
                     'pctStubs': lg_sizes.get('pct_stubs')}
                    if lg_sizes else None),
        'womenTranslate': [{
            'label': r['label'], 'field': r['field'],
            'enTitle': r['en_title'] or '',
            'sitelinks': r['sitelink_count'], 'views': r['views'],
            'occupations': (r['occupation_names'] or '')[:OCCUPATION_LIMIT],
        } for r in d['women_translate']],
        'womenCreate': [{
            'label': r['label'], 'field': r['field'],
            'statements': r['statements'],
            'description': (r['description'] or '')[:DESCRIPTION_LIMIT],
        } for r in d['women_create']],
        'hasPeers': bool(d['peers']),
    }
