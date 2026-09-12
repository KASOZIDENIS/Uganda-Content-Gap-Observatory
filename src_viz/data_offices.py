# -*- coding: utf-8 -*-
"""Render the Ugandan women in public office and their article coverage.

Three groups, which are what the page is organised around:

  with an article      covered somewhere, in some language
  no article anywhere  she held office and Wikipedia has no page for her
  needs Luganda        an English article exists, a Luganda one does not

Everything comes from the office_women / office_positions / office_summary
tables that src_data/office_analysis.py fills, so this reads only SQLite and
loads neither pandas nor requests.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402


# Article status, most-work-first. 'translate' is a subset of having an
# article, so the three groups the page leads with are derived rather than
# taken straight from these keys.
STATUS_LABELS = {
    'none': 'No article anywhere',
    'translate': 'Needs Luganda translation',
    'other_lang': 'Another language only',
    'lg_only': 'Luganda only',
    'both': 'English and Luganda',
}
STATUS_ORDER = ('none', 'translate', 'other_lang', 'lg_only', 'both')

# The three groups, as (key, label, what the work is).
GROUPS = (
    ('none', 'No article anywhere', 'write from sources'),
    ('translate', 'Needs translating to Luganda',
     'translate the existing English article'),
    ('has', 'Already has an article', 'nothing to do here'),
)


def status_of(sitelinks, en_title, lg_title):
    if not sitelinks:
        return 'none'
    if en_title and not lg_title:
        return 'translate'
    if en_title and lg_title:
        return 'both'
    if lg_title:
        return 'lg_only'
    return 'other_lang'


def load(conn):
    held = {}
    for qitem, name in conn.execute(
            'SELECT qitem, position_label FROM office_positions ORDER BY position_label'):
        held.setdefault(qitem, []).append(name)

    tier_rank = {tier: i for i, tier in enumerate(config.BIG_OFFICE_TIERS)}
    tier_rank['other'] = len(tier_rank)

    women = []
    for (qitem, label, description, sitelinks, statements,
         en_title, lg_title, citizen, tier) in conn.execute("""
            SELECT qitem, label, description, sitelink_count, statements,
                   en_title, lg_title, ugandan_citizen, tier
            FROM office_women"""):
        women.append({
            'qitem': qitem,
            'label': label,
            'description': description,
            'sitelinks': sitelinks,
            'statements': statements,
            'en_title': en_title,
            'lg_title': lg_title,
            'citizen': bool(citizen),
            'tier': tier,
            'positions': sorted(set(held.get(qitem, []))),
            'status': status_of(sitelinks, en_title, lg_title),
        })

    # Most senior office first, then whoever Wikidata already documents best,
    # because that is the order someone writing the missing articles wants.
    women.sort(key=lambda w: (tier_rank[w['tier']], -w['statements'],
                              (w['label'] or '')))

    office = [w for w in women if w['tier'] != 'other']
    counted = lambda rows, pred: sum(1 for w in rows if pred(w))

    tiers = []
    for tier in config.BIG_OFFICE_TIERS:
        rows = [w for w in office if w['tier'] == tier]
        if not rows:
            continue
        with_article = counted(rows, lambda w: w['sitelinks'] > 0)
        tiers.append({
            'tier': tier,
            'label': config.TIER_LABELS[tier],
            'holders': len(rows),
            'with_article': with_article,
            'none': len(rows) - with_article,
            'translate': counted(rows, lambda w: w['status'] == 'translate'),
            'covered': 100.0 * with_article / len(rows),
        })

    worst = conn.execute("""
        SELECT position_label, tier, holders, with_article, no_article
        FROM office_summary WHERE no_article > 0 AND tier != 'other'
        ORDER BY no_article DESC, holders DESC LIMIT 12""").fetchall()

    # A non-citizen in a non-diplomatic tier is a Ugandan office holder whose
    # P27 is simply missing, rather than a foreign envoy posted to Kampala.
    missing_p27 = [w for w in office
                   if not w['citizen'] and w['tier'] != 'diplomatic']

    return {
        'women': women,
        'office': office,
        'n_office': len(office),
        'n_with': counted(office, lambda w: w['sitelinks'] > 0),
        'n_none': counted(office, lambda w: w['sitelinks'] == 0),
        'n_translate': counted(office, lambda w: w['status'] == 'translate'),
        'n_both': counted(office, lambda w: w['status'] == 'both'),
        'n_other_role': len(women) - len(office),
        'tiers': tiers,
        'worst': worst,
        'missing_p27': missing_p27,
        'foreign': [w for w in office
                    if not w['citizen'] and w['tier'] == 'diplomatic'],
        'positions_seen': conn.execute(
            'SELECT COUNT(*) FROM office_summary').fetchone()[0],
    }
