# -*- coding: utf-8 -*-
"""Stage 5: day-one starter worklists for Uganda's Incubator Wikipedias.

Two Ugandan languages are past the "no project at all" stage:

  Runyankore (nyn)  approved by the Language Committee, awaiting creation
                    by developers - https://incubator.wikimedia.org/wiki/Wp/nyn
  Acholi (ach)      eligible test wiki with a request pending on Meta
                    https://incubator.wikimedia.org/wiki/Wp/ach

A brand-new Wikipedia's first few hundred articles decide whether it reads as
a real encyclopedia or an empty shell, and a test wiki needs demonstrable
content volume to win approval. Both need a ranked list on day one.

Each list has two halves:

  universal  the Uganda topics every Ugandan Wikipedia should carry, taken
             from the main corpus by priority
  home       topics from the region where the language is actually spoken -
             the content no other edition is motivated to write

Incubator test wikis live at incubator.wikimedia.org/wiki/Wp/<code>/... and
are not Wikidata sitelinks, so existing test-wiki coverage cannot be measured
here. These are proposed lists, not gap measurements.
"""

import pandas as pd

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri, run_sparql

SCRIPT = 'incubator_starter'

INCUBATOR_TARGETS = {
    'nyn': {
        'name': 'Runyankore',
        'status': 'Approved by Language Committee, awaiting creation (T429189)',
        'incubator': 'https://incubator.wikimedia.org/wiki/Wp/nyn',
        'language_qid': 'Q35772',
        'home_region': 'Ankole sub-region',
        'districts': ['Mbarara District', 'Bushenyi District',
                      'Ntungamo District', 'Kiruhura District',
                      'Ibanda District', 'Isingiro District',
                      'Buhweju District', 'Mitooma District',
                      'Rubirizi District', 'Sheema District',
                      'Kazo District', 'Rwampara District'],
    },
    'ach': {
        'name': 'Acholi',
        'status': 'Eligible test wiki, request pending on Meta-Wiki',
        'incubator': 'https://incubator.wikimedia.org/wiki/Wp/ach',
        'language_qid': 'Q33705',
        'home_region': 'Acholi sub-region',
        'districts': ['Gulu District', 'Kitgum District', 'Pader District',
                      'Amuru District', 'Nwoya District', 'Agago District',
                      'Lamwo District', 'Omoro District'],
    },
}

UNIVERSAL_TOPICS = 150      # Uganda-wide essentials per starter list
HOME_TOPICS = 250           # region-specific topics per starter list


def _resolve_districts(names):
    """District label -> QID, restricted to administrative units in Uganda."""
    values = ' '.join(f'"{n}"@en' for n in names)
    query = f"""
    SELECT ?d ?dLabel WHERE {{
      VALUES ?label {{ {values} }}
      ?d rdfs:label ?label ; wdt:P17 wd:Q1036 .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    try:
        rows = run_sparql(query, timeout=300)
    except Exception as error:                         # noqa: BLE001
        print(f'    district lookup failed ({type(error).__name__})')
        return {}
    return {binding_value(b, 'dLabel'): qid_from_uri(binding_value(b, 'd'))
            for b in rows}


def _home_region_items(district_qids, language_qid):
    """Corpus-eligible items belonging to the language's home region."""
    if not district_qids:
        return set()
    values = ' '.join('wd:' + q for q in district_qids)
    query = f"""
    SELECT DISTINCT ?item WHERE {{
      {{
        VALUES ?district {{ {values} }}
        ?item wdt:P131+ ?district .
      }} UNION {{
        VALUES ?lang {{ wd:{language_qid} }}
        {{ ?item wdt:P407 ?lang }} UNION {{ ?item wdt:P103 ?lang }}
        UNION {{ ?item wdt:P1412 ?lang }} UNION {{ ?item wdt:P2936 ?lang }}
      }}
      ?item wikibase:sitelinks ?sl . FILTER(?sl > 0)
    }}
    """
    try:
        rows = run_sparql(query, timeout=400)
    except Exception as error:                         # noqa: BLE001
        print(f'    home-region lookup failed ({type(error).__name__})')
        return set()
    return {qid_from_uri(binding_value(b, 'item')) for b in rows}


def generate_starter_lists(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'generate_starter_lists', force) as st:
        if st.skip:
            return

        # The main corpus, already gated on a structural link to Uganda by
        # generate_missing_ccc; reuse that gate rather than redefining it.
        corpus = pd.read_sql("""
            SELECT c.qitem, c.label, c.sitelink_count, c.types, c.admin_qid,
                   c.gender_qid, en.title AS en_title,
                   COALESCE(pv.views, 0) AS views
            FROM ccc_items c
            LEFT JOIN sitelinks en
                   ON en.qitem = c.qitem AND en.languagecode = 'en'
            LEFT JOIN pageviews pv ON pv.qitem = c.qitem
            WHERE c.strategies LIKE '%country_wd%'
               OR c.strategies LIKE '%citizenship_wd%'
               OR c.strategies LIKE '%location_wd%'
               OR c.strategies LIKE '%birth_death_wd%'
        """, conn)
        labels = dict(conn.execute('SELECT qitem, label FROM entity_labels'))
        corpus['type_labels'] = corpus.types.fillna('').apply(
            lambda s: ', '.join(labels.get(q, q) for q in s.split('|')[:3] if q))

        importance = corpus.sitelink_count.rank(pct=True)
        demand = corpus.views.rank(pct=True)
        corpus['priority'] = (100 * (importance + demand) / 2).round(1)

        summary = []
        for code, target in INCUBATOR_TARGETS.items():
            print(f'\n  {target["name"]} ({code}) - {target["status"]}')
            districts = _resolve_districts(target['districts'])
            print(f'    resolved {len(districts)}/{len(target["districts"])} districts')

            home_qids = _home_region_items(list(districts.values()),
                                           target['language_qid'])
            print(f'    {len(home_qids)} items tied to the {target["home_region"]}')

            home = corpus[corpus.qitem.isin(home_qids)].copy()
            home['section'] = f'home: {target["home_region"]}'
            home = home.sort_values(
                ['priority', 'sitelink_count'], ascending=False).head(HOME_TOPICS)

            universal = corpus[~corpus.qitem.isin(home_qids)].copy()
            universal['section'] = 'universal: Uganda essentials'
            universal = universal.sort_values(
                ['priority', 'sitelink_count'],
                ascending=False).head(UNIVERSAL_TOPICS)

            out = pd.concat([universal, home], ignore_index=True)
            out['starter_rank'] = range(1, len(out) + 1)
            out = out[['starter_rank', 'section', 'qitem', 'label', 'en_title',
                       'sitelink_count', 'views', 'priority', 'type_labels']]
            _export(out, f'ug_starter_{code}')

            out.to_sql(f'starter_{code}', conn, if_exists='replace', index=False)
            summary.append({
                'languagecode': code,
                'language': target['name'],
                'status': target['status'],
                'incubator_url': target['incubator'],
                'home_region': target['home_region'],
                'districts_resolved': len(districts),
                'home_topics_found': len(home_qids),
                'starter_list_size': len(out),
            })
            print(f'    starter list: {len(out)} topics '
                  f'({len(universal)} universal + {len(home)} home)')

        df = pd.DataFrame(summary)
        _export(df, 'ug_incubator_targets')
        df.to_sql('incubator_targets', conn, if_exists='replace', index=False)
        conn.commit()


def _export(df, name):
    import os
    path = os.path.join(config.DATA_PATH, name + '.csv')
    df.to_csv(path, index=False, encoding='utf-8')
    print(f'    -> {name}.csv ({len(df)} rows)')


def main(force=False):
    conn = ug_utils.connect()
    generate_starter_lists(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
