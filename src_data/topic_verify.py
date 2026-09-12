# -*- coding: utf-8 -*-
"""Settle the topics in last year's categories that our corpus does not hold.

145 of the imported articles are absent from our corpus. That is two different
situations wearing one label, and telling them apart matters in both
directions:

  a recall miss     a genuinely Ugandan topic that our seven retrieval
                    strategies failed to reach. Worth fixing on our side.
  an over-collect   a topic with no structural link to Uganda that a Wikipedia
                    category swept in anyway. Worth knowing before anyone
                    plans work from their ranking.

The second kind is not hypothetical. Their "Governance in Uganda" export
contains Elizabeth II at 8.6 million views, which is 62% of all the readership
their analysis measured, and their write-up attributes that dominance to Idi
Amin and Museveni instead. This project already guards against exactly that
trap: she reaches our corpus by title keyword only and is held off every
worklist for it.

So each missing topic is asked the same question the pipeline asks: is there a
structural Wikidata link to Uganda? Country, a location inside Uganda,
Ugandan citizenship, or birth or death there.

    python src_data/topic_verify.py
"""

import csv
import os

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri

SCRIPT = 'topic_verify'

IN_FILE = os.path.join(config.DATA_PATH, 'topic_areas.csv')
OUT_FILE = os.path.join(config.DATA_PATH, 'topic_offcorpus.csv')

# The same structural test the worklists use, asked of one batch of items.
LINK_QUERY = """
SELECT ?item
       (COUNT(DISTINCT ?country) AS ?country)
       (COUNT(DISTINCT ?admin) AS ?admin)
       (COUNT(DISTINCT ?citizen) AS ?citizen)
       (COUNT(DISTINCT ?born) AS ?born)
WHERE {
  VALUES ?item { {values} }
  OPTIONAL { ?item wdt:P17 wd:Q1036 . BIND(1 AS ?country) }
  OPTIONAL { ?item wdt:P131+ wd:Q1036 . BIND(1 AS ?admin) }
  OPTIONAL { ?item wdt:P27 wd:Q1036 . BIND(1 AS ?citizen) }
  OPTIONAL { { ?item wdt:P19 ?bp } UNION { ?item wdt:P20 ?bp }
             ?bp wdt:P17 wd:Q1036 . BIND(1 AS ?born) }
}
GROUP BY ?item
"""


def verify(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'verify_offcorpus', force) as st:
        if st.skip:
            return

        with open(IN_FILE, encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        in_corpus = {q for (q,) in conn.execute('SELECT qitem FROM ccc_items')}

        topics = {}
        for row in rows:
            if row['qitem'] in in_corpus:
                continue
            topics.setdefault(row['qitem'], {
                'qitem': row['qitem'], 'title': row['title'],
                'areas': [], 'their_views': row['their_views'] or '0'})
            topics[row['qitem']]['areas'].append(row['area'])

        qids = sorted(topics)
        print(f'  {len(qids)} imported topics are not in our corpus; asking '
              f'Wikidata whether each has a structural link to Uganda')

        linked = {}
        for b in ug_utils.run_sparql_chunked(LINK_QUERY, qids, chunk_size=120,
                                             label='topic links'):
            qid = qid_from_uri(binding_value(b, 'item'))
            linked[qid] = {
                'country': int(binding_value(b, 'country', 0) or 0),
                'admin': int(binding_value(b, 'admin', 0) or 0),
                'citizen': int(binding_value(b, 'citizen', 0) or 0),
                'born': int(binding_value(b, 'born', 0) or 0),
            }

        conn.execute('DROP TABLE IF EXISTS topic_offcorpus')
        conn.execute("""CREATE TABLE topic_offcorpus (
            qitem text PRIMARY KEY, title text, areas text,
            their_views int, verdict text, link text)""")

        out, tally = [], {}
        for qid in qids:
            hits = linked.get(qid, {})
            names = [name for name, key in
                     (('country', 'country'), ('inside Uganda', 'admin'),
                      ('citizenship', 'citizen'), ('birth or death', 'born'))
                     if hits.get(key)]
            verdict = 'recall_miss' if names else 'over_collected'
            tally[verdict] = tally.get(verdict, 0) + 1
            topic = topics[qid]
            out.append((qid, topic['title'], '; '.join(sorted(topic['areas'])),
                        int(topic['their_views'] or 0), verdict,
                        ', '.join(names)))

        conn.executemany(
            'INSERT OR REPLACE INTO topic_offcorpus VALUES (?,?,?,?,?,?)', out)
        conn.commit()

        with open(OUT_FILE, 'w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['qitem', 'title', 'areas', 'their_views',
                             'verdict', 'link'])
            writer.writerows(sorted(out, key=lambda r: -r[3]))

        print(f'  recall misses (really Ugandan, we missed them): '
              f'{tally.get("recall_miss", 0)}')
        print(f'  over-collected by their categories: '
              f'{tally.get("over_collected", 0)}')
        print(f'    -> {OUT_FILE}')


def main(force=False):
    conn = ug_utils.connect()
    verify(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
