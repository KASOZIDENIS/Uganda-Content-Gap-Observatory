# -*- coding: utf-8 -*-
"""What Wikimedia Commons holds about Uganda.

Reads the tables src_data/commons_audit.py fills: the category graph walked
from Category:Uganda, the files found in it, and the sampled check on how the
media type was derived.

The one number this page must not present bare is the category count. Commons
categories form a graph that reaches the rest of the world if followed far
enough, so every total here is a function of the crawl depth that produced it,
and the depth travels with the number.
"""

import config

# The thematic buckets, in the order the page shows them. Matches THEMES in
# src_data/commons_audit.py.
THEME_ORDER = ('People', 'Culture', 'Geography', 'Environment', 'Sports',
               'Buildings', 'History', 'Economy', 'Government', 'Education',
               'Health', 'Charts and data', 'Wikimedia community', 'Other')

MEDIA_LABELS = {
    'BITMAP': 'Photographs and bitmap images',
    'DRAWING': 'Drawings (SVG)',
    'VIDEO': 'Video',
    'AUDIO': 'Audio',
    'OFFICE': 'Documents (PDF, DjVu)',
    '3D': '3D models',
    'UNKNOWN': 'Unrecognised',
}

TOP_CATEGORIES = 40


def _has(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone() is not None


def load(conn):
    if not _has(conn, 'commons_categories') or not _has(conn, 'commons_files'):
        raise SystemExit('no commons tables\n'
                         'run: python src_data/commons_audit.py')

    n_categories = conn.execute(
        'SELECT COUNT(*) FROM commons_categories').fetchone()[0]
    n_files = conn.execute('SELECT COUNT(*) FROM commons_files').fetchone()[0]
    truncated = conn.execute(
        'SELECT COUNT(*) FROM commons_categories WHERE truncated = 1'
    ).fetchone()[0]
    max_depth = conn.execute(
        'SELECT MAX(depth) FROM commons_categories').fetchone()[0] or 0

    # how the graph grows with depth: the reason a bare total means little
    depths = [{'depth': d, 'categories': n, 'files': f or 0}
              for d, n, f in conn.execute("""
                  SELECT depth, COUNT(*), SUM(files)
                  FROM commons_categories GROUP BY depth ORDER BY depth""")]

    media = []
    for kind, n in conn.execute("""SELECT mediatype, COUNT(*) FROM commons_files
                                   GROUP BY mediatype ORDER BY 2 DESC"""):
        media.append({
            'key': kind,
            'label': MEDIA_LABELS.get(kind, kind),
            'files': n,
            'share': 100.0 * n / n_files if n_files else 0.0,
        })

    themes = []
    counts = dict(conn.execute("""SELECT theme, COUNT(*) FROM commons_files
                                  GROUP BY theme"""))
    cat_counts = dict(conn.execute("""SELECT theme, COUNT(*)
                                      FROM commons_categories GROUP BY theme"""))
    for name in THEME_ORDER:
        n = counts.get(name, 0)
        if not n and not cat_counts.get(name):
            continue
        themes.append({
            'key': name,
            'label': name,
            'files': n,
            'categories': cat_counts.get(name, 0),
            'share': 100.0 * n / n_files if n_files else 0.0,
        })

    campaigns = []
    for name, n in conn.execute("""SELECT campaign, COUNT(*) FROM commons_files
                                   WHERE campaign != '' GROUP BY campaign
                                   ORDER BY 2 DESC"""):
        campaigns.append({
            'key': name,
            'label': name,
            'files': n,
            'share': 100.0 * n / n_files if n_files else 0.0,
        })
    from_campaigns = sum(c['files'] for c in campaigns)

    top = [{'title': t.replace('Category:', ''),
            'url': 'https://commons.wikimedia.org/wiki/'
                   + t.replace(' ', '_'),
            'depth': d, 'files': f, 'theme': th, 'campaign': cp}
           for t, d, f, th, cp in conn.execute("""
               SELECT title, depth, files, theme, campaign
               FROM commons_categories WHERE files > 0
               ORDER BY files DESC, title LIMIT ?""", (TOP_CATEGORIES,))]

    check = None
    if _has(conn, 'commons_mediatype_check'):
        row = conn.execute("""SELECT sampled, agreed, disagreed, unresolved,
                                     accuracy FROM commons_mediatype_check"""
                           ).fetchone()
        if row:
            check = {'sampled': row[0], 'agreed': row[1], 'disagreed': row[2],
                     'unresolved': row[3], 'accuracy': row[4]}

    photos = next((m['files'] for m in media if m['key'] == 'BITMAP'), 0)

    return {
        'nCategories': n_categories,
        'nFiles': n_files,
        'maxDepth': max_depth,
        'truncated': truncated,
        'depths': depths,
        'media': media,
        'themes': themes,
        'campaigns': campaigns,
        'fromCampaigns': from_campaigns,
        'campaignShare': 100.0 * from_campaigns / n_files if n_files else 0.0,
        'photos': photos,
        'photoShare': 100.0 * photos / n_files if n_files else 0.0,
        'top': top,
        'check': check,
        'mediaLabels': dict(MEDIA_LABELS),
    }
