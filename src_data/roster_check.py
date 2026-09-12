# -*- coding: utf-8 -*-
"""Stage 7: check a roster of serving office holders against Wikimedia.

Every other stage in this project starts from Wikidata and asks what Wikipedia
is missing. That cannot answer "who is missing from Wikidata", because a woman
absent from Wikidata is invisible to a Wikidata query. The question has to be
approached from the other side: start from a roster of real appointments
gathered outside Wikimedia, then look each name up.

The rosters are the human-owned part. One file per cohort, listed in
config.ROSTERS, each carrying one row per person:

    name, office, organisation, sector, rank, source_url

source_url is mandatory: it is what makes a row checkable by someone else,
and what an editor needs before writing anything. Extend the file, re-run
this stage, and the page picks the additions up.

Each name is then resolved three ways:

    Wikidata   wbsearchentities over labels and aliases, then the candidates'
               P31/P27 to see whether they are even people
    enwiki     the search API
    lgwiki     the search API

Name order varies in Ugandan usage, so matching is on token overlap rather
than string equality, and the result is deliberately three-valued:

    absent          nothing found, so a candidate for creation
    possible_match  something with a similar name exists, needs a human look
    documented      a full-name match against a person

'absent' is a statement about a search, not proof that a person is missing.
Nobody should be added to Wikimedia on the strength of this table alone.
"""

import csv
import os
import time

import config
import ug_utils

SCRIPT = 'roster_check'

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
HUMAN = 'Q5'

# Honorifics and post-nominals to drop before comparing names.
TITLES = {'ms', 'mrs', 'miss', 'mr', 'dr', 'prof', 'professor', 'eng',
          'hon', 'rt', 'sen', 'amb', 'ambassador', 'the', 'sc'}

# Ranks in descending seniority, so the page can lead with the biggest offices.
RANK_ORDER = ('chief', 'executive', 'senior')


def roster_path(cohort):
    return os.path.join(config.DATA_PATH, config.roster_file(cohort))


def ordered_tokens(name):
    """Name tokens in order: lowercased, de-punctuated, titles removed."""
    cleaned = ''.join(c.lower() if c.isalnum() or c.isspace() else ' '
                      for c in (name or ''))
    return [t for t in cleaned.split() if len(t) > 2 and t not in TITLES]


def tokens(name):
    """The same tokens as a set, for overlap comparisons."""
    return set(ordered_tokens(name))


def name_variants(name):
    """Search strings to try for one roster name.

    wbsearchentities is a prefix search, so "Catherine Bitarakwate
    Musingwiire" does not find the item labelled "Catherine Bitarakwate":
    the query is longer than the label. Ugandan usage also reorders given
    and family names freely. Both are handled by asking several ways.
    """
    parts = ordered_tokens(name)
    if not parts:
        return []
    tries = [' '.join(parts)]
    if len(parts) >= 3:
        tries += [f'{parts[0]} {parts[-1]}', f'{parts[0]} {parts[1]}',
                  f'{parts[-2]} {parts[-1]}']
    elif len(parts) == 2:
        tries.append(f'{parts[1]} {parts[0]}')
    if len(parts) > 1:
        tries.append(parts[-1])
    seen, out = set(), []
    for candidate in tries:
        if candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out[:5]


def read_roster(cohort):
    path = roster_path(cohort)
    if not os.path.exists(path):
        raise SystemExit(
            f'no roster at {path}\n'
            'This stage needs a roster of real appointments gathered outside '
            'Wikimedia. See the module docstring for the column format.')
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get('name') or '').strip()]
    for row in rows:
        for key in ('name', 'office', 'organisation', 'sector', 'rank',
                    'source_url'):
            row[key] = (row.get(key) or '').strip()
    return rows


def _api(session, url, params, timeout=60):
    """One MediaWiki API call, with the retry the other stages use."""
    params = dict(params, format='json')
    for attempt in range(4):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code in (429, 503):
                time.sleep(float(response.headers.get('Retry-After', 0))
                           or 2 ** attempt)
                continue
            response.raise_for_status()
            return response.json()
        except Exception:                              # noqa: BLE001
            time.sleep(2 ** attempt)
    return {}


def wikidata_candidates(session, name):
    """Items whose label or alias looks like this name, over all variants."""
    found = {}
    for variant in name_variants(name):
        payload = _api(session, WIKIDATA_API,
                       {'action': 'wbsearchentities', 'search': variant,
                        'language': 'en', 'uselang': 'en', 'type': 'item',
                        'limit': 15})
        for hit in payload.get('search', []):
            found.setdefault(hit['id'], {
                'qid': hit['id'],
                'label': hit.get('label', ''),
                'description': hit.get('description', '')})
        time.sleep(0.15)
    return list(found.values())


def describe_items(session, qids):
    """P31 and P27 for candidate items, so non-people can be discarded."""
    out = {}
    for i in range(0, len(qids), 40):
        batch = qids[i:i + 40]
        payload = _api(session, WIKIDATA_API,
                       {'action': 'wbgetentities', 'ids': '|'.join(batch),
                        'props': 'claims'})
        for qid, entity in (payload.get('entities') or {}).items():
            claims = entity.get('claims') or {}

            def values(prop):
                found = []
                for statement in claims.get(prop, []):
                    value = (statement.get('mainsnak', {})
                             .get('datavalue', {}).get('value') or {})
                    if isinstance(value, dict) and value.get('id'):
                        found.append(value['id'])
                return found

            kinds = values('P31')
            # Only rule a candidate out when it says outright that it is
            # something other than a person. A stub with no P31 is exactly
            # the kind of thin item this page expects to find.
            out[qid] = {'not_a_person': bool(kinds) and HUMAN not in kinds,
                        'ugandan': config.UGANDA in values('P27')}
        time.sleep(0.2)
    return out


def wiki_search(session, languagecode, name):
    """Article titles on one Wikipedia that match the name."""
    payload = _api(session, f'https://{languagecode}.wikipedia.org/w/api.php',
                   {'action': 'query', 'list': 'search',
                    'srsearch': f'"{name}"', 'srlimit': 8,
                    'srnamespace': 0, 'srprop': ''})
    return [hit['title']
            for hit in payload.get('query', {}).get('search', [])]


def classify(name, candidates, described, en_titles, lg_titles):
    """Four-valued status, plus whatever it matched on.

        absent          no item and no article: a candidate for creation
        possible_match  a similar name exists and a human must judge it
        wikidata_only   an item covers the name, but no article does
        documented      an article covers the name

    wikidata_only is kept separate because the two need different work: an
    item exists to hang sources on, so the article is the missing piece.
    """
    want = tokens(name)
    if not want:
        return 'absent', '', '', ''

    en_hit = _first_full(want, en_titles)
    lg_hit = _first_full(want, lg_titles)

    exact_qid, partial_qid = '', ''
    for candidate in candidates:
        if described.get(candidate['qid'], {}).get('not_a_person'):
            continue
        have = tokens(candidate['label'])
        if want <= have and not exact_qid:
            exact_qid = candidate['qid']
        elif len(want & have) >= 2 and not partial_qid:
            partial_qid = candidate['qid']

    if en_hit or lg_hit:
        return 'documented', exact_qid or partial_qid, en_hit, lg_hit
    if exact_qid:
        return 'wikidata_only', exact_qid, '', ''
    if partial_qid:
        return 'possible_match', partial_qid, '', ''
    # A partial title match is worth a human look but is not documentation.
    for title in en_titles + lg_titles:
        if len(want & tokens(title)) >= 2:
            return 'possible_match', '', '', ''
    return 'absent', '', '', ''


def _first_full(want, titles):
    """The first title that accounts for every token of the roster name."""
    for title in titles:
        if want <= tokens(title):
            return title
    return ''


def check_roster(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'check_roster', force) as st:
        if st.skip:
            return

        session = ug_utils.get_session()
        conn.execute('DROP TABLE IF EXISTS roster_status')
        conn.execute("""CREATE TABLE roster_status (
            cohort text, name text, office text, organisation text,
            sector text, rank text, source_url text, status text,
            wikidata_qid text, en_title text, lg_title text,
            PRIMARY KEY (cohort, name, organisation, office))""")

        for cohort, filename, _label in config.ROSTERS:
            try:
                roster = read_roster(cohort)
            except SystemExit as reason:
                print(f'  {cohort}: skipped, {reason}')
                continue
            print(f'  {cohort}: {len(roster)} names from {filename}')

            rows = []
            for i, entry in enumerate(roster, 1):
                name = entry['name']
                candidates = wikidata_candidates(session, name)
                described = describe_items(
                    session, [c['qid'] for c in candidates]) if candidates else {}
                en_titles = wiki_search(session, config.REFERENCE_WIKI, name)
                lg_titles = wiki_search(session, 'lg', name)
                status, qid, en_title, lg_title = classify(
                    name, candidates, described, en_titles, lg_titles)
                rows.append((cohort, name, entry['office'],
                             entry['organisation'], entry['sector'],
                             entry['rank'], entry['source_url'], status, qid,
                             en_title, lg_title))
                print(f'    {i:>3}/{len(roster)} {status:<15} {name}')
                time.sleep(0.3)

            conn.executemany(
                'INSERT OR REPLACE INTO roster_status '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows)
            conn.commit()

            tally = {}
            for row in rows:
                tally[row[7]] = tally.get(row[7], 0) + 1
            print('    ' + ' | '.join(f'{k}: {v}'
                                      for k, v in sorted(tally.items())))


def export_roster(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'export_roster', force) as st:
        if st.skip:
            return

        header = ['name', 'office', 'organisation', 'sector', 'rank',
                  'source_url', 'status', 'wikidata_qid', 'en_title',
                  'lg_title']
        rank_rank = {rank: i for i, rank in enumerate(RANK_ORDER)}

        def dump(cohort, where, name):
            rows = conn.execute(f"""
                SELECT name, office, organisation, sector, rank, source_url,
                       status, wikidata_qid, en_title, lg_title
                FROM roster_status WHERE cohort = ? {where}""",
                                (cohort,)).fetchall()
            rows.sort(key=lambda r: (rank_rank.get(r[4], 9), r[2], r[0]))
            path = os.path.join(config.DATA_PATH, name + '.csv')
            with open(path, 'w', encoding='utf-8', newline='') as fh:
                writer = csv.writer(fh)
                writer.writerow(header)
                writer.writerows(rows)
            print(f'    -> {name}.csv ({len(rows)} rows)')

        for cohort, _filename, _label in config.ROSTERS:
            dump(cohort, '', f'ug_{cohort}_offices_roster')
            dump(cohort, "AND status = 'absent'",
                 f'ug_{cohort}_offices_undocumented')
            dump(cohort, "AND status = 'possible_match'",
                 f'ug_{cohort}_offices_to_verify')


def main(force=False):
    conn = ug_utils.connect()
    check_roster(conn, force)
    export_roster(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
