# -*- coding: utf-8 -*-
"""Render the full item list for the edition holding the most Uganda articles.

The dashboard states that the largest Uganda encyclopedia in the world holds
two biographies. This page is the evidence: every one of that edition's Uganda
articles, with the Wikidata type that put it there.

Which edition that is comes from the data, not from a constant, so the page
follows the ranking if another edition overtakes it in a later cycle.

Reads only SQLite, so it needs no network and no pipeline dependencies.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402


# Worklist-grade strategies. An item reached only by the weaker ones is in the
# corpus for recall, and is worth flagging here because it is the reason a
# Uganda list can contain Finland.
CORE_STRATEGIES = ('country_wd', 'citizenship_wd', 'location_wd',
                   'birth_death_wd')

# People first, then the buckets that thin out fastest. The ordering is the
# argument: whoever opens this page should hit the biographies immediately.
BUCKET_ORDER = ('people', 'institutions', 'other', 'places')


def load(conn):
    """Everything the page needs, for whichever edition ranks first."""
    languagecode, total = conn.execute("""
        SELECT languagecode, COUNT(DISTINCT qitem) AS n FROM sitelinks
        GROUP BY languagecode ORDER BY n DESC LIMIT 1""").fetchone()

    labels = dict(conn.execute('SELECT qitem, label FROM entity_labels'))
    stats = conn.execute(
        'SELECT articles, active_editors FROM edition_stats WHERE languagecode=?',
        (languagecode,)).fetchone()

    items = []
    for qitem, title, label, sitelinks, gender, types, strategies in conn.execute("""
            SELECT c.qitem, s.title, c.label, c.sitelink_count,
                   c.gender_qid, c.types, c.strategies
            FROM sitelinks s JOIN ccc_items c ON c.qitem = s.qitem
            WHERE s.languagecode = ?""", (languagecode,)):
        type_names = [labels.get(q, q) for q in (types or '').split('|') if q]
        bucket = config.bucket_of(', '.join(type_names), gender is not None)
        items.append({
            'qitem': qitem,
            'title': title,
            'label': label,
            'sitelinks': sitelinks or 0,
            'types': type_names,
            'bucket': bucket,
            'core': any(name in (strategies or '') for name in CORE_STRATEGIES),
        })

    items.sort(key=lambda it: (BUCKET_ORDER.index(it['bucket']),
                               -it['sitelinks'], (it['label'] or it['title'] or '')))

    counts = {b: sum(1 for it in items if it['bucket'] == b) for b in BUCKET_ORDER}

    # The headline is not "how many places" but how few distinct kinds of
    # thing account for nearly all of it, so tally the primary type.
    primary = {}
    for it in items:
        name = it['types'][0] if it['types'] else 'no type recorded'
        primary[name] = primary.get(name, 0) + 1

    return {
        'languagecode': languagecode,
        'total': total,
        'items': items,
        'counts': counts,
        'primary': sorted(primary.items(), key=lambda kv: -kv[1]),
        'edition_articles': stats[0] if stats else None,
        'weak_only': sum(1 for it in items if not it['core']),
        # No English label at all is itself a marker of bulk creation, and at
        # this share a blank cell would read as a rendering fault.
        'unlabelled': sum(1 for it in items if not it['label']),
    }
