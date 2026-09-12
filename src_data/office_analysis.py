# -*- coding: utf-8 -*-
"""Stage 6: Ugandan women who hold or held public office, and their articles.

Answers a narrower question than stage 4. Stage 4 asks which fields Ugandan
women work in, inferred from occupation. This asks who actually held office,
which Wikidata records separately as P39 (position held), and then splits the
office holders three ways:

  with an article      she is covered somewhere, in some language
  no article anywhere  she held national office and Wikipedia has no page
  translate to lg      an English article exists, a Luganda one does not

Two retrieval branches, unioned:

  citizen_office  P27 = Uganda, P21 = female, and any P39
  ugandan_office  P21 = female with a P39 whose position is tied to Uganda
                  (P1001 applies-to-jurisdiction, or P17 country)

The second branch is what catches an office holder whose citizenship is not
recorded. It also picks up foreign envoys posted to Uganda, so citizenship is
stored per person rather than assumed, and the page says which is which.

Seniority comes from config.OFFICE_TIERS, shared with the page builder.

CSV export here uses the standard library rather than pandas: this stage does
its aggregation in SQL and has no dataframe work to justify the import.
"""

import csv
import os

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri, run_sparql, run_sparql_chunked

SCRIPT = 'office_analysis'

FEMALE = 'Q6581072'

# Cheap ID queries first. Asking for the person facts in the same query as the
# UNION makes WDQS return 502, so the set is resolved first and the details
# come back through chunked VALUES lookups, as in content_retrieval.
HOLDERS_CITIZEN = f"""
SELECT DISTINCT ?p WHERE {{
  ?p wdt:P27 wd:{config.UGANDA} ; wdt:P21 wd:{FEMALE} ; wdt:P39 ?pos .
}}"""

HOLDERS_UGANDAN_OFFICE = f"""
SELECT DISTINCT ?p WHERE {{
  ?p wdt:P21 wd:{FEMALE} ; wdt:P39 ?pos .
  {{ ?pos wdt:P1001 wd:{config.UGANDA} }} UNION {{ ?pos wdt:P17 wd:{config.UGANDA} }}
}}"""

FACTS_QUERY = """
SELECT ?p (SAMPLE(?lab) AS ?label) (SAMPLE(?desc) AS ?description)
       (SAMPLE(?sl) AS ?sitelinks) (SAMPLE(?st) AS ?statements)
       (SAMPLE(?enName) AS ?en) (SAMPLE(?lgName) AS ?lg)
WHERE {
  VALUES ?p { {values} }
  ?p wikibase:sitelinks ?sl ; wikibase:statements ?st .
  OPTIONAL { ?p rdfs:label ?lab . FILTER(LANG(?lab) = "en") }
  OPTIONAL { ?p schema:description ?desc . FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?enArt schema:about ?p ;
             schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enName }
  OPTIONAL { ?lgArt schema:about ?p ;
             schema:isPartOf <https://lg.wikipedia.org/> ; schema:name ?lgName }
} GROUP BY ?p
"""

# p:/ps:/pq: rather than wdt:, so the term dates on the statement come too.
POSITIONS_QUERY = """
SELECT ?p ?pos ?posLabel ?start ?end WHERE {
  VALUES ?p { {values} }
  ?p p:P39 ?stmt . ?stmt ps:P39 ?pos .
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def _export(rows, header, name):
    """Write one CSV, matching the naming the other stages use."""
    path = os.path.join(config.DATA_PATH, name + '.csv')
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    print(f'    -> {name}.csv ({len(rows)} rows)')


def fetch_office_holders(conn, force=False):
    """Resolve the office holders, their articles and their positions."""
    with ug_utils.stage(conn, SCRIPT, 'fetch_office_holders', force) as st:
        if st.skip:
            return

        citizens = {qid_from_uri(binding_value(b, 'p'))
                    for b in run_sparql(HOLDERS_CITIZEN, timeout=300)}
        by_office = {qid_from_uri(binding_value(b, 'p'))
                     for b in run_sparql(HOLDERS_UGANDAN_OFFICE, timeout=300)}
        qitems = sorted(citizens | by_office)
        print(f'  citizen_office {len(citizens)} | ugandan_office {len(by_office)} '
              f'| union {len(qitems)} '
              f'({len(by_office - citizens)} with no Ugandan citizenship recorded)')

        conn.execute('DROP TABLE IF EXISTS office_positions')
        conn.execute("""CREATE TABLE office_positions (
            qitem text, position_qid text, position_label text, tier text,
            start_date text, end_date text,
            PRIMARY KEY (qitem, position_qid))""")

        positions = {}
        rows = []
        for b in run_sparql_chunked(POSITIONS_QUERY, qitems,
                                    chunk_size=350, label='positions'):
            qitem = qid_from_uri(binding_value(b, 'p'))
            position_qid = qid_from_uri(binding_value(b, 'pos'))
            name = binding_value(b, 'posLabel', '') or ''
            positions.setdefault(qitem, []).append(name)
            rows.append((qitem, position_qid, name, config.office_tier(name),
                         binding_value(b, 'start'), binding_value(b, 'end')))
        conn.executemany(
            'INSERT OR IGNORE INTO office_positions VALUES (?,?,?,?,?,?)', rows)
        conn.commit()
        # One person can hold one position over several terms, which the
        # primary key collapses, so report what landed rather than what we sent.
        stored = conn.execute('SELECT COUNT(*) FROM office_positions').fetchone()[0]
        print(f'  stored {stored} person-position pairs from {len(rows)} statements')

        conn.execute('DROP TABLE IF EXISTS office_women')
        conn.execute("""CREATE TABLE office_women (
            qitem text PRIMARY KEY, label text, description text,
            sitelink_count int, statements int, en_title text, lg_title text,
            ugandan_citizen int, tier text)""")

        people = []
        for b in run_sparql_chunked(FACTS_QUERY, qitems,
                                    chunk_size=350, label='facts'):
            qitem = qid_from_uri(binding_value(b, 'p'))
            people.append((
                qitem,
                binding_value(b, 'label'),
                binding_value(b, 'description'),
                int(binding_value(b, 'sitelinks', 0)),
                int(binding_value(b, 'statements', 0)),
                binding_value(b, 'en'),
                binding_value(b, 'lg'),
                1 if qitem in citizens else 0,
                config.most_senior_tier(positions.get(qitem, []))))
        conn.executemany(
            'INSERT OR REPLACE INTO office_women VALUES (?,?,?,?,?,?,?,?,?)', people)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_office_tier '
                     'ON office_women(tier)')
        conn.commit()
        print(f'  stored {len(people)} office holders')

        for tier in config.BIG_OFFICE_TIERS + ('other',):
            n = conn.execute('SELECT COUNT(*) FROM office_women WHERE tier=?',
                             (tier,)).fetchone()[0]
            if n:
                print(f'    {config.TIER_LABELS[tier]}: {n}')


def generate_office_outputs(conn, force=False):
    """The three worklists, plus a per-position summary."""
    with ug_utils.stage(conn, SCRIPT, 'generate_office_outputs', force) as st:
        if st.skip:
            return

        order = {tier: i for i, tier in enumerate(config.BIG_OFFICE_TIERS)}
        order['other'] = len(order)

        holders = conn.execute("""
            SELECT qitem, label, description, sitelink_count, statements,
                   en_title, lg_title, ugandan_citizen, tier
            FROM office_women""").fetchall()

        held = {}
        for qitem, name in conn.execute(
                'SELECT qitem, position_label FROM office_positions'):
            held.setdefault(qitem, []).append(name)

        def enrich(row):
            (qitem, label, description, sitelinks, statements,
             en_title, lg_title, citizen, tier) = row
            offices = '; '.join(sorted(set(held.get(qitem, []))))
            return {
                'sort': (order[tier], -statements, (label or '')),
                'row': [qitem, label, description, config.TIER_LABELS[tier],
                        offices, sitelinks, statements, en_title, lg_title,
                        'yes' if citizen else 'no'],
                'tier': tier, 'sitelinks': sitelinks,
                'en': en_title, 'lg': lg_title,
            }

        records = sorted((enrich(r) for r in holders), key=lambda x: x['sort'])
        big = [r for r in records if r['tier'] != 'other']

        header = ['qitem', 'label', 'description', 'tier', 'positions_held',
                  'sitelink_count', 'statements', 'en_title', 'lg_title',
                  'ugandan_citizen']
        _export([r['row'] for r in records], header, 'ug_women_office_holders')
        _export([r['row'] for r in big if r['sitelinks'] > 0], header,
                'ug_women_office_with_article')
        _export([r['row'] for r in big if r['sitelinks'] == 0], header,
                'ug_women_office_no_article')
        _export([r['row'] for r in big if r['en'] and not r['lg']], header,
                'ug_women_office_translate_to_lg')

        # Per-position summary, so a campaign can be aimed at one office.
        conn.execute('DROP TABLE IF EXISTS office_summary')
        conn.execute("""CREATE TABLE office_summary (
            position_qid text PRIMARY KEY, position_label text, tier text,
            holders int, with_article int, no_article int, needs_lg int)""")
        summary = conn.execute("""
            SELECT p.position_qid, p.position_label, p.tier,
                   COUNT(DISTINCT w.qitem) AS holders,
                   SUM(CASE WHEN w.sitelink_count > 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN w.sitelink_count = 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN w.en_title IS NOT NULL
                             AND w.lg_title IS NULL THEN 1 ELSE 0 END)
            FROM office_positions p
            JOIN office_women w ON w.qitem = p.qitem
            GROUP BY p.position_qid, p.position_label, p.tier
            ORDER BY holders DESC""").fetchall()
        conn.executemany(
            'INSERT OR REPLACE INTO office_summary VALUES (?,?,?,?,?,?,?)', summary)
        conn.commit()
        _export(summary, ['position_qid', 'position_label', 'tier', 'holders',
                          'with_article', 'no_article', 'needs_lg'],
                'ug_women_office_by_position')

        no_article = sum(1 for r in big if r['sitelinks'] == 0)
        print(f'  {len(big)} women in public office | '
              f'{len(big) - no_article} with an article | '
              f'{no_article} with none | '
              f"{sum(1 for r in big if r['en'] and not r['lg'])} to translate")


def main(force=False):
    conn = ug_utils.connect()
    fetch_office_holders(conn, force)
    generate_office_outputs(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
