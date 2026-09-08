# -*- coding: utf-8 -*-
"""Stage 3: turn the CCC corpus into gap statistics and worklists.

Mirrors WDO's stats_generation.py. Everything here is a set intersection
between the Uganda CCC and some other set: a language edition, a gender, a
district, a topic, a peer country.

Outputs land in both SQLite (for the dashboard) and CSV (for reuse).
"""

import os

import pandas as pd

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri, run_sparql

SCRIPT = 'stats_generation'

MALE, FEMALE = 'Q6581097', 'Q6581072'

# Strategies that assert a *structural* link between the item and Uganda:
# its country, a location inside Uganda, Ugandan citizenship, or birth/death
# there. The remaining strategies (keyword_title, ethnic_group_wd,
# language_wd, part_of_wd) are useful for recall but weak on their own -
# cross-border ethnicities pull in Kenyans, an "... in Uganda" redirect pulls
# in global topics. Worklists are gated on a core strategy so a human doing
# the work is not handed Elizabeth II or a Kenyan marathon runner.
CORE_STRATEGIES = ('country_wd', 'citizenship_wd', 'location_wd',
                   'birth_death_wd')


def _core_clause(alias='c'):
    return ' OR '.join(
        f"{alias}.strategies LIKE '%{name}%'" for name in CORE_STRATEGIES)


def _export(df, name):
    path = os.path.join(config.DATA_PATH, name + '.csv')
    df.to_csv(path, index=False, encoding='utf-8')
    print(f'    -> {name}.csv ({len(df)} rows)')


def _labels(conn):
    return dict(conn.execute('SELECT qitem, label FROM entity_labels'))


# ---------------------------------------------------------------------------

def generate_corpus_overview(conn, force=False):
    """Headline numbers: corpus size, strategy contribution, article-less mass."""
    with ug_utils.stage(conn, SCRIPT, 'generate_corpus_overview', force) as st:
        if st.skip:
            return

        strategies = pd.read_sql("""
            SELECT strategy, COUNT(*) AS items
            FROM strategy_hits GROUP BY strategy ORDER BY items DESC""", conn)
        _export(strategies, 'ug_strategy_contribution')

        confidence = pd.read_sql("""
            SELECT num_strategies, COUNT(*) AS items
            FROM ccc_items GROUP BY num_strategies ORDER BY num_strategies""", conn)
        _export(confidence, 'ug_strategy_confidence')

        wikidata_only = pd.read_sql("""
            SELECT type_label, no_article, with_article
            FROM wikidata_only ORDER BY no_article DESC""", conn)
        _export(wikidata_only, 'ug_wikidata_only_by_type')

        totals = conn.execute(
            'SELECT no_article, with_article FROM wikidata_only_totals').fetchone()
        ccc_total = conn.execute('SELECT COUNT(*) FROM ccc_items').fetchone()[0]

        overview = pd.DataFrame([
            {'metric': 'ccc_items_total', 'value': ccc_total},
            {'metric': 'country_items_with_article', 'value': totals[1]},
            {'metric': 'country_items_without_article', 'value': totals[0]},
        ])
        _export(overview, 'ug_overview')
        print(f'  CCC corpus: {ccc_total} items')


def generate_language_coverage(conn, force=False):
    """How much of the Uganda CCC each Wikipedia language edition carries."""
    with ug_utils.stage(conn, SCRIPT, 'generate_language_coverage', force) as st:
        if st.skip:
            return

        total = conn.execute('SELECT COUNT(*) FROM ccc_items').fetchone()[0]
        coverage = pd.read_sql("""
            SELECT languagecode, COUNT(DISTINCT qitem) AS ccc_articles
            FROM sitelinks GROUP BY languagecode ORDER BY ccc_articles DESC""", conn)
        coverage['pct_of_ccc'] = (100.0 * coverage.ccc_articles / total).round(2)
        coverage['is_ugandan_language'] = coverage.languagecode.isin(config.LOCAL_WIKIS)
        _export(coverage, 'ug_coverage_by_language')

        # Spread: in how many editions does a given Uganda topic appear?
        spread = pd.read_sql("""
            SELECT sitelink_count, COUNT(*) AS items
            FROM ccc_items GROUP BY sitelink_count ORDER BY sitelink_count""", conn)
        # Five buckets, not six: the validated single-hue ordinal ramp only
        # supports five visually separable steps in light mode.
        buckets = [(1, 1, 'in 1 wiki only'), (2, 5, 'in 2-5'),
                   (6, 10, 'in 6-10'), (11, 25, 'in 11-25'),
                   (26, 100000, 'in 26+')]
        rows = []
        for low, high, label in buckets:
            # spread['items'], not spread.items - the latter is a DataFrame method.
            n = int(spread[(spread.sitelink_count >= low) &
                           (spread.sitelink_count <= high)]['items'].sum())
            rows.append({'bucket': label, 'items': n,
                         'pct': round(100.0 * n / total, 2) if total else 0})
        _export(pd.DataFrame(rows), 'ug_spread_buckets')

        for languagecode in config.TARGET_WIKIS:
            row = coverage[coverage.languagecode == languagecode]
            if not row.empty:
                r = row.iloc[0]
                print(f'  {languagecode}wiki: {r.ccc_articles} CCC articles '
                      f'({r.pct_of_ccc}% of corpus)')


def generate_missing_ccc(conn, force=False):
    """Worklists: Uganda topics absent from each local-language Wikipedia.

    Ranked by a blend of editorial importance (how many editions already
    have it) and reader demand (trailing pageviews on the reference wiki),
    combined as the mean of the two percentile ranks so neither signal's
    scale dominates.
    """
    with ug_utils.stage(conn, SCRIPT, 'generate_missing_ccc', force) as st:
        if st.skip:
            return

        base = pd.read_sql(f"""
            SELECT c.qitem, c.label, c.sitelink_count, c.types,
                   c.gender_qid, c.admin_qid, c.num_strategies, c.strategies,
                   en.title AS en_title,
                   COALESCE(pv.views, 0) AS views
            FROM ccc_items c
            LEFT JOIN sitelinks en
                   ON en.qitem = c.qitem AND en.languagecode = ?
            LEFT JOIN pageviews pv
                   ON pv.qitem = c.qitem
            WHERE ({_core_clause('c')})
              AND (c.label IS NOT NULL OR en.title IS NOT NULL)
        """, conn, params=(config.REFERENCE_WIKI,))
        print(f'  {len(base)} items pass the core-strategy gate '
              f'(of {conn.execute("SELECT COUNT(*) FROM ccc_items").fetchone()[0]})')

        labels = _labels(conn)
        base['type_labels'] = base.types.fillna('').apply(
            lambda s: ', '.join(labels.get(q, q) for q in s.split('|')[:3] if q))

        for languagecode in config.LOCAL_WIKIS:
            present = {r[0] for r in conn.execute(
                'SELECT qitem FROM sitelinks WHERE languagecode=?', (languagecode,))}
            missing = base[~base.qitem.isin(present)].copy()

            # Only topics that exist somewhere to translate from are actionable.
            missing = missing[missing.sitelink_count > 0]

            importance = missing.sitelink_count.rank(pct=True)
            demand = missing.views.rank(pct=True)
            missing['priority'] = (100 * (importance + demand) / 2).round(1)
            missing = missing.sort_values(
                ['priority', 'sitelink_count'], ascending=False)

            out = missing[['qitem', 'label', 'en_title', 'sitelink_count',
                           'views', 'priority', 'type_labels',
                           'num_strategies', 'strategies']]
            _export(out, f'ug_missing_{languagecode}')
            print(f'  missing from {languagecode}wiki: {len(out)} topics')

            out.head(300).to_sql(f'missing_{languagecode}', conn,
                                 if_exists='replace', index=False)
        conn.commit()


def generate_incomplete_ccc(conn, force=False):
    """Topics that exist locally but only as stubs next to the enwiki version."""
    with ug_utils.stage(conn, SCRIPT, 'generate_incomplete_ccc', force) as st:
        if st.skip:
            return

        for languagecode in config.LOCAL_WIKIS:
            df = pd.read_sql("""
                SELECT c.qitem, c.label, c.sitelink_count,
                       loc.title AS local_title, loc.num_bytes AS local_bytes,
                       ref.num_bytes AS ref_bytes,
                       COALESCE(pv.views, 0) AS views
                FROM article_sizes loc
                JOIN ccc_items c ON c.qitem = loc.qitem
                LEFT JOIN article_sizes ref
                       ON ref.qitem = loc.qitem AND ref.languagecode = ?
                LEFT JOIN pageviews pv ON pv.qitem = loc.qitem
                WHERE loc.languagecode = ?
            """, conn, params=(config.REFERENCE_WIKI, languagecode))

            if df.empty:
                print(f'  {languagecode}wiki: no sized articles')
                continue

            df['ref_bytes'] = df.ref_bytes.fillna(0)
            df['completeness'] = (
                100.0 * df.local_bytes / df.ref_bytes.where(df.ref_bytes > 0)
            ).round(1)
            df['is_stub'] = df.local_bytes < 2000
            df = df.sort_values(['views', 'sitelink_count'], ascending=False)
            _export(df, f'ug_incomplete_{languagecode}')

            stubs = int(df.is_stub.sum())
            print(f'  {languagecode}wiki: {stubs}/{len(df)} Uganda articles '
                  f'under 2KB ({100 * stubs // max(len(df), 1)}%)')


def generate_gender_gap(conn, force=False):
    """Gender balance among Ugandan biographies, overall and per wiki."""
    with ug_utils.stage(conn, SCRIPT, 'generate_gender_gap', force) as st:
        if st.skip:
            return

        people = pd.read_sql("""
            SELECT qitem, gender_qid, sitelink_count
            FROM ccc_items WHERE gender_qid IS NOT NULL""", conn)

        rows = [{
            'scope': 'all wikis (CCC corpus)',
            'men': int((people.gender_qid == MALE).sum()),
            'women': int((people.gender_qid == FEMALE).sum()),
            'other': int((~people.gender_qid.isin([MALE, FEMALE])).sum()),
        }]

        for languagecode in config.TARGET_WIKIS:
            present = {r[0] for r in conn.execute(
                'SELECT qitem FROM sitelinks WHERE languagecode=?', (languagecode,))}
            here = people[people.qitem.isin(present)]
            rows.append({
                'scope': f'{languagecode}wiki',
                'men': int((here.gender_qid == MALE).sum()),
                'women': int((here.gender_qid == FEMALE).sum()),
                'other': int((~here.gender_qid.isin([MALE, FEMALE])).sum()),
            })

        df = pd.DataFrame(rows)
        df['total'] = df.men + df.women + df.other
        df['pct_women'] = (100.0 * df.women / df.total.where(df.total > 0)).round(1)
        _export(df, 'ug_gender_gap')
        for _, r in df.iterrows():
            print(f'  {r.scope}: {r.women} women / {r.total} biographies '
                  f'({r.pct_women}%)')

        # The women most worth translating into the local wikis.
        lg_present = {r[0] for r in conn.execute(
            'SELECT qitem FROM sitelinks WHERE languagecode=?', ('lg',))}
        women = pd.read_sql("""
            SELECT c.qitem, c.label, c.sitelink_count, c.occupation_qid,
                   en.title AS en_title, COALESCE(pv.views,0) AS views
            FROM ccc_items c
            LEFT JOIN sitelinks en ON en.qitem=c.qitem AND en.languagecode='en'
            LEFT JOIN pageviews pv ON pv.qitem=c.qitem
            WHERE c.gender_qid = ?""", conn, params=(FEMALE,))
        labels = _labels(conn)
        women['occupation'] = women.occupation_qid.map(
            lambda q: labels.get(q, '') if q else '')
        women['in_lgwiki'] = women.qitem.isin(lg_present)
        women = women.sort_values(['views', 'sitelink_count'], ascending=False)
        _export(women, 'ug_women_biographies')


def generate_geography_gap(conn, force=False):
    """Which parts of Uganda the corpus actually covers."""
    with ug_utils.stage(conn, SCRIPT, 'generate_geography_gap', force) as st:
        if st.skip:
            return

        labels = _labels(conn)
        df = pd.read_sql("""
            SELECT admin_qid, COUNT(*) AS items
            FROM ccc_items WHERE admin_qid IS NOT NULL
            GROUP BY admin_qid ORDER BY items DESC""", conn)
        df['admin_label'] = df.admin_qid.map(lambda q: labels.get(q, q))
        _export(df[['admin_qid', 'admin_label', 'items']], 'ug_admin_coverage')

        geo = pd.read_sql("""
            SELECT qitem, label, latitude, longitude, sitelink_count
            FROM ccc_items
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL""", conn)
        _export(geo, 'ug_geolocated_items')
        print(f'  {len(geo)} CCC items carry coordinates')

        # Do Uganda's own administrative units have articles locally?
        query = """
        SELECT ?unit ?unitLabel ?sl
               (BOUND(?en) AS ?in_en) (BOUND(?lg) AS ?in_lg) (BOUND(?sw) AS ?in_sw)
        WHERE {
          ?unit wdt:P131 wd:Q1036 ; wikibase:sitelinks ?sl .
          OPTIONAL { ?en schema:about ?unit ; schema:isPartOf <https://en.wikipedia.org/> }
          OPTIONAL { ?lg schema:about ?unit ; schema:isPartOf <https://lg.wikipedia.org/> }
          OPTIONAL { ?sw schema:about ?unit ; schema:isPartOf <https://sw.wikipedia.org/> }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """
        try:
            rows = run_sparql(query, timeout=300)
        except Exception as error:                     # noqa: BLE001
            print(f'  district query failed ({type(error).__name__}), skipped')
            return

        units = pd.DataFrame([{
            'qitem': qid_from_uri(binding_value(b, 'unit')),
            'name': binding_value(b, 'unitLabel', ''),
            'sitelinks': int(binding_value(b, 'sl', 0)),
            'in_en': binding_value(b, 'in_en') == 'true',
            'in_lg': binding_value(b, 'in_lg') == 'true',
            'in_sw': binding_value(b, 'in_sw') == 'true',
        } for b in rows])
        _export(units, 'ug_admin_units_coverage')
        units.to_sql('admin_units_coverage', conn, if_exists='replace', index=False)
        conn.commit()
        if not units.empty:
            print(f'  {len(units)} first-level units: '
                  f'{int(units.in_en.sum())} in enwiki, '
                  f'{int(units.in_lg.sum())} in lgwiki, '
                  f'{int(units.in_sw.sum())} in swwiki')


def generate_topical_coverage(conn, force=False):
    """Topic mix of the corpus, and how each topic fares in the local wikis."""
    with ug_utils.stage(conn, SCRIPT, 'generate_topical_coverage', force) as st:
        if st.skip:
            return

        labels = _labels(conn)
        items = pd.read_sql('SELECT qitem, types FROM ccc_items', conn)
        present = {lc: {r[0] for r in conn.execute(
            'SELECT qitem FROM sitelinks WHERE languagecode=?', (lc,))}
            for lc in config.TARGET_WIKIS}

        counts = {}
        for qitem, types in items.itertuples(index=False):
            for qid in (types or '').split('|'):
                if not qid:
                    continue
                slot = counts.setdefault(qid, {'items': 0, 'en': 0, 'lg': 0, 'sw': 0})
                slot['items'] += 1
                for lc in config.TARGET_WIKIS:
                    if qitem in present[lc]:
                        slot[lc] += 1

        df = pd.DataFrame([
            {'type_qid': qid, 'type_label': labels.get(qid, qid), **vals}
            for qid, vals in counts.items()])
        df = df.sort_values('items', ascending=False).head(80)
        df['pct_in_lg'] = (100.0 * df.lg / df['items']).round(1)
        df['pct_in_sw'] = (100.0 * df.sw / df['items']).round(1)
        _export(df, 'ug_topical_coverage')
        df.to_sql('topical_coverage', conn, if_exists='replace', index=False)
        conn.commit()


# Coarse buckets used to describe what an edition's Uganda content is *made of*.
# Matched against Wikidata type labels, so no QIDs to go stale.
PLACE_WORDS = (
    'stream', 'hill', 'river', 'mountain', 'island', 'lake', 'waterfall',
    'settlement', 'village', 'town', 'municipality', 'district', 'sub-county',
    'county', 'parish', 'territorial entity', 'valley', 'swamp',
    'protected area', 'national park', 'peak', 'plain', 'forest',
)
# 'city' is deliberately absent: as a substring it also matches "electricity".
# 'settlement', 'town' and 'municipality' already cover populated places.
INSTITUTION_WORDS = (
    'school', 'university', 'college', 'hospital', 'clinic', 'business',
    'company', 'organization', 'organisation', 'club', 'team', 'bank',
    'agency', 'ministry', 'party', 'church', 'mosque', 'institute',
    'enterprise', 'newspaper', 'radio', 'station', 'hotel',
)


def _bucket(type_labels, is_person):
    if is_person:
        return 'people'
    joined = type_labels.lower()
    if any(word in joined for word in PLACE_WORDS):
        return 'places'
    if any(word in joined for word in INSTITUTION_WORDS):
        return 'institutions'
    return 'other'


def generate_edition_composition(conn, force=False):
    """What each edition's Uganda content is made of.

    The single most revealing statistic in this analysis: two editions can
    hold a similar number of Uganda articles and describe entirely different
    Ugandas - one all landscape, the other all people.
    """
    with ug_utils.stage(conn, SCRIPT, 'generate_edition_composition', force) as st:
        if st.skip:
            return

        labels = _labels(conn)
        items = {}
        for qitem, gender, types in conn.execute(
                'SELECT qitem, gender_qid, types FROM ccc_items'):
            names = ', '.join(labels.get(q, '')
                              for q in (types or '').split('|') if q)
            items[qitem] = _bucket(names, gender is not None)

        top = [r[0] for r in conn.execute("""
            SELECT languagecode FROM sitelinks GROUP BY languagecode
            ORDER BY COUNT(DISTINCT qitem) DESC LIMIT 10""")]
        for languagecode in config.TARGET_WIKIS:
            if languagecode not in top:
                top.append(languagecode)

        rows = []
        for languagecode in top:
            tally = {'people': 0, 'places': 0, 'institutions': 0, 'other': 0}
            for (qitem,) in conn.execute(
                    'SELECT qitem FROM sitelinks WHERE languagecode=?',
                    (languagecode,)):
                bucket = items.get(qitem)
                if bucket:
                    tally[bucket] += 1
            total = sum(tally.values())
            rows.append({'languagecode': languagecode, **tally, 'total': total,
                         'pct_people': round(100.0 * tally['people'] / total, 1)
                         if total else 0})

        df = pd.DataFrame(rows).sort_values('total', ascending=False)
        _export(df, 'ug_edition_composition')
        df.to_sql('edition_composition', conn, if_exists='replace', index=False)
        conn.commit()
        for _, r in df.head(6).iterrows():
            print(f'  {r.languagecode}wiki: {r.total} Uganda articles - '
                  f'{r.people} people, {r.places} places, '
                  f'{r.institutions} institutions')


def generate_peer_comparison(conn, force=False):
    """Uganda's corpus next to comparable African countries."""
    with ug_utils.stage(conn, SCRIPT, 'generate_peer_comparison', force) as st:
        if st.skip:
            return

        rows = []
        for qid, name in config.PEER_COUNTRIES.items():
            query = f"""
            SELECT (COUNT(DISTINCT ?item) AS ?withArticle)
                   (COUNT(DISTINCT ?en) AS ?inEn)
            WHERE {{
              ?item wdt:P17 wd:{qid} ; wikibase:sitelinks ?sl .
              FILTER(?sl > 0)
              OPTIONAL {{ ?en schema:about ?item ;
                              schema:isPartOf <https://en.wikipedia.org/> }}
            }}
            """
            # Two flat counts rather than one self-joined query: the join
            # form worked but took minutes per country for the same answer.
            people_query = f"""
            SELECT (COUNT(*) AS ?c) WHERE {{
              ?p wdt:P27 wd:{qid} ; wikibase:sitelinks ?sl . FILTER(?sl > 0)
            }}"""
            women_query = f"""
            SELECT (COUNT(*) AS ?c) WHERE {{
              ?p wdt:P27 wd:{qid} ; wdt:P21 wd:{FEMALE} ;
                 wikibase:sitelinks ?sl . FILTER(?sl > 0)
            }}"""
            try:
                main_row = run_sparql(query, timeout=300)[0]
                people = int(binding_value(
                    run_sparql(people_query, timeout=300)[0], 'c', 0))
                women = int(binding_value(
                    run_sparql(women_query, timeout=300)[0], 'c', 0))
            except Exception as error:                 # noqa: BLE001
                print(f'    {name} failed ({type(error).__name__}), skipped')
                continue
            rows.append({
                'country': name, 'qitem': qid,
                'items_with_article': int(binding_value(main_row, 'withArticle', 0)),
                'in_enwiki': int(binding_value(main_row, 'inEn', 0)),
                'biographies': people,
                'women_biographies': women,
                'pct_women': round(100.0 * women / people, 1) if people else 0,
            })
            print(f'    {name}: {rows[-1]["items_with_article"]} items, '
                  f'{people} biographies, {rows[-1]["pct_women"]}% women')

        df = pd.DataFrame(rows).sort_values('items_with_article', ascending=False)
        _export(df, 'ug_peer_countries')
        df.to_sql('peer_countries', conn, if_exists='replace', index=False)
        conn.commit()


def export_full_corpus(conn, force=False):
    """One flat CSV of the whole corpus, for anyone who wants to re-slice it."""
    with ug_utils.stage(conn, SCRIPT, 'export_full_corpus', force) as st:
        if st.skip:
            return

        labels = _labels(conn)
        df = pd.read_sql("""
            SELECT c.qitem, c.label, c.sitelink_count, c.num_strategies,
                   c.strategies, c.types, c.gender_qid, c.admin_qid,
                   c.latitude, c.longitude, c.date_of_birth, c.inception,
                   en.title AS en_title, lg.title AS lg_title,
                   sw.title AS sw_title,
                   COALESCE(pv.views, 0) AS en_views
            FROM ccc_items c
            LEFT JOIN sitelinks en ON en.qitem=c.qitem AND en.languagecode='en'
            LEFT JOIN sitelinks lg ON lg.qitem=c.qitem AND lg.languagecode='lg'
            LEFT JOIN sitelinks sw ON sw.qitem=c.qitem AND sw.languagecode='sw'
            LEFT JOIN pageviews pv ON pv.qitem=c.qitem
        """, conn)
        df['is_core'] = df.strategies.fillna('').apply(
            lambda s: int(any(name in s for name in CORE_STRATEGIES)))
        df['gender'] = df.gender_qid.map(
            {MALE: 'male', FEMALE: 'female'}).fillna('')
        df['admin_label'] = df.admin_qid.map(lambda q: labels.get(q, '') if q else '')
        df['type_labels'] = df.types.fillna('').apply(
            lambda s: ', '.join(labels.get(q, q) for q in s.split('|')[:4] if q))
        _export(df, 'ug_ccc_full_corpus')


def main(force=False):
    conn = ug_utils.connect()
    generate_corpus_overview(conn, force)
    generate_language_coverage(conn, force)
    generate_missing_ccc(conn, force)
    generate_incomplete_ccc(conn, force)
    generate_gender_gap(conn, force)
    generate_geography_gap(conn, force)
    generate_topical_coverage(conn, force)
    generate_edition_composition(conn, force)
    generate_peer_comparison(conn, force)
    export_full_corpus(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
