# -*- coding: utf-8 -*-
"""Render the roster of serving office holders against their Wikimedia record.

The one page here that does not start from Wikimedia. Every other page asks
what Wikipedia is missing relative to Wikidata; this one starts from a roster
of real appointments gathered outside Wikimedia altogether, because a woman
who is in neither Wikidata nor Wikipedia cannot be found by querying either.

Reads the roster_status table that src_data/roster_check.py fills,
for one cohort at a time. The cohorts are listed in config.ROSTERS;
the women's and men's pages are the same code over different rows.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402


STATUS_LABELS = {
    'absent': 'Nothing on Wikimedia',
    'possible_match': 'Similar name, needs checking',
    'wikidata_only': 'Wikidata item, no article',
    'documented': 'Has an article',
}
STATUS_ORDER = ('absent', 'wikidata_only', 'possible_match', 'documented')

RANK_LABELS = {
    'chief': 'Heads the institution',
    'executive': 'Executive or board',
    'senior': 'Senior management',
}
RANK_ORDER = ('chief', 'executive', 'senior')

SECTOR_LABELS = {
    'government': 'Government',
    'military': 'Armed forces',
    'police': 'Police',
    'judiciary': 'Judiciary',
    'parastatal': 'State-owned enterprise',
    'telecom': 'Telecom',
    'technology': 'Technology',
    'private': 'Private sector',
    'media': 'Media',
    'religion': 'Faith leadership',
    'sport': 'Sport',
    'ngo': 'NGO and multilateral',
}


def load(conn, cohort='women'):
    rank_rank = {rank: i for i, rank in enumerate(RANK_ORDER)}
    status_rank = {status: i for i, status in enumerate(STATUS_ORDER)}

    people = []
    for (name, office, organisation, sector, rank, source_url,
         status, qid, en_title, lg_title) in conn.execute("""
            SELECT name, office, organisation, sector, rank, source_url,
                   status, wikidata_qid, en_title, lg_title
            FROM roster_status WHERE cohort = ?""", (cohort,)):
        people.append({
            'name': name, 'office': office, 'organisation': organisation,
            'sector': sector, 'rank': rank, 'source_url': source_url,
            'status': status, 'qid': qid,
            'en_title': en_title, 'lg_title': lg_title,
        })

    # Nothing-on-Wikimedia first, and within that the biggest offices first:
    # that is the order in which the list is worth working through.
    people.sort(key=lambda p: (status_rank.get(p['status'], 9),
                               rank_rank.get(p['rank'], 9),
                               p['organisation'], p['name']))

    count = lambda pred: sum(1 for p in people if pred(p))
    absent = [p for p in people if p['status'] == 'absent']

    by_sector = []
    for sector in SECTOR_LABELS:
        rows = [p for p in people if p['sector'] == sector]
        if rows:
            by_sector.append({
                'sector': sector,
                'label': SECTOR_LABELS[sector],
                'total': len(rows),
                'absent': sum(1 for p in rows if p['status'] == 'absent'),
            })

    by_rank = []
    for rank in RANK_ORDER:
        rows = [p for p in people if p['rank'] == rank]
        if rows:
            by_rank.append({
                'rank': rank, 'label': RANK_LABELS[rank], 'total': len(rows),
                'absent': sum(1 for p in rows if p['status'] == 'absent'),
            })

    return {
        'people': people,
        'total': len(people),
        'absent': absent,
        'n_absent': len(absent),
        'n_wikidata_only': count(lambda p: p['status'] == 'wikidata_only'),
        'n_possible': count(lambda p: p['status'] == 'possible_match'),
        'n_documented': count(lambda p: p['status'] == 'documented'),
        'organisations': len({p['organisation'] for p in people}),
        'by_sector': by_sector,
        'by_rank': by_rank,
        'top_absent': [p for p in absent if p['rank'] == 'chief'],
        'cohort': cohort,
    }
