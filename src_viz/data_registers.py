# -*- coding: utf-8 -*-
"""Uganda's official registers beside Wikimedia's record of them.

Reads the register_entries table that src_data/official_registers.py fills:
the UBOS administrative hierarchy and the Electoral Commission's constituency
and MP results, each entry marked with whether any Wikipedia describes it.
"""

import config

KIND_LABELS = {
    'district': 'Districts',
    'county': 'Counties',
    'constituency': 'Parliamentary constituencies',
    'mp': 'Members of Parliament',
    'subcounty': 'Sub-counties',
    'parish': 'Parishes',
}
KIND_ORDER = tuple(KIND_LABELS)
SOURCE_LABELS = {'UBOS': 'Uganda Bureau of Statistics',
                 'EC': 'Electoral Commission'}

# Kinds listed in full. Sub-counties and parishes run to thousands, so they
# are sampled on the page and complete in the CSV export.
LIST_IN_FULL = ('district', 'county', 'constituency', 'mp')
SAMPLE = 60


def _has(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone() is not None


def load(conn):
    if not _has(conn, 'register_entries'):
        raise SystemExit('no register_entries table\n'
                         'run: python src_data/official_registers.py')

    kinds = []
    for key in KIND_ORDER:
        row = conn.execute("""
            SELECT COUNT(*),
                   SUM(verdict = 'has_article'),
                   SUM(verdict = 'no_article_found'),
                   MIN(source)
            FROM register_entries WHERE kind = ?""", (key,)).fetchone()
        total, described, missing, source = row
        if not total:
            continue
        kinds.append({
            'key': key,
            'label': KIND_LABELS[key],
            'source': source,
            'sourceLabel': SOURCE_LABELS.get(source, source),
            'total': total,
            'described': described or 0,
            'missing': missing or 0,
            'covered': 100.0 * (described or 0) / total,
            'listed': key in LIST_IN_FULL,
        })

    total = sum(k['total'] for k in kinds)
    described = sum(k['described'] for k in kinds)
    missing = sum(k['missing'] for k in kinds)

    rows, omitted = [], 0
    for k in kinds:
        limit = -1 if k['listed'] else SAMPLE
        query = """
            SELECT name, district, parent, party, votes
            FROM register_entries
            WHERE kind = ? AND verdict = 'no_article_found'
            ORDER BY district, name"""
        got = conn.execute(query if limit < 0 else query + ' LIMIT ?',
                           (k['key'],) if limit < 0
                           else (k['key'], limit)).fetchall()
        if limit >= 0:
            omitted += max(0, k['missing'] - len(got))
        for name, district, parent, party, votes in got:
            rows.append({
                'key': f'{k["key"]}|{district}|{name}',
                'kind': k['key'],
                'kindLabel': k['label'],
                'name': name,
                'district': district,
                'parent': parent or '',
                'party': party or '',
                'votes': votes,
            })

    # The MPs are the one cohort of people here, and the sharpest of the
    # lists: every one of them was elected to the national parliament.
    mps = [r for r in rows if r['kind'] == 'mp']

    return {
        'kinds': kinds,
        'total': total,
        'described': described,
        'missing': missing,
        'rows': rows,
        'omitted': omitted,
        'sampleSize': SAMPLE,
        'nMps': next((k['total'] for k in kinds if k['key'] == 'mp'), 0),
        'mpsMissing': len(mps),
        'kindLabels': dict(KIND_LABELS),
        'sourceLabels': dict(SOURCE_LABELS),
    }
