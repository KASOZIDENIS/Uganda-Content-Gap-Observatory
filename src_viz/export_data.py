# -*- coding: utf-8 -*-
"""Export one JSON view model per page for build_pages.py to render.

The split of responsibility: this module owns the database and every number,
build_pages.py owns the markup. So all the counting, percentage work and
sorting happens here, and the renderers are handed values that are ready to
print. Nothing is recomputed on the other side of the boundary.

Each page's SQL lives in its data_*.py module, whose load() functions are
reused here rather than copied.

Written to data/ui/<page>.json. The pages themselves never read these files:
they are opened from disk, where fetch() of a sibling file is blocked as a
cross-origin request, so build_pages.py resolves every value into the markup
at build time instead.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config                    # noqa: E402
import data_dashboard           # noqa: E402
import tokens                   # noqa: E402
import dashboard_view            # noqa: E402
import data_edition        # noqa: E402
import data_offices        # noqa: E402
import data_undocumented   # noqa: E402
import data_topics         # noqa: E402
import data_osm            # noqa: E402
import data_registers      # noqa: E402

OUT_DIR = os.path.join(config.PROJECT_PATH, 'data', 'ui')


def nav(current):
    """The tab bar, which every page carries."""
    return {
        'current': current,
        'pages': [{'key': key, 'label': label, 'href': href}
                  for key, label, href in config.PAGES],
    }


def share(part, whole, digits=0):
    """A percentage as a printable string, the way the pages show it."""
    value = 0.0 if not whole else 100.0 * part / whole
    return f'{value:.{digits}f}'


# What differs between the women's and men's pages: everything else about
# them is the same code over different rows of the same table.
COHORT_COPY = {
    'women': {
        'page': 'undocumented',
        'title': 'Undocumented Ugandan Women in Office',
        'noun': 'women',
        'heading': 'Women running Ugandan institutions who are not on '
                   'Wikimedia at all',
        'lede': 'hold or held a senior position in Ugandan government, state '
                'enterprise, telecom or business',
        'sectors': 'government, state enterprise, telecom and business',
        'calloutTail': 'A permanent secretary runs a ministry. The Head of '
                       'Public Service runs the civil service.',
    },
    'men': {
        'page': 'undocumented_men',
        'title': 'Undocumented Ugandan Men in Office',
        'noun': 'men',
        'heading': 'Men running Ugandan institutions who are not on '
                   'Wikimedia at all',
        'lede': 'command a division, run a police directorate, sit on the '
                'bench, lead a faith or a media house, or run a state '
                'enterprise',
        'sectors': 'the armed forces, the police, the bench, faith '
                   'leadership, media, sport and the public service',
        'calloutTail': 'A division commander runs a third of the army. An '
                       'Inspector General runs the police. An archbishop or a '
                       'mufti speaks for millions.',
    },
}


def _gap_reading(d):
    """The standfirst over the two breakdown tables.

    Read off the numbers rather than asserted, because which axis explains the
    gap differs between the rosters. Categories smaller than five are left out
    of the comparison: a sector with one name in it can read 0% or 100% and
    say nothing either way.
    """
    lead = 'By sector, then by how senior the office is. '
    parts = []

    swept = [r for r in d['by_sector']
             if r['total'] >= 5 and r['absent'] == r['total']]
    if swept:
        named = ', '.join(f'{r["total"]} under {r["label"]}' for r in swept)
        parts.append(
            f'Every one of the {named} is absent, which is the sharpest '
            f'reading on this page.')

    ranks = {r['rank']: r for r in d['by_rank'] if r['total'] >= 5}
    chief, executive = ranks.get('chief'), ranks.get('executive')
    if chief and executive:
        chief_share = share(chief['absent'], chief['total'])
        exec_share = share(executive['absent'], executive['total'])
        if float(exec_share) > float(chief_share):
            parts.append(
                f'Coverage also thins a rung down: {chief_share}% of the '
                f'people who head an institution are missing, against '
                f'{exec_share}% of the executives and officers who run it '
                f'for them.')

    if not parts:
        parts.append(
            'Neither axis separates them cleanly in this roster, so the gap '
            'is spread rather than concentrated.')
    return lead + ' '.join(parts)


# --------------------------------------------------------------- undocumented
def undocumented_view(conn, cohort='women'):
    d = data_undocumented.load(conn, cohort)
    module = data_undocumented

    people = [{
        'key': f"{p['name']}|{p['organisation']}|{p['office']}",
        'name': p['name'],
        'office': p['office'],
        'organisation': p['organisation'],
        'sector': p['sector'],
        'sectorLabel': module.SECTOR_LABELS.get(p['sector'], p['sector']),
        'rank': p['rank'],
        'rankLabel': module.RANK_LABELS.get(p['rank'], p['rank']),
        'status': p['status'],
        'statusLabel': module.STATUS_LABELS[p['status']],
        'qid': p['qid'] or '',
        'enTitle': p['en_title'] or '',
        'lgTitle': p['lg_title'] or '',
        'sourceUrl': p['source_url'] or '',
    } for p in d['people']]

    status_counts = {}
    for p in d['people']:
        status_counts[p['status']] = status_counts.get(p['status'], 0) + 1

    copy = COHORT_COPY[cohort]
    return {
        'nav': nav(copy['page']),
        'cycle': config.cycle_year_month(),
        'title': copy['title'],
        'sheet': 'undocumented.css',
        'cohort': cohort,
        'noun': copy['noun'],
        'heading': copy['heading'],
        'lede': copy['lede'],
        'sectors': copy['sectors'],
        'rosterFile': config.roster_file(cohort),
        'calloutTail': copy['calloutTail'],
        'people': people,
        'total': d['total'],
        'nAbsent': d['n_absent'],
        'nWikidataOnly': d['n_wikidata_only'],
        'nPossible': d['n_possible'],
        'nDocumented': d['n_documented'],
        'organisations': d['organisations'],
        'absentShare': share(d['n_absent'], d['total']),
        'topAbsent': [{'name': p['name'], 'office': p['office'],
                       'organisation': p['organisation']}
                      for p in d['top_absent']],
        'bySector': [{
            'key': r['sector'], 'label': r['label'], 'total': r['total'],
            'absent': r['absent'], 'share': share(r['absent'], r['total']),
        } for r in d['by_sector']],
        'byRank': [{
            'key': r['rank'], 'label': r['label'], 'total': r['total'],
            'absent': r['absent'], 'share': share(r['absent'], r['total']),
        } for r in d['by_rank']],
        'statusOrder': list(module.STATUS_ORDER),
        'statusLabels': dict(module.STATUS_LABELS),
        'statusCounts': status_counts,
        'gapReading': _gap_reading(d),
    }


# --------------------------------------------------------------------- offices
def offices_view(conn):
    d = data_offices.load(conn)
    module = data_offices

    women = [{
        'key': w['qitem'],
        'qitem': w['qitem'],
        'label': w['label'] or w['qitem'],
        'description': w['description'] or '',
        'sitelinks': w['sitelinks'],
        'statements': w['statements'],
        'enTitle': w['en_title'] or '',
        'lgTitle': w['lg_title'] or '',
        'citizen': w['citizen'],
        'tier': w['tier'],
        'tierLabel': config.TIER_LABELS[w['tier']],
        'status': w['status'],
        'statusLabel': module.STATUS_LABELS[w['status']],
        'positions': '; '.join(w['positions']) or 'not recorded',
        # The three groups the page leads with: translate is a subset of
        # having an article, so the grouping is derived, not a status.
        'group': ('none' if w['status'] == 'none'
                  else 'translate' if w['status'] == 'translate' else 'has'),
    } for w in d['women']]

    tiers = [{
        'key': t['tier'], 'label': t['label'], 'holders': t['holders'],
        'withArticle': t['with_article'], 'none': t['none'],
        'covered': round(t['covered'], 1),
        'coveredText': f"{t['covered']:.0f}",
    } for t in d['tiers']]
    best = max(tiers, key=lambda t: t['covered']) if tiers else None
    worst = min(tiers, key=lambda t: t['covered']) if tiers else None

    group_counts = {'none': d['n_none'], 'translate': d['n_translate'],
                    'has': d['n_with']}

    return {
        'nav': nav('offices'),
        'cycle': config.cycle_year_month(),
        'title': 'Ugandan Women in Public Office',
        'sheet': 'offices.css',
        'women': women,
        'total': len(d['women']),
        'nOffice': d['n_office'],
        'nWith': d['n_with'],
        'nNone': d['n_none'],
        'nTranslate': d['n_translate'],
        'nBoth': d['n_both'],
        'nOtherRole': d['n_other_role'],
        'positionsSeen': d['positions_seen'],
        'otherTierLabel': config.TIER_LABELS['other'],
        'noneShare': share(d['n_none'], d['n_office']),
        'tiers': tiers,
        'best': best,
        'worst': worst,
        # Two different counts, for two different jobs. 'groups' is the
        # analysis: how the 493 public-office holders split, where the
        # translation group is a subset of those who have an article.
        # 'groupFilters' is what the filter chips promise, counted over every
        # row the table actually holds, which includes the women whose only
        # recorded position is not a public office.
        'groups': [{'key': key, 'label': label, 'work': work,
                    'count': group_counts[key],
                    'share': share(group_counts[key], d['n_office'])}
                   for key, label, work in module.GROUPS],
        'groupFilters': [
            {'key': key, 'label': label,
             'count': sum(1 for w in women if w['group'] == key)}
            for key, label, _work in module.GROUPS],
        'worstOffices': [{
            'label': position_label, 'holders': holders,
            'noArticle': no_article,
        } for position_label, _tier, holders, _with, no_article in d['worst']],
        'nMissingP27': len(d['missing_p27']),
        'nForeign': len(d['foreign']),
    }


# ---------------------------------------------------------------------- topics
def topics_view(conn):
    d = data_topics.load(conn)

    def topic(t):
        return {
            'key': t['qitem'],
            'qitem': t['qitem'],
            'title': t['title'],
            'area': t.get('area') or t['areas'][0],
            'areas': ', '.join(t['areas']),
            'theirViews': t['theirViews'],
            'ourViews': t['ourViews'],
            'editions': t['editions'],
            'enTitle': t['enTitle'],
            'inLuganda': t['inLuganda'],
            'lgStub': t['lgStub'],
            'core': t['core'],
        }

    areas = [{
        'key': a['area'],
        'label': a['area'],
        'topics': a['topics'],
        'coreTopics': a['coreTopics'],
        'inLuganda': a['inLuganda'],
        'missing': a['missing'],
        'stubs': a['stubs'],
        'unserved': a['unserved'],
        'reportedViews': a['reportedViews'],
        'structuralViews': a['structuralViews'],
        'offTopicViews': a['offTopicViews'],
        'covered': round(a['covered'], 1),
        'coveredText': f"{a['covered']:.0f}",
        'offTopicText': f"{a['offTopicShare']:.0f}",
        'unservedText': f"{a['unservedShare']:.0f}",
    } for a in d['areas']]

    return {
        'nav': nav('topics'),
        'cycle': config.cycle_year_month(),
        'title': 'Uganda Topic Areas',
        'sheet': 'topics.css',
        'nTopics': d['nTopics'],
        'nCore': d['nCore'],
        'nAreas': d['nAreas'],
        'nMemberships': d['nMemberships'],
        'nInLuganda': d['nInLuganda'],
        'nMissing': d['nMissing'],
        'nStubs': d['nStubs'],
        'nNoViews': d['nNoViews'],
        'nOurViews': d['nOurViews'],
        'reportedViews': d['reportedViews'],
        'structuralViews': d['structuralViews'],
        'offTopicViews': d['offTopicViews'],
        'unservedViews': d['unservedViews'],
        'structuralShare': share(d['structuralViews'], d['reportedViews']),
        'offTopicShare': share(d['offTopicViews'], d['reportedViews']),
        'unservedShare': share(d['unservedViews'], d['structuralViews']),
        'coveredShare': share(d['nInLuganda'], d['nCore']),
        'areas': areas,
        'worklist': [topic(t) for t in d['worklist']],
        'nWorklistRows': d['nWorklistRows'],
        'nWorklistTopics': d['nWorklistTopics'],
        'recallMisses': [topic(t) for t in d['recallMisses']],
        'overCollected': [topic(t) for t in d['overCollected'][:15]],
        'nOverCollected': d['nOverCollected'],
        'verified': d['verified'],
        'pageviewMonths': config.PAGEVIEW_MONTHS,
        'hrefs': {'plan': config.page_href('plan'),
                  'dashboard': config.page_href('dashboard')},
    }


# -------------------------------------------------------------------------- osm
def osm_view(conn):
    d = data_osm.load(conn)
    return {
        'nav': nav('osm'),
        'cycle': config.cycle_year_month(),
        'title': 'Uganda on OpenStreetMap',
        'sheet': 'osm.css',
        'classes': d['classes'],
        'total': d['total'],
        'untagged': d['untagged'],
        'tagged': d['tagged'],
        'taggedShare': share(d['tagged'], d['total'], 1),
        'nClasses': d['nClasses'],
        'noArticle': d['noArticle'],
        'itemNoArticle': d['itemNoArticle'],
        'undescribed': d['undescribed'],
        'described': d['described'],
        'matched': d['matched'],
        'half': d['half'],
        'nHalf': d['nHalf'],
        'worklist': d['worklist'],
        'omitted': d['omitted'],
        'sampleSize': d['sampleSize'],
        'stateLabels': d['stateLabels'],
        'verdictLabels': d['verdictLabels'],
    }


# -------------------------------------------------------------------- registers
def registers_view(conn):
    d = data_registers.load(conn)
    return {
        'nav': nav('registers'),
        'cycle': config.cycle_year_month(),
        'title': 'Uganda Official Registers',
        'sheet': 'registers.css',
        'kinds': d['kinds'],
        'total': d['total'],
        'described': d['described'],
        'missing': d['missing'],
        'rows': d['rows'],
        'omitted': d['omitted'],
        'sampleSize': d['sampleSize'],
        'nMps': d['nMps'],
        'mpsMissing': d['mpsMissing'],
        'kindLabels': d['kindLabels'],
        'sourceLabels': d['sourceLabels'],
    }


# ------------------------------------------------------------------ action plan
def plan_view(conn):
    """The action plan is a frozen baseline, so it needs no figures exported.

    Its numbers are fixed on purpose: a plan needs a starting line that does
    not move under it. Only the shared nav travels.
    """
    return {
        'nav': nav('plan'),
        'cycle': config.cycle_year_month(),
        'title': 'Uganda Gap Action Plan',
        'sheet': 'plan.css',
        'components': False,   # the plan carries its own full sheet
    }


# --------------------------------------------------------------------- edition
def edition_view(conn):
    d = data_edition.load(conn)
    module = data_edition
    total = d['total']
    counts = d['counts']
    people = counts['people']

    items = [{
        'key': it['qitem'],
        'qitem': it['qitem'],
        'title': it['title'],
        'label': it['label'] or '',
        'types': ', '.join(it['types'][:3]) or 'no type recorded',
        'sitelinks': it['sitelinks'],
        'bucket': it['bucket'],
        'bucketLabel': config.BUCKET_LABELS[it['bucket']],
        'core': it['core'],
    } for it in d['items']]

    # The bar chart shows the commonest primary types; the tail is summarised
    # in a note rather than drawn, so the limit lives here with the counts.
    limit = 14
    bars = d['primary'][:limit]
    shown = sum(n for _name, n in bars)

    return {
        'nav': nav('edition'),
        'cycle': config.cycle_year_month(),
        'title': f"{d['languagecode']}wiki Uganda Articles",
        'sheet': 'edition.css',
        'languagecode': d['languagecode'],
        'items': items,
        'total': total,
        'people': people,
        'peopleWord': 'is a biography' if people == 1 else 'are biographies',
        'peopleShare': share(people, total, 2),
        'places': counts['places'],
        'placesShare': share(counts['places'], total, 1),
        'shareOfEdition': (
            f"{share(total, d['edition_articles'], 1)}% of the edition"
            if d['edition_articles'] else 'share of edition unknown'),
        'topType': d['primary'][0][0] if d['primary'] else '',
        'topTypeCount': d['primary'][0][1] if d['primary'] else 0,
        'weakOnly': d['weak_only'],
        'unlabelled': d['unlabelled'],
        'dashboardHref': config.page_href('dashboard'),
        'typeBars': [{'label': name, 'value': n} for name, n in bars],
        'typeTail': {
            'kinds': len(bars),
            'shown': shown,
            'share': share(shown, total),
            'rest': total - shown,
            'restKinds': len(d['primary']) - limit,
        } if len(d['primary']) > limit else None,
        'buckets': [{
            'key': b, 'label': config.BUCKET_LABELS[b], 'count': counts[b],
        } for b in module.BUCKET_ORDER if counts[b]],
    }


PAGES = {
    'dashboard': dashboard_view.view,
    'registers': registers_view,
    'osm': osm_view,
    'undocumented_men': lambda conn: undocumented_view(conn, 'men'),
    'topics': topics_view,
    'plan': plan_view,
    'edition': edition_view,
    'offices': offices_view,
    'undocumented': undocumented_view,
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_FILE)

    # One palette, two consumers: this sheet and the chart fills, which are
    # CSS custom properties rather than hex values baked into the markup.
    tokens_path = tokens.TOKENS_FILE
    os.makedirs(os.path.dirname(tokens_path), exist_ok=True)
    with open(tokens_path, 'w', encoding='utf-8') as handle:
        handle.write(tokens.tokens_css())
    print(f'wrote {tokens_path}')

    for name, view in PAGES.items():
        payload = view(conn)
        path = os.path.join(OUT_DIR, name + '.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
        print(f'wrote {path} ({os.path.getsize(path) // 1024} KB)')

    conn.close()


if __name__ == '__main__':
    main()
