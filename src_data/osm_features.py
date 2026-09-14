# -*- coding: utf-8 -*-
"""Stage 10: what OpenStreetMap knows about Uganda that Wikimedia does not.

OSM is the third map of Uganda, after Wikidata and Wikipedia, and it is by far
the most complete on the ground: tens of thousands of named villages, schools
and roads that no encyclopedia has ever described. Features can carry a
`wikidata` and a `wikipedia` tag, so the overlap is machine-readable, and the
four states of that overlap are exactly the question here:

    both            cross-referenced in both directions
    wikidata_only   tagged with an item, no article tagged
    wikipedia_only  tagged with an article, no item tagged
    untagged        no Wikimedia cross-reference at all

One thing this stage must not claim. **An untagged OSM feature is not proof
that Wikimedia has nothing about it.** It means no OSM contributor has made
the link, which is a statement about OSM's tagging rather than about
Wikidata's contents. Uganda's OSM data is largely imported and mapped by
people who never touch the wiki side, so untagged is the overwhelming default.

So the stage does two different jobs, and the page keeps them apart:

  the tagging gap   counted over every named feature, honestly labelled as a
                    cross-reference gap
  the real gap      every untagged feature is matched against this
                    project's corpus by position and name, which settles
                    whether any Wikipedia describes that place

Roads arrive as many segments per road, so linear features are grouped by
name and carry a segment count. That count is a rough proxy for length, not a
measurement: it depends on how finely a road happens to be split.

    python src_data/osm_features.py
"""

import csv
import os
import time

import config
import ug_utils
from ug_utils import binding_value, qid_from_uri

SCRIPT = 'osm_features'

# Several public Overpass instances, tried in turn. The main one returned a
# run of 504s on queries as small as "named towns in Uganda" while this stage
# was being written, and a country-wide village query is far heavier than
# that, so falling back matters more here than politeness alone.
# The main instance first: it was the only one answering when this was
# written. The others stay as fallbacks rather than being removed, since which
# instance is healthy changes by the day.
OVERPASS_MIRRORS = (
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
)
OUT_FILE = os.path.join(config.DATA_PATH, 'ug_osm_features.csv')
GAP_FILE = os.path.join(config.DATA_PATH, 'ug_osm_undocumented.csv')

# Be a good citizen: Overpass is donated infrastructure and these are heavy
# country-wide area queries.
#
# Timeouts measured rather than guessed. A health check found the main
# instance answering "named cities in Uganda" in 15 seconds while both
# mirrors returned 504 after 52 and 62 seconds, so a long client timeout
# spends minutes failing over to instances that are down. The client gives up
# quickly and moves on; the declared server timeout is generous only for the
# classes that need it.
OVERPASS_PAUSE = 20
CLIENT_TIMEOUT = 90         # per mirror attempt, so failover is quick
CLIENT_TIMEOUT_BULK = 600   # 61,000 villages legitimately take a while
SERVER_TIMEOUT = 180
SERVER_TIMEOUT_BULK = 550

# key, label, overpass selector, shape, tier
#
# shape 'element' keeps one row per OSM object; 'linear' groups segments by
# name, because a road is split into dozens of ways.
#
# tier 'major' is checked against Wikidata name by name. The bulk classes are
# too large for that in one cycle and are reported as a tagging gap only:
# Uganda has 61,061 named villages and 2,445 named hospitals in OSM, measured
# before this list was written.
FEATURE_CLASSES = (
    ('city', 'Cities', 'node["place"="city"]["name"]', 'element', 'major'),
    ('town', 'Towns', 'node["place"="town"]["name"]', 'element', 'major'),
    ('university', 'Universities',
     'nwr["amenity"="university"]["name"]', 'element', 'major'),
    ('hospital', 'Hospitals',
     'nwr["amenity"="hospital"]["name"]', 'element', 'bulk'),
    ('protected', 'Protected areas',
     'nwr["boundary"="protected_area"]["name"]', 'element', 'major'),
    ('trunk', 'Trunk roads',
     'way["highway"="trunk"]["name"]', 'linear', 'major'),
    ('primary', 'Primary roads',
     'way["highway"="primary"]["name"]', 'linear', 'major'),
    ('river', 'Rivers', 'way["waterway"="river"]["name"]', 'linear', 'major'),
    ('village', 'Villages',
     'node["place"="village"]["name"]', 'element', 'bulk'),
    ('school', 'Schools',
     'nwr["amenity"="school"]["name"]', 'element', 'bulk'),
    ('clinic', 'Clinics and health centres',
     'nwr["amenity"="clinic"]["name"]', 'element', 'bulk'),
    ('secondary', 'Secondary roads',
     'way["highway"="secondary"]["name"]', 'linear', 'bulk'),
)

AREA = 'area["ISO3166-1"="UG"][admin_level=2]->.ug;'

# Uganda's bounding box, for splitting a query that is too heavy to answer
# whole. The 61,061 named villages defeated every mirror as one request; in
# sixteen tiles each piece is a few thousand nodes and goes through.
UG_BBOX = (-1.50, 29.55, 4.25, 35.05)     # south, west, north, east
TILES = 4


def overpass(query, client_timeout=CLIENT_TIMEOUT, rounds=2):
    """One Overpass call, trying each mirror before backing off and retrying.

    Returns the parsed payload, or None when every mirror has refused.
    """
    session = ug_utils.get_session()
    for round_number in range(rounds):
        for endpoint in OVERPASS_MIRRORS:
            host = endpoint.split('/')[2]
            try:
                response = session.post(endpoint, data={'data': query},
                                        timeout=client_timeout)
            except Exception as error:                 # noqa: BLE001
                print(f'    {host}: {type(error).__name__}')
                continue
            if response.status_code in (429, 504):
                print(f'    {host}: busy ({response.status_code})')
                continue
            if response.status_code >= 400:
                print(f'    {host}: HTTP {response.status_code}')
                continue
            try:
                payload = response.json()
            except Exception:                          # noqa: BLE001
                print(f'    {host}: unparseable response')
                continue
            time.sleep(OVERPASS_PAUSE)
            return payload
        if round_number + 1 < rounds:
            wait = 90
            print(f'    every mirror busy, waiting {wait}s')
            time.sleep(wait)
    return None


def link_state(tags):
    """Which of the four cross-reference states a feature is in."""
    qid = (tags.get('wikidata') or '').strip()
    article = (tags.get('wikipedia') or '').strip()
    if qid and article:
        return 'both', qid, article
    if qid:
        return 'wikidata_only', qid, ''
    if article:
        return 'wikipedia_only', '', article
    return 'untagged', '', ''


def _collect(payload, shape, rows):
    """Fold one Overpass payload into the row accumulator."""
    for element in payload.get('elements', []):
        tags = element.get('tags') or {}
        name = (tags.get('name') or '').strip()
        if not name:
            continue
        state, qid, article = link_state(tags)

        # A node carries lat/lon directly; a way or relation carries the
        # centre that `out center` adds.
        centre = element.get('center') or {}
        lat = element.get('lat', centre.get('lat'))
        lon = element.get('lon', centre.get('lon'))

        if shape == 'linear':
            # One row per road, not per way: a road is many segments and the
            # tags may sit on only some of them. Segments are counted by way
            # id so a tiled fetch cannot count the same way twice.
            row = rows.setdefault(name, {
                'name': name, 'osm_type': 'route', 'osm_id': element['id'],
                'segments': set(), 'wikidata_qid': '', 'wikipedia_tag': '',
                'lat': lat, 'lon': lon,
            })
            row['segments'].add(element['id'])
            row['wikidata_qid'] = row['wikidata_qid'] or qid
            row['wikipedia_tag'] = row['wikipedia_tag'] or article
        else:
            rows[(element['type'], element['id'])] = {
                'name': name, 'osm_type': element['type'],
                'osm_id': element['id'], 'segments': 1,
                'wikidata_qid': qid, 'wikipedia_tag': article,
                'lat': lat, 'lon': lon,
            }


def _tiles(n=TILES):
    south, west, north, east = UG_BBOX
    dy = (north - south) / n
    dx = (east - west) / n
    for i in range(n):
        for j in range(n):
            yield (south + i * dy, west + j * dx,
                   south + (i + 1) * dy, west + (j + 1) * dx)


def fetch_class(key, selector, shape, tier):
    """Every named feature of one class, with its wiki tags and centre.

    Tried whole first. A class that defeats every mirror is retried tile by
    tile over Uganda's bounding box, which is what makes the village layer
    reachable at all.
    """
    bulk = tier == 'bulk'
    server = SERVER_TIMEOUT_BULK if bulk else SERVER_TIMEOUT
    client = CLIENT_TIMEOUT_BULK if bulk else CLIENT_TIMEOUT

    rows = {}
    query = (f'[out:json][timeout:{server}];\n{AREA}\n'
             f'{selector}(area.ug);\nout tags center;')
    payload = overpass(query, client_timeout=client)

    if payload is not None:
        _collect(payload, shape, rows)
    else:
        print(f'\n    whole-country query failed, retrying in '
              f'{TILES * TILES} tiles')
        got = 0
        for south, west, north, east in _tiles():
            bbox = f'{south:.4f},{west:.4f},{north:.4f},{east:.4f}'
            tiled = (f'[out:json][timeout:{SERVER_TIMEOUT}];\n'
                     f'{selector}({bbox});\nout tags center;')
            piece = overpass(tiled, client_timeout=CLIENT_TIMEOUT)
            if piece is None:
                print(f'      tile {bbox} failed, skipped')
                continue
            _collect(piece, shape, rows)
            got += 1
        print(f'      {got}/{TILES * TILES} tiles returned', end='; ')
        if not rows:
            return []

    out = []
    for row in rows.values():
        if isinstance(row['segments'], set):
            row['segments'] = len(row['segments'])
        state, _qid, _article = link_state({
            'wikidata': row['wikidata_qid'],
            'wikipedia': row['wikipedia_tag']})
        row['link_state'] = state
        out.append(row)
    return out


def fetch_features(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'fetch_features', force) as st:
        if st.skip:
            return

        conn.execute("""CREATE TABLE IF NOT EXISTS osm_features (
            feature_class text, name text, osm_type text, osm_id int,
            segments int, wikidata_qid text, wikipedia_tag text,
            link_state text, latitude real, longitude real,
            PRIMARY KEY (feature_class, osm_type, osm_id))""")

        for key, label, selector, shape, tier in FEATURE_CLASSES:
            have = conn.execute(
                'SELECT COUNT(*) FROM osm_features WHERE feature_class=?',
                (key,)).fetchone()[0]
            if have and not force:
                # Each class is its own checkpoint. One country-wide query can
                # take minutes, so a later failure must not throw away the
                # classes that already landed.
                print(f'  {label}: {have} already fetched, skipping')
                continue
            conn.execute('DELETE FROM osm_features WHERE feature_class=?',
                         (key,))
            print(f'  {label} ...', end=' ', flush=True)
            rows = fetch_class(key, selector, shape, tier)
            conn.executemany(
                'INSERT OR REPLACE INTO osm_features '
                'VALUES (?,?,?,?,?,?,?,?,?,?)',
                [(key, r['name'], r['osm_type'], r['osm_id'], r['segments'],
                  r['wikidata_qid'], r['wikipedia_tag'], r['link_state'],
                  r['lat'], r['lon'])
                 for r in rows])
            conn.commit()
            states = {}
            for r in rows:
                states[r['link_state']] = states.get(r['link_state'], 0) + 1
            print(f'{len(rows)} named, ' + ', '.join(
                f'{v} {k}' for k, v in sorted(states.items())))

        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_osm_class '
            'ON osm_features(feature_class, link_state)')
        conn.commit()


# ---------------------------------------------------------------------------
# Does Wikimedia actually describe these places?
# ---------------------------------------------------------------------------
#
# Not by name alone. A first attempt asked Wikidata for each name together
# with country=Uganda and found almost nothing, for two reasons that both
# matter: "Gulu" also names places in Indonesia and Nigeria, and Gulu in
# Uganda carries no P17 statement at all, so a country filter rejects the very
# item it should find.
#
# So the match is geographic. Every item in this project's corpus has at
# least one Wikipedia article by construction, and 6,633 of them carry
# coordinates. An OSM feature within MATCH_KM of such an item, sharing a name
# token with it, is described somewhere. Anything else is reported as "no
# article found nearby", which is a search result and not a proof of absence.

MATCH_KM = 2.0
CELL = 0.05          # degrees, the spatial index bucket
KM_PER_DEG = 111.32

# Words that carry no identifying weight in a Ugandan place or facility name.
GENERIC = {'the', 'and', 'for', 'school', 'primary', 'secondary', 'college',
           'hospital', 'centre', 'center', 'health', 'road', 'river',
           'village', 'town', 'city', 'university', 'clinic', 'ltd',
           'sub', 'county', 'district', 'parish', 'trading'}


def _name_tokens(name):
    cleaned = ''.join(c.lower() if c.isalnum() or c.isspace() else ' '
                      for c in (name or ''))
    return {t for t in cleaned.split() if len(t) > 2 and t not in GENERIC}


def _distance_km(lat1, lon1, lat2, lon2):
    """Equirectangular approximation, ample over a couple of kilometres."""
    import math
    dlat = (lat2 - lat1) * KM_PER_DEG
    dlon = ((lon2 - lon1) * KM_PER_DEG
            * math.cos(math.radians((lat1 + lat2) / 2)))
    return math.hypot(dlat, dlon)


def match_corpus(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'match_corpus', force) as st:
        if st.skip:
            return

        corpus = conn.execute("""
            SELECT qitem, label, latitude, longitude
            FROM ccc_items
            WHERE latitude IS NOT NULL AND label IS NOT NULL""").fetchall()
        print(f'  {len(corpus)} corpus items carry coordinates and a label')

        grid = {}
        for qitem, label, lat, lon in corpus:
            cell = (int(lat / CELL), int(lon / CELL))
            grid.setdefault(cell, []).append(
                (qitem, label, lat, lon, _name_tokens(label)))

        features = conn.execute("""
            SELECT feature_class, osm_type, osm_id, name, latitude, longitude
            FROM osm_features
            WHERE link_state = 'untagged' AND latitude IS NOT NULL""").fetchall()
        print(f'  matching {len(features)} untagged features against them')

        conn.execute('DROP TABLE IF EXISTS osm_matched')
        conn.execute("""CREATE TABLE osm_matched (
            feature_class text, osm_type text, osm_id int, name text,
            verdict text, qitem text, matched_label text, distance_km real,
            PRIMARY KEY (feature_class, osm_type, osm_id))""")

        # A wikidata tag says an item exists, not that anyone has written
        # about it. Every corpus item has at least one article by
        # construction, so a tagged QID absent from the corpus is an item with
        # no article in any language: Uganda's schools were imported into OSM
        # with item references en masse, and almost none of them are written
        # up anywhere.
        in_corpus = {q for (q,) in conn.execute(
            'SELECT qitem FROM ccc_items')}
        tagged = conn.execute("""
            SELECT feature_class, osm_type, osm_id, name, wikidata_qid
            FROM osm_features
            WHERE wikidata_qid != '' """).fetchall()
        tagged_rows = [
            (key, osm_type, osm_id, name,
             'has_article' if qid in in_corpus else 'item_no_article',
             qid, '', None)
            for key, osm_type, osm_id, name, qid in tagged]

        out, tally = [], {}
        span = int(MATCH_KM / KM_PER_DEG / CELL) + 1
        for key, osm_type, osm_id, name, lat, lon in features:
            wanted = _name_tokens(name)
            cell = (int(lat / CELL), int(lon / CELL))
            best = None
            if wanted:
                for dy in range(-span, span + 1):
                    for dx in range(-span, span + 1):
                        for item in grid.get((cell[0] + dy, cell[1] + dx), ()):
                            qitem, label, ilat, ilon, tokens = item
                            if not (wanted & tokens):
                                continue
                            km = _distance_km(lat, lon, ilat, ilon)
                            if km <= MATCH_KM and (best is None
                                                   or km < best[2]):
                                best = (qitem, label, km)
            verdict = 'has_article' if best else 'no_article_found'
            tally[verdict] = tally.get(verdict, 0) + 1
            out.append((key, osm_type, osm_id, name, verdict,
                        best[0] if best else '', best[1] if best else '',
                        round(best[2], 2) if best else None))

        for row in tagged_rows:
            tally[row[4]] = tally.get(row[4], 0) + 1
        conn.executemany(
            'INSERT OR REPLACE INTO osm_matched VALUES (?,?,?,?,?,?,?,?)',
            out + tagged_rows)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_osm_matched '
                     'ON osm_matched(feature_class, verdict)')
        conn.commit()
        print('  ' + ' | '.join(f'{k}: {v}' for k, v in sorted(tally.items())))


def export(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'export', force) as st:
        if st.skip:
            return
        labels = {key: label for key, label, _s, _sh, _t in FEATURE_CLASSES}

        def dump(path, where, params=()):
            rows = conn.execute(f"""
                SELECT feature_class, name, osm_type, osm_id, segments,
                       wikidata_qid, wikipedia_tag, link_state
                FROM osm_features {where}
                ORDER BY feature_class, name""", params).fetchall()
            with open(path, 'w', encoding='utf-8', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(['feature_class', 'class_label', 'name',
                                 'osm_type', 'osm_id', 'segments',
                                 'wikidata_qid', 'wikipedia_tag',
                                 'link_state', 'osm_url'])
                for r in rows:
                    # 'route' is this pipeline's own label for a named
                    # linear feature assembled from many ways; osm_id is
                    # one of those ways, and openstreetmap.org serves only
                    # node, way and relation, so /route/ would 404.
                    kind = 'way' if r[2] == 'route' else r[2]
                    url = f'https://www.openstreetmap.org/{kind}/{r[3]}'
                    writer.writerow([r[0], labels.get(r[0], r[0]), r[1], r[2],
                                     r[3], r[4], r[5], r[6], r[7], url])
            print(f'    -> {os.path.basename(path)} ({len(rows)} rows)')

        dump(OUT_FILE, '')
        dump(GAP_FILE, "WHERE link_state = 'untagged'")


def main(force=False):
    conn = ug_utils.connect()
    fetch_features(conn, force)
    match_corpus(conn, force)
    export(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
