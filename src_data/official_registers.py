# -*- coding: utf-8 -*-
"""Stage 11: Uganda's own official registers, checked against Wikimedia.

Two government sources, neither of which has an API:

  UBOS   the 2024 census sub-county profiles, an XLSX carrying the whole
         administrative hierarchy: 146 districts, 312 counties, 2,207
         sub-counties and 10,854 parishes. The level of each row is encoded
         in the cell style rather than the text, which is how they are told
         apart here.
  EC     the Electoral Commission's schedule of results for directly elected
         members of parliament, 2025/2026. A PDF, but one whose text runs are
         separated by a font marker, which makes the columns recoverable.

Both are parsed without new dependencies. An XLSX is a zip of XML, and this
PDF's content streams are Flate-coded with the text in ordinary string
literals, so zipfile, zlib and the re module are enough.

What the parsing cost is worth knowing. The 2021 edition of the same EC
results is not recoverable: its text is broken into single glyphs with no
reliable field marker, so a name comes out as "O CH ER O J I M BR ICK Y" with
no way to tell a kerning gap from a real space. Publishing mangled names of
real people would be worse than publishing nothing, so only the 2026 file is
used. A proper PDF library would lift that restriction.

Coverage is then decided locally. Every item in this project's corpus has at
least one Wikipedia article by construction, so a register entry whose name
matches a corpus label is described somewhere and one that does not is
reported as "no article found", which is a search result rather than a proof
of absence.

    python src_data/official_registers.py
"""

import csv
import html
import io
import os
import re
import time
import zipfile
import zlib

import config
import ug_utils

SCRIPT = 'official_registers'

UBOS_XLSX = ('https://www.ubos.org/wp-content/uploads/statistics/'
             'NPHC-2024-Subcounty-Profiles-Excel-Tables.xlsx')
EC_PDF = ('https://www.ec.or.ug/sites/default/files/Elec_results/'
          'SCHEDULE%20OF%20ELECTION%20RESULTS%20FOR%20DIRECTLY%20ELECTED%20'
          'MEMBERS%20OF%20PARLIAMENT%20GENERAL%20ELECTION%202025-2026.pdf')

OUT_UNITS = os.path.join(config.DATA_PATH, 'ug_register_units.csv')
OUT_GAP = os.path.join(config.DATA_PATH, 'ug_register_undocumented.csv')
OUT_MPS = os.path.join(config.DATA_PATH, 'ug_register_mps.csv')

# Cell style index to administrative level, in the UBOS workbook's Table1.
# Verified against the counts the census reports: 146, 312, 2,207, 10,854.
UBOS_LEVELS = {'21': 'district', '18': 'county', '19': 'subcounty',
               '22': 'parish'}
UBOS_HEADINGS = {'DISTRICT', 'COUNTY', 'SUBCOUNTY', 'PARISH', 'National'}

KIND_LABELS = {
    'district': 'Districts',
    'county': 'Counties',
    'subcounty': 'Sub-counties',
    'parish': 'Parishes',
    'constituency': 'Parliamentary constituencies',
    'mp': 'Members of Parliament',
}

# Words that carry no identifying weight when comparing a register name to a
# Wikipedia title.
GENERIC = {'the', 'and', 'district', 'county', 'sub', 'subcounty', 'parish',
           'town', 'council', 'ward', 'division', 'city', 'municipality',
           'constituency', 'north', 'south', 'east', 'west', 'central'}


CACHE_DIR = os.path.join(config.DATA_PATH, 'cache')
DOWNLOAD_TIMEOUT = 600
DOWNLOAD_RETRIES = 3


def fetch(url, label):
    """Download once and keep it.

    The census workbook is nine megabytes from a server that times out as
    often as it answers, so a cached copy is both faster on a re-run and
    considerably politer. Delete data/cache to force a fresh pull.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, url.rsplit('/', 1)[-1][:120])
    if os.path.exists(cached) and os.path.getsize(cached) > 1024:
        data = open(cached, 'rb').read()
        print(f'  {label}: {len(data):,} bytes from cache')
        return data

    session = ug_utils.get_session()
    for attempt in range(DOWNLOAD_RETRIES):
        print(f'  downloading {label} '
              f'(attempt {attempt + 1}/{DOWNLOAD_RETRIES}) ...',
              end=' ', flush=True)
        try:
            response = session.get(url, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            data = response.content
        except Exception as error:                     # noqa: BLE001
            print(f'{type(error).__name__}')
            time.sleep(10 * (attempt + 1))
            continue
        print(f'{len(data):,} bytes')
        with open(cached, 'wb') as handle:
            handle.write(data)
        return data
    raise SystemExit(f'could not download {label} from {url}')


# ---------------------------------------------------------------- UBOS xlsx
CELL = re.compile(r'<c r="A\d+"([^>]*)>(.*?)</c>', re.S)


def parse_ubos(data):
    """The administrative hierarchy, one row per unit, with its parents."""
    book = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    for si in re.findall(
            r'<si>(.*?)</si>',
            book.read('xl/sharedStrings.xml').decode('utf-8', 'replace'), re.S):
        shared.append(html.unescape(
            ''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))))

    sheet = book.read('xl/worksheets/sheet2.xml').decode('utf-8', 'replace')
    rows, parents = [], {}
    for row_xml in re.findall(r'<row[^>]*>(.*?)</row>', sheet, re.S):
        m = CELL.search(row_xml)
        if not m:
            continue
        attrs, body = m.group(1), m.group(2)
        style = re.search(r's="(\d+)"', attrs)
        kind = UBOS_LEVELS.get(style.group(1)) if style else None
        if kind is None:
            continue
        value = re.search(r'<v>(.*?)</v>', body, re.S)
        if value is None:
            continue
        if re.search(r't="s"', attrs):
            index = int(value.group(1))
            name = shared[index] if index < len(shared) else ''
        else:
            name = value.group(1)
        name = ' '.join(html.unescape(name).split())
        if not name or name in UBOS_HEADINGS:
            continue

        parents[kind] = name
        if kind == 'district':
            parents = {'district': name}
        rows.append({
            'source': 'UBOS',
            'kind': kind,
            'name': name,
            'district': parents.get('district', ''),
            'parent': (parents.get('subcounty') if kind == 'parish'
                       else parents.get('county') if kind == 'subcounty'
                       else parents.get('district') if kind == 'county'
                       else ''),
        })
    return rows


# ------------------------------------------------------------------- EC pdf
STREAM = re.compile(rb'stream\r?\n(.*?)endstream', re.S)
PAREN = re.compile(rb'\((?:\\.|[^\\()])*\)', re.S)
UNESCAPE = re.compile(rb'\\([()\\])')
CODE = re.compile(r'^\d{3}$')
VOTES = re.compile(r'^[\d,]+$')

# Collapsing single spaces occasionally swallows a real one, which shows up as
# an electoral-area word glued to what precedes it: BAMUNANIKACOUNTY. The
# suffixes are distinctive enough to put the space back safely.
GLUED = re.compile(r'(?<=[A-Z]{3})(COUNTY|DIVISION|MUNICIPALITY|CITY|WARD)\b')


def unglue(name):
    """Put back a space the glyph-level spacing swallowed."""
    return GLUED.sub(lambda m: ' ' + m.group(1), name)


def _pdf_fields(data):
    """Text runs, split on the marker this file puts between table cells."""
    pieces = []
    for raw_stream in STREAM.findall(data):
        try:
            raw = zlib.decompress(raw_stream)
        except Exception:                              # noqa: BLE001
            continue
        for m in PAREN.finditer(raw):
            pieces.append(UNESCAPE.sub(rb'\1', m.group(0)[1:-1])
                          .decode('latin-1', 'replace'))
    joined = ' '.join(pieces)

    out = []
    for field in joined.split('x-none'):
        # Glyphs are drawn one at a time, so a single space is kerning and
        # anything wider is a real gap.
        text = re.sub(r'(?<=\S) (?=\S)', '', field.strip())
        text = ' '.join(text.split())
        if text:
            out.append(text)
    return out


def parse_ec(data):
    """Constituencies and the candidate who won each."""
    fields = _pdf_fields(data)
    candidates, i = [], 0
    while i + 5 < len(fields):
        if CODE.match(fields[i]) and VOTES.match(fields[i + 5]):
            candidates.append({
                'district': unglue(fields[i + 1]),
                'constituency': unglue(fields[i + 2]),
                'candidate': fields[i + 3],
                'party': fields[i + 4],
                'votes': int(fields[i + 5].replace(',', '')),
            })
            i += 6
        else:
            i += 1

    winners = {}
    for row in candidates:
        best = winners.get(row['constituency'])
        if best is None or row['votes'] > best['votes']:
            winners[row['constituency']] = row

    rows = []
    for name, row in winners.items():
        rows.append({'source': 'EC', 'kind': 'constituency', 'name': name,
                     'district': row['district'], 'parent': row['district']})
        rows.append({'source': 'EC', 'kind': 'mp', 'name': row['candidate'],
                     'district': row['district'], 'parent': name,
                     'party': row['party'], 'votes': row['votes']})
    return rows, len(candidates)


# ------------------------------------------------------------------ matching
def tokens(name):
    cleaned = ''.join(c.lower() if c.isalnum() or c.isspace() else ' '
                      for c in (name or ''))
    return frozenset(t for t in cleaned.split()
                     if len(t) > 2 and t not in GENERIC)


def ingest(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'ingest', force) as st:
        if st.skip:
            return

        rows = parse_ubos(fetch(UBOS_XLSX, 'the UBOS census workbook'))
        counts = {}
        for row in rows:
            counts[row['kind']] = counts.get(row['kind'], 0) + 1
        print('  UBOS: ' + ', '.join(f'{v} {k}' for k, v in counts.items()))

        ec_rows, n_candidates = parse_ec(fetch(EC_PDF, 'the EC results'))
        cons = sum(1 for r in ec_rows if r['kind'] == 'constituency')
        print(f'  EC: {cons} constituencies and their winners, '
              f'from {n_candidates} candidate rows')
        rows.extend(ec_rows)

        conn.execute('DROP TABLE IF EXISTS register_entries')
        conn.execute("""CREATE TABLE register_entries (
            source text, kind text, name text, district text, parent text,
            party text, votes int, verdict text, matched_label text,
            PRIMARY KEY (source, kind, name, district, parent))""")
        conn.executemany(
            'INSERT OR REPLACE INTO register_entries '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            [(r['source'], r['kind'], r['name'], r['district'], r['parent'],
              r.get('party', ''), r.get('votes'), '', '') for r in rows])
        conn.commit()
        print(f'  stored {len(rows)} register entries')


def match(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'match', force) as st:
        if st.skip:
            return

        index = {}
        for label, in conn.execute(
                'SELECT label FROM ccc_items WHERE label IS NOT NULL'):
            key = tokens(label)
            if key:
                index.setdefault(key, label)
        print(f'  {len(index)} distinct corpus labels to match against')

        updates, tally = [], {}
        for source, kind, name, district, parent in conn.execute(
                'SELECT source, kind, name, district, parent '
                'FROM register_entries'):
            key = tokens(name)
            hit = index.get(key) if key else None
            verdict = 'has_article' if hit else 'no_article_found'
            tally[(kind, verdict)] = tally.get((kind, verdict), 0) + 1
            updates.append((verdict, hit or '', source, kind, name, district,
                            parent))
        conn.executemany("""
            UPDATE register_entries SET verdict = ?, matched_label = ?
            WHERE source = ? AND kind = ? AND name = ? AND district = ?
              AND parent = ?""", updates)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_register '
                     'ON register_entries(kind, verdict)')
        conn.commit()

        for kind in KIND_LABELS:
            have = tally.get((kind, 'has_article'), 0)
            miss = tally.get((kind, 'no_article_found'), 0)
            if have or miss:
                print(f'    {KIND_LABELS[kind]:30} {have:>6} described, '
                      f'{miss:>6} not found')


def export(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'export', force) as st:
        if st.skip:
            return
        header = ['source', 'kind', 'name', 'district', 'parent', 'party',
                  'votes', 'verdict', 'matched_label']

        def dump(path, where, params=()):
            rows = conn.execute(
                f'SELECT {", ".join(header)} FROM register_entries {where} '
                f'ORDER BY kind, district, name', params).fetchall()
            with open(path, 'w', encoding='utf-8', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerows(rows)
            print(f'    -> {os.path.basename(path)} ({len(rows)} rows)')

        dump(OUT_UNITS, '')
        dump(OUT_GAP, "WHERE verdict = 'no_article_found'")
        dump(OUT_MPS, "WHERE kind = 'mp'")


def main(force=False):
    conn = ug_utils.connect()
    ingest(conn, force)
    match(conn, force)
    export(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
