# -*- coding: utf-8 -*-
"""Folklore of Uganda across two axes: communities and heritage aspects.

Reads the tables src_data/folklore_matrix.py fills. The matrix is a floor
rather than a census: it counts English Wikipedia articles whose title carries
a community's name, so an article titled for the practice alone, such as
Empaako or Kasubi Tombs, is invisible to it. Those are caught by the anchors
instead, and the page says which is which.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src_data'))

import folklore_matrix as fm      # noqa: E402  the curated taxonomy


def _has(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone() is not None


def load(conn):
    if not _has(conn, 'folklore_articles') or not _has(conn, 'folklore_anchors'):
        raise SystemExit('no folklore tables\n'
                         'run: python src_data/folklore_matrix.py')

    families = dict(fm.FAMILIES)
    aspect_labels = {k: l for k, l, _p, _v in fm.ASPECTS}
    aspect_parent = {k: p for k, _l, p, _v in fm.ASPECTS}
    domain_labels = dict(fm.UNESCO_DOMAINS)

    counts = {(g, a): n for g, a, n in conn.execute(
        """SELECT group_key, aspect, COUNT(*) FROM folklore_articles
           WHERE aspect != '' GROUP BY 1, 2""")}
    titles = {}
    for g, a, t in conn.execute(
            """SELECT group_key, aspect, title FROM folklore_articles
               WHERE aspect != '' ORDER BY title"""):
        titles.setdefault((g, a), []).append(t)

    aspects = [{'key': k, 'label': l, 'parent': p,
                'parentLabel': domain_labels.get(p, p),
                'articles': sum(n for (_g, ak), n in counts.items() if ak == k)}
               for k, l, p, _v in fm.ASPECTS]

    groups, rows = [], []
    for key, label, family, _variants in fm.GROUPS:
        total = sum(n for (g, _a), n in counts.items() if g == key)
        groups.append({'key': key, 'label': label, 'family': family,
                       'familyLabel': families.get(family, family),
                       'articles': total})
        rows.append({
            'key': key, 'label': label, 'family': family,
            'familyLabel': families.get(family, family),
            'total': total,
            'cells': [{'aspect': a['key'],
                       'n': counts.get((key, a['key']), 0),
                       'titles': titles.get((key, a['key']), [])}
                      for a in aspects],
        })

    fam_summary = []
    for fkey, flabel in fm.FAMILIES:
        members = [g for g in groups if g['family'] == fkey]
        fam_summary.append({
            'key': fkey, 'label': flabel,
            'groups': len(members),
            'articles': sum(g['articles'] for g in members),
            'empty': sum(1 for g in members if not g['articles']),
        })

    anchors = []
    for (name, year, listing, group_key, aspect, en, lg, qid,
         languages) in conn.execute(
            """SELECT name, year, listing, group_key, aspect, en_title,
                      lg_title, qid, languages FROM folklore_anchors
               ORDER BY listing DESC, year"""):
        anchors.append({
            'name': name, 'year': year, 'listing': listing,
            'group': group_key, 'aspect': aspect_labels.get(aspect, aspect),
            'en': en, 'lg': lg, 'qid': (qid or '').split(' ')[0],
            'languages': languages,
            'intangible': listing != 'World Heritage',
        })
    ich = [a for a in anchors if a['intangible']]
    tangible = [a for a in anchors if not a['intangible']]

    total_articles = sum(g['articles'] for g in groups)
    empty_groups = [g for g in groups if not g['articles']]
    empty_aspects = [a for a in aspects if not a['articles']]
    cells = len(groups) * len(aspects)
    filled = sum(1 for r in rows for c in r['cells'] if c['n'])

    return {
        'families': fam_summary,
        'groups': groups,
        'aspects': aspects,
        'rows': rows,
        'anchors': anchors,
        'ich': ich,
        'tangible': tangible,
        'nGroups': len(groups),
        'nAspects': len(aspects),
        'nArticles': total_articles,
        'nDistinct': conn.execute(
            'SELECT COUNT(DISTINCT title) FROM folklore_articles').fetchone()[0],
        'nDropped': conn.execute(
            "SELECT COUNT(*) FROM folklore_articles WHERE aspect = ''"
        ).fetchone()[0],
        'emptyGroups': [g['label'] for g in empty_groups],
        'emptyAspects': [a['label'] for a in empty_aspects],
        'cells': cells,
        'filled': filled,
        'fillShare': 100.0 * filled / cells if cells else 0.0,
        'ichLanguages': sum(a['languages'] for a in ich),
        'tangibleLanguages': sum(a['languages'] for a in tangible),
        'ichUndocumented': [a['name'] for a in ich if not a['languages']],
        'inventories': [
            {'what': what, 'holder': holder, 'url': url, 'note': note}
            for what, holder, url, note in fm.EXTERNAL_INVENTORIES],
    }
