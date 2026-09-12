# -*- coding: utf-8 -*-
"""The dashboard's database queries.

Read by src_viz/dashboard_view.py, which turns them into the JSON
view model the dashboard page renders. The palette and the generated
CSS custom properties live in src_viz/tokens.py.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402


# Editions whose Uganda content is overwhelmingly bot-generated. Flagged in
# the coverage chart so the ranking is not read as editorial effort.
BOT_HEAVY = {'ceb', 'sw', 'arz', 'war', 'nl', 'vi', 'uz', 'azb', 'ce'}


def pct(part, whole, digits=1):
    return round(100.0 * part / whole, digits) if whole else 0


# --------------------------------------------------------------- data access
def _has(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (table,)).fetchone() is not None


def load(conn):
    def rows(query, params=()):
        cur = conn.execute(query, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def one(query, params=()):
        r = conn.execute(query, params).fetchone()
        return r[0] if r else 0

    d = {}
    d['ccc_total'] = one('SELECT COUNT(*) FROM ccc_items')
    wd = conn.execute(
        'SELECT no_article, with_article FROM wikidata_only_totals').fetchone()
    d['wd_no_article'], d['wd_with_article'] = wd if wd else (0, 0)

    d['coverage'] = rows("""
        SELECT languagecode, COUNT(DISTINCT qitem) AS n FROM sitelinks
        GROUP BY languagecode ORDER BY n DESC LIMIT 20""")
    d['editions'] = one('SELECT COUNT(DISTINCT languagecode) FROM sitelinks')

    d['per_wiki'] = {
        lc: one('SELECT COUNT(DISTINCT qitem) FROM sitelinks WHERE languagecode=?',
                (lc,))
        for lc in config.TARGET_WIKIS}

    d['only_one'] = one('SELECT COUNT(*) FROM ccc_items WHERE sitelink_count=1')
    d['spread_raw'] = rows("""
        SELECT sitelink_count, COUNT(*) AS n FROM ccc_items
        GROUP BY sitelink_count""")

    d['composition'] = rows("""
        SELECT languagecode, people, places, institutions, other, total
        FROM edition_composition ORDER BY total DESC
        """) if _has(conn, 'edition_composition') else []

    d['wd_types'] = rows("""
        SELECT type_label, no_article, with_article FROM wikidata_only
        ORDER BY no_article DESC LIMIT 10""")

    d['bios'] = one('SELECT COUNT(*) FROM ccc_items WHERE gender_qid IS NOT NULL')
    d['women'] = one("SELECT COUNT(*) FROM ccc_items WHERE gender_qid='Q6581072'")
    d['men'] = one("SELECT COUNT(*) FROM ccc_items WHERE gender_qid='Q6581097'")

    d['gender_by_wiki'] = [{
        'wiki': 'all editions', 'men': d['men'], 'women': d['women']}]
    for lc in config.TARGET_WIKIS:
        d['gender_by_wiki'].append({
            'wiki': lc + 'wiki',
            'men': one("""SELECT COUNT(*) FROM ccc_items c
                          JOIN sitelinks s ON s.qitem=c.qitem AND s.languagecode=?
                          WHERE c.gender_qid='Q6581097'""", (lc,)),
            'women': one("""SELECT COUNT(*) FROM ccc_items c
                            JOIN sitelinks s ON s.qitem=c.qitem AND s.languagecode=?
                            WHERE c.gender_qid='Q6581072'""", (lc,))})

    d['edition_stats'] = {
        r['languagecode']: r for r in rows('SELECT * FROM edition_stats')
    } if _has(conn, 'edition_stats') else {}

    d['women_fields'] = rows("""
        SELECT * FROM women_by_field ORDER BY women DESC
        """) if _has(conn, 'women_by_field') else []
    d['women_translate'] = rows("""
        SELECT label, field, en_title, sitelink_count, views, occupation_names
        FROM women_translate ORDER BY views DESC, sitelink_count DESC LIMIT 25
        """) if _has(conn, 'women_translate') else []
    d['women_create'] = rows("""
        SELECT label, field, statements, occupation_names, description
        FROM women_create ORDER BY statements DESC LIMIT 25
        """) if _has(conn, 'women_create') else []

    d['women_lg_sizes'] = (rows('SELECT * FROM women_lg_article_sizes') or [{}])[0] \
        if _has(conn, 'women_lg_article_sizes') else {}
    d['women_lg_only'] = one("""
        SELECT COUNT(*) FROM women
        WHERE lg_title IS NOT NULL AND en_title IS NULL
        """) if _has(conn, 'women') else 0

    d['peers'] = rows('SELECT * FROM peer_countries') \
        if _has(conn, 'peer_countries') else []
    d['admin_units'] = rows('SELECT * FROM admin_units_coverage') \
        if _has(conn, 'admin_units_coverage') else []
    d['strategies'] = rows("""
        SELECT strategy, COUNT(*) AS n FROM strategy_hits
        GROUP BY strategy ORDER BY n DESC""")

    # Worklist eligibility: a structural link to Uganda, not just a keyword
    # or a cross-border ethnicity. Mirrors CORE_STRATEGIES in stats_generation.
    d['core_eligible'] = one("""
        SELECT COUNT(*) FROM ccc_items
        WHERE strategies LIKE '%country_wd%' OR strategies LIKE '%citizenship_wd%'
           OR strategies LIKE '%location_wd%' OR strategies LIKE '%birth_death_wd%'
        """)

    for lc in config.LOCAL_WIKIS:
        table = f'missing_{lc}'
        d[table] = rows(f"""
            SELECT label, en_title, sitelink_count, views, priority, type_labels
            FROM {table} ORDER BY priority DESC, sitelink_count DESC LIMIT 30
            """) if _has(conn, table) else []

    d['stubs'] = {}
    for lc in config.LOCAL_WIKIS:
        if not _has(conn, 'article_sizes'):
            d['stubs'][lc] = {'total': 0, 'stubs': 0}
            continue
        d['stubs'][lc] = {
            'total': one('SELECT COUNT(*) FROM article_sizes WHERE languagecode=?',
                         (lc,)),
            'stubs': one("""SELECT COUNT(*) FROM article_sizes
                            WHERE languagecode=? AND num_bytes < 2000""", (lc,))}
    return d


def bucket_spread(spread_rows):
    buckets = [(1, 1, 'in 1 edition only'), (2, 5, 'in 2-5 editions'),
               (6, 10, 'in 6-10'), (11, 25, 'in 11-25'), (26, 10 ** 6, 'in 26+')]
    return [{'label': label,
             'n': sum(r['n'] for r in spread_rows
                      if low <= (r['sitelink_count'] or 0) <= high)}
            for low, high, label in buckets]
