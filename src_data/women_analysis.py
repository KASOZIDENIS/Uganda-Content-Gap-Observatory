# -*- coding: utf-8 -*-
"""Stage 4: Ugandan women by field, and the two worklists that follow.

Answers two different questions that need two different lists:

  translate  she has an English article but no Luganda one - the work is
             translation, and the source text already exists
  create     she has no article in any language - the work is writing from
             sources, and nothing exists to translate

Both are broken down by field (football, politics, music, ...) because the
gaps are not evenly distributed and different editor groups care about
different fields.

"Ugandan woman" here means Wikidata P27 = Uganda and P21 = female. Citizenship
alone is used deliberately: adding a birth-place branch with the pipeline's
single-country guard makes the query time out on WDQS, and citizenship is the
standard reading.
"""

import pandas as pd

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri, run_sparql

SCRIPT = 'women_analysis'

BASE = '?p wdt:P27 wd:Q1036 ; wdt:P21 wd:Q6581072 .'

# ---------------------------------------------------------------------------
# Field classification. QID sets rather than label matching, so a renamed
# Wikidata label cannot silently empty a bucket.
# ---------------------------------------------------------------------------
FOOTBALL_OCC = {'Q937857'}                        # association football player
FOOTBALL_SPORT = {'Q2736'}                        # association football

SPORT_OCC = {
    'Q3665646',   # basketball player
    'Q17619498',  # netballer
    'Q10873124',  # chess player
    'Q11338576',  # boxer
    'Q10843402',  # swimmer
    'Q11303721',  # golfer
    'Q15117302',  # volleyball player
    'Q12299841',  # cricketer
    'Q11513337',  # athletics competitor
    'Q13415036',  # rugby player
    'Q10833314',  # tennis player
    'Q13141064',  # badminton player
    'Q2066131',   # athlete
    'Q11774891',  # racing cyclist
}
POLITICS_OCC = {
    'Q82955',     # politician
    'Q4175034',   # legislator
    'Q16533',     # judge
    'Q193391',    # diplomat
    'Q83307',     # minister
    'Q212238',    # civil servant
    'Q3242115',   # political activist
}
MEDIA_OCC = {
    'Q1930187',   # journalist
    'Q36180',     # writer
    'Q49757',     # poet
    'Q6625963',   # novelist
    'Q18939491',  # columnist
    'Q947873',    # television presenter
    'Q2722764',   # radio personality
}
ARTS_OCC = {
    'Q33999',     # actor
    'Q639669',    # musician
    'Q177220',    # singer
    'Q4610556',   # model
    'Q5716684',   # dancer
    'Q483501',    # artist
    'Q2865819',   # opera singer
    'Q10798782',  # television actor
}
ACTIVISM_OCC = {
    'Q1476215',   # human rights defender
    'Q15253558',  # activist
    'Q7019111',   # social worker
    'Q11499147',  # women's rights activist
}
ACADEMIA_OCC = {
    'Q1569495',   # lecturer
    'Q37226',     # teacher
    'Q1650915',   # researcher
    'Q1622272',   # university teacher
    'Q3400985',   # academic
    'Q182436',    # librarian
    'Q901',       # scientist
    'Q1622272',
}
HEALTH_OCC = {
    'Q39631',     # physician
    'Q186360',    # nurse
    'Q1250916',   # midwife
}
BUSINESS_OCC = {
    'Q131524',    # entrepreneur
    'Q43845',     # businessperson
    'Q2961975',   # business executive
    'Q326653',    # accountant
}
LAW_OCC = {'Q40348'}          # lawyer

# Evaluated in order; first match wins. Sport sits ahead of politics because
# a sport occupation is unambiguous, while "politician" is often one of
# several roles a public figure holds.
FIELD_RULES = [
    ('Football', FOOTBALL_OCC, FOOTBALL_SPORT),
    ('Other sport', SPORT_OCC, None),          # None = "any sport not football"
    ('Politics & government', POLITICS_OCC, set()),
    ('Media & writing', MEDIA_OCC, set()),
    ('Arts & entertainment', ARTS_OCC, set()),
    ('Activism & social work', ACTIVISM_OCC, set()),
    ('Academia & education', ACADEMIA_OCC, set()),
    ('Health', HEALTH_OCC, set()),
    ('Business & finance', BUSINESS_OCC, set()),
    ('Law', LAW_OCC, set()),
]


def classify(occupations, sports):
    """Assign one primary field. Returns 'Other / unspecified' if nothing fits."""
    occ = set(occupations)
    spo = set(sports)
    for name, occ_set, sport_set in FIELD_RULES:
        if occ & occ_set:
            return name
        if sport_set and (spo & sport_set):
            return name
        if name == 'Other sport' and sport_set is None and (spo - FOOTBALL_SPORT):
            return name
    return 'Other / unspecified'


PEOPLE_QUERY = """
SELECT ?p (SAMPLE(?lab) AS ?label) (SAMPLE(?desc) AS ?description)
       (SAMPLE(?sl) AS ?sitelinks) (SAMPLE(?st) AS ?statements)
       (SAMPLE(?enName) AS ?en) (SAMPLE(?lgName) AS ?lg)
       (SAMPLE(?dob) AS ?birth)
       (GROUP_CONCAT(DISTINCT ?occ; separator="|") AS ?occupations)
       (GROUP_CONCAT(DISTINCT ?sport; separator="|") AS ?sports)
WHERE {
  ?p wdt:P27 wd:Q1036 ; wdt:P21 wd:Q6581072 ;
     wikibase:sitelinks ?sl ; wikibase:statements ?st .
  OPTIONAL { ?p rdfs:label ?lab . FILTER(LANG(?lab) = "en") }
  OPTIONAL { ?p schema:description ?desc . FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?p wdt:P106 ?occ }
  OPTIONAL { ?p wdt:P641 ?sport }
  OPTIONAL { ?p wdt:P569 ?dob }
  OPTIONAL { ?enArt schema:about ?p ;
             schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enName }
  OPTIONAL { ?lgArt schema:about ?p ;
             schema:isPartOf <https://lg.wikipedia.org/> ; schema:name ?lgName }
}
GROUP BY ?p
"""


def fetch_women(conn, force=False):
    """Pull every Ugandan woman in Wikidata with the fields we classify on."""
    with ug_utils.stage(conn, SCRIPT, 'fetch_women', force) as st:
        if st.skip:
            return

        rows = run_sparql(PEOPLE_QUERY, timeout=600)
        print(f'  fetched {len(rows)} Ugandan women from Wikidata')

        conn.execute('DROP TABLE IF EXISTS women')
        conn.execute("""CREATE TABLE women (
            qitem text PRIMARY KEY, label text, description text,
            sitelink_count int, statements int,
            en_title text, lg_title text, date_of_birth text,
            occupations text, sports text, field text)""")

        records = []
        for b in rows:
            occupations = [qid_from_uri(u) for u in
                           (binding_value(b, 'occupations', '') or '').split('|') if u]
            sports = [qid_from_uri(u) for u in
                      (binding_value(b, 'sports', '') or '').split('|') if u]
            records.append((
                qid_from_uri(binding_value(b, 'p')),
                binding_value(b, 'label'),
                binding_value(b, 'description'),
                int(binding_value(b, 'sitelinks', 0)),
                int(binding_value(b, 'statements', 0)),
                binding_value(b, 'en'),
                binding_value(b, 'lg'),
                binding_value(b, 'birth'),
                '|'.join(occupations), '|'.join(sports),
                classify(occupations, sports)))

        conn.executemany(
            'INSERT OR REPLACE INTO women VALUES (?,?,?,?,?,?,?,?,?,?,?)', records)
        conn.commit()
        print(f'  stored {len(records)} women')


def _occupation_labels(conn):
    """Readable occupation names, reusing entity_labels and filling gaps."""
    known = dict(conn.execute('SELECT qitem, label FROM entity_labels'))
    needed = set()
    for (occupations,) in conn.execute('SELECT occupations FROM women'):
        needed.update(q for q in (occupations or '').split('|')
                      if q and q not in known)
    needed = sorted(needed)
    if needed:
        print(f'  resolving {len(needed)} new occupation labels')
        template = """
        SELECT ?item ?itemLabel WHERE {
          VALUES ?item { {values} }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }"""
        for b in ug_utils.run_sparql_chunked(template, needed,
                                             chunk_size=300, label='occ labels'):
            qid = qid_from_uri(binding_value(b, 'item'))
            known[qid] = binding_value(b, 'itemLabel')
            conn.execute('INSERT OR REPLACE INTO entity_labels VALUES (?,?)',
                         (qid, known[qid]))
        conn.commit()
    return known


def generate_women_outputs(conn, force=False):
    """Summary by field, plus the translate and create worklists."""
    with ug_utils.stage(conn, SCRIPT, 'generate_women_outputs', force) as st:
        if st.skip:
            return

        labels = _occupation_labels(conn)
        df = pd.read_sql('SELECT * FROM women', conn)
        df['has_en'] = df.en_title.notna()
        df['has_lg'] = df.lg_title.notna()
        df['has_any'] = df.sitelink_count > 0
        df['occupation_names'] = df.occupations.fillna('').apply(
            lambda s: ', '.join(labels.get(q, q) for q in s.split('|')[:4] if q))

        # Reader demand, where we already have it from the main pipeline.
        views = dict(conn.execute('SELECT qitem, views FROM pageviews'))
        df['views'] = df.qitem.map(views).fillna(0).astype(int)

        # ---- summary by field -------------------------------------------
        summary = df.groupby('field').agg(
            women=('qitem', 'count'),
            with_any_article=('has_any', 'sum'),
            in_english=('has_en', 'sum'),
            in_luganda=('has_lg', 'sum'),
        ).reset_index()
        summary['en_not_lg'] = df[df.has_en & ~df.has_lg].groupby(
            'field').size().reindex(summary.field).fillna(0).astype(int).values
        summary['no_article_anywhere'] = df[~df.has_any].groupby(
            'field').size().reindex(summary.field).fillna(0).astype(int).values
        summary['pct_in_luganda'] = (
            100.0 * summary.in_luganda / summary.women).round(1)
        summary = summary.sort_values('women', ascending=False)

        total = pd.DataFrame([{
            'field': 'ALL FIELDS',
            'women': len(df),
            'with_any_article': int(df.has_any.sum()),
            'in_english': int(df.has_en.sum()),
            'in_luganda': int(df.has_lg.sum()),
            'en_not_lg': int((df.has_en & ~df.has_lg).sum()),
            'no_article_anywhere': int((~df.has_any).sum()),
            'pct_in_luganda': round(100.0 * df.has_lg.sum() / len(df), 1),
        }])
        summary = pd.concat([total, summary], ignore_index=True)
        _export(summary, 'ug_women_by_field')
        summary.to_sql('women_by_field', conn, if_exists='replace', index=False)

        print('  field breakdown:')
        for _, r in summary.iterrows():
            print(f'    {r.field:26s} {r.women:5d} women | '
                  f'en {r.in_english:4d} | lg {r.in_luganda:4d} | '
                  f'en-not-lg {r.en_not_lg:4d} | no article {r.no_article_anywhere:5d}')

        # ---- worklist 1: translate (English exists, Luganda does not) ----
        translate = df[df.has_en & ~df.has_lg].copy()
        translate = translate.sort_values(
            ['views', 'sitelink_count', 'statements'], ascending=False)
        _export(translate[['qitem', 'label', 'field', 'en_title',
                           'sitelink_count', 'views', 'statements',
                           'occupation_names', 'description']],
                'ug_women_translate_to_lg')
        translate.head(400).to_sql('women_translate', conn,
                                   if_exists='replace', index=False)

        # ---- worklist 2: create (no article in any language) -------------
        create = df[~df.has_any].copy()
        # No pageviews and no sitelinks exist for these, so Wikidata statement
        # count stands in as a documentation proxy: the better described she
        # already is, the easier she is to source an article from.
        create = create.sort_values(['statements', 'label'],
                                    ascending=[False, True])
        _export(create[['qitem', 'label', 'field', 'statements',
                        'date_of_birth', 'occupation_names', 'description']],
                'ug_women_create_from_scratch')
        create.head(400).to_sql('women_create', conn,
                                if_exists='replace', index=False)

        # ---- per-field split of both lists ------------------------------
        for field in sorted(df.field.unique()):
            slug = (field.lower().replace(' & ', '_').replace(' / ', '_')
                    .replace(' ', '_'))
            sub_t = translate[translate.field == field]
            if len(sub_t):
                _export(sub_t[['qitem', 'label', 'en_title', 'sitelink_count',
                               'views', 'occupation_names']],
                        f'ug_women_translate_{slug}')
            sub_c = create[create.field == field]
            if len(sub_c):
                _export(sub_c[['qitem', 'label', 'statements',
                               'occupation_names', 'description']],
                        f'ug_women_create_{slug}')

        print(f'  translate list: {len(translate)} women')
        print(f'  create list:    {len(create)} women')


def _export(df, name):
    import os
    path = os.path.join(config.DATA_PATH, name + '.csv')
    df.to_csv(path, index=False, encoding='utf-8')
    print(f'    -> {name}.csv ({len(df)} rows)')


def measure_luganda_articles(conn, force=False):
    """Measure how substantial Luganda's women's biographies actually are.

    Coverage counts alone cannot distinguish a written article from a
    generated placeholder, and the parity finding depends on the difference.
    """
    with ug_utils.stage(conn, SCRIPT, 'measure_luganda_articles', force) as st:
        if st.skip:
            return

        titles = [r[0] for r in conn.execute(
            'SELECT lg_title FROM women WHERE lg_title IS NOT NULL')]
        if not titles:
            print('  no Luganda women biographies to measure')
            return

        session = ug_utils.get_session()
        api = 'https://lg.wikipedia.org/w/api.php'
        sizes = []
        for i in range(0, len(titles), 50):
            params = {'action': 'query', 'format': 'json', 'prop': 'info',
                      'titles': '|'.join(titles[i:i + 50])}
            try:
                payload = session.get(api, params=params, timeout=60).json()
            except Exception:                          # noqa: BLE001
                continue
            sizes += [p['length'] for p in
                      payload.get('query', {}).get('pages', {}).values()
                      if 'length' in p]

        if not sizes:
            print('  could not measure any articles')
            return

        sizes.sort()
        median = sizes[len(sizes) // 2]
        stubs = sum(1 for s in sizes if s < 2000)
        conn.execute('DROP TABLE IF EXISTS women_lg_article_sizes')
        conn.execute("""CREATE TABLE women_lg_article_sizes (
            measured int, median_bytes int, stubs int, pct_stubs real)""")
        conn.execute('INSERT INTO women_lg_article_sizes VALUES (?,?,?,?)',
                     (len(sizes), median, stubs,
                      round(100.0 * stubs / len(sizes), 1)))
        conn.commit()
        print(f'  measured {len(sizes)} Luganda women biographies: '
              f'median {median:,} bytes, {stubs} under 2KB '
              f'({100 * stubs // len(sizes)}%)')


def main(force=False):
    conn = ug_utils.connect()
    fetch_women(conn, force)
    generate_women_outputs(conn, force)
    measure_luganda_articles(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
