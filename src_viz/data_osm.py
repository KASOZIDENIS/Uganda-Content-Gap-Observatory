# -*- coding: utf-8 -*-
"""OpenStreetMap's Uganda beside Wikimedia's.

Reads the osm_features and osm_matched tables that src_data/osm_features.py
fills, and keeps two questions apart because they are not the same question:

  the cross-reference gap  how many named OSM features carry a wikidata or
                           wikipedia tag. A statement about OSM's tagging,
                           and mostly fixable by mappers.
  the documentation gap    whether any Wikipedia describes the place, decided
                           by matching position and name against this
                           project's corpus. A statement about Wikimedia, and
                           the one that needs articles written.

Conflating the two would badly overstate the finding: most Ugandan OSM
features are untagged because nobody has done the linking, not because
Wikimedia is empty.
"""

import config

CLASS_LABELS = {
    'city': 'Cities',
    'town': 'Towns',
    'university': 'Universities',
    'hospital': 'Hospitals',
    'protected': 'Protected areas',
    'trunk': 'Trunk roads',
    'primary': 'Primary roads',
    'river': 'Rivers',
    'village': 'Villages',
    'school': 'Schools',
    'clinic': 'Clinics and health centres',
    'secondary': 'Secondary roads',
}
CLASS_ORDER = tuple(CLASS_LABELS)
LINEAR = ('trunk', 'primary', 'secondary', 'river')

# Classes listed in full on the page. The rest are sampled, because a table
# of every unmatched Ugandan village would be a twenty-megabyte page.
LIST_IN_FULL = ('city', 'town', 'university', 'protected', 'trunk', 'primary',
                'river', 'hospital')
SAMPLE = 60

STATE_LABELS = {
    'both': 'Both tags',
    'wikidata_only': 'Wikidata tag only',
    'wikipedia_only': 'Wikipedia tag only',
    'untagged': 'No Wikimedia tag',
}
VERDICT_LABELS = {
    'no_article_found': 'Nothing found at all',
    'item_no_article': 'Wikidata item, no article',
    'has_article': 'Described already',
}


def _has(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone() is not None


def load(conn):
    if not _has(conn, 'osm_features'):
        raise SystemExit('no osm_features table\n'
                         'run: python src_data/osm_features.py')
    matched = _has(conn, 'osm_matched')

    classes = []
    for key in CLASS_ORDER:
        states = dict(conn.execute("""
            SELECT link_state, COUNT(*) FROM osm_features
            WHERE feature_class = ? GROUP BY link_state""", (key,)))
        total = sum(states.values())
        if not total:
            continue
        untagged = states.get('untagged', 0)
        verdicts = {}
        if matched:
            verdicts = dict(conn.execute("""
                SELECT verdict, COUNT(*) FROM osm_matched
                WHERE feature_class = ? GROUP BY verdict""", (key,)))
        classes.append({
            'key': key,
            'label': CLASS_LABELS[key],
            'total': total,
            'untagged': untagged,
            'wikidataOnly': states.get('wikidata_only', 0),
            'wikipediaOnly': states.get('wikipedia_only', 0),
            'both': states.get('both', 0),
            'tagged': total - untagged,
            'taggedShare': 100.0 * (total - untagged) / total,
            'noArticle': verdicts.get('no_article_found', 0),
            'itemNoArticle': verdicts.get('item_no_article', 0),
            'described': verdicts.get('has_article', 0),
            'linear': key in LINEAR,
            'listed': key in LIST_IN_FULL,
        })

    total = sum(c['total'] for c in classes)
    untagged = sum(c['untagged'] for c in classes)
    no_article = sum(c['noArticle'] for c in classes)
    item_no_article = sum(c['itemNoArticle'] for c in classes)
    described = sum(c['described'] for c in classes)

    # Half-tagged features: 19,000-odd of them once Uganda's schools are
    # counted, so the page shows a sample and states the total.
    n_half = conn.execute("""
        SELECT COUNT(*) FROM osm_features
        WHERE link_state IN ('wikidata_only', 'wikipedia_only')"""
                          ).fetchone()[0]
    half = conn.execute("""
        SELECT feature_class, name, osm_type, osm_id, wikidata_qid,
               wikipedia_tag, link_state
        FROM osm_features
        WHERE link_state IN ('wikidata_only', 'wikipedia_only')
        ORDER BY feature_class, name LIMIT ?""", (SAMPLE,)).fetchall()

    # The worklist: unmatched features, the listed classes in full and the
    # bulk classes sampled, with the omitted count stated on the page.
    rows, omitted = [], 0
    if matched:
        for c in classes:
            limit = -1 if c['listed'] else SAMPLE
            query = """
                SELECT m.name, m.osm_type, m.osm_id, f.segments, f.latitude,
                       f.longitude
                FROM osm_matched m
                JOIN osm_features f
                  ON f.feature_class = m.feature_class
                 AND f.osm_type = m.osm_type AND f.osm_id = m.osm_id
                WHERE m.feature_class = ? AND m.verdict = 'no_article_found'
                ORDER BY f.segments DESC, m.name"""
            got = conn.execute(query if limit < 0 else query + ' LIMIT ?',
                               (c['key'],) if limit < 0
                               else (c['key'], limit)).fetchall()
            if limit >= 0:
                omitted += max(0, c['noArticle'] - len(got))
            for name, osm_type, osm_id, segments, lat, lon in got:
                rows.append({
                    'key': f'{osm_type}/{osm_id}',
                    'featureClass': c['key'],
                    'classLabel': c['label'],
                    'name': name,
                    'osmType': osm_type,
                    'osmId': osm_id,
                    'segments': segments,
                    'lat': lat,
                    'lon': lon,
                })

    return {
        'classes': classes,
        'total': total,
        'untagged': untagged,
        'tagged': total - untagged,
        'nClasses': len(classes),
        'noArticle': no_article,
        'itemNoArticle': item_no_article,
        'undescribed': no_article + item_no_article,
        'described': described,
        'matched': matched,
        'half': [{
            'featureClass': r[0],
            'classLabel': CLASS_LABELS.get(r[0], r[0]),
            'name': r[1], 'osmType': r[2], 'osmId': r[3],
            'qid': r[4] or '', 'wikipediaTag': r[5] or '', 'state': r[6],
        } for r in half],
        'nHalf': n_half,
        'worklist': rows,
        'omitted': omitted,
        'sampleSize': SAMPLE,
        'stateLabels': dict(STATE_LABELS),
        'verdictLabels': dict(VERDICT_LABELS),
    }
