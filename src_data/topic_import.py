# -*- coding: utf-8 -*-
"""Normalise last year's topic-area exports into one input file.

The `training data/` folder holds the previous cycle's content gap analysis:
eleven per-category exports of Uganda pages on English Wikipedia, each row
carrying a Wikidata QID and a pageview total. That work contributes something
this project does not have, which is a topic axis. Our own categorisation is
by Wikidata type (stream, hill, human) and, for women, by field; neither says
"health" or "education", which is how a User Group actually plans a campaign.

So the categories are imported rather than re-derived, and what this project
adds on top is the half their analysis could not see: which of those topics
have a Luganda article, and which do not.

Three things are cleaned up on the way in:

  namespaces   847 of their 2,215 rows are Categories and 15 are Templates.
               Those are navigation scaffolding, not articles anyone reads, so
               only the 1,353 article rows are kept.
  duplicates   306 titles appear in more than one category, so a per-category
               view total cannot be summed across categories without double
               counting. Membership is kept as one row per (topic, item) pair
               and the page de-duplicates when it totals.
  names        file names become readable area names.

Their view figures are kept as-is and labelled as theirs. The window behind
them is not documented in the source material, and comparing the 190 items we
also measured suggests it is roughly twice our six complete months, so the two
are never added together or substituted for one another.

    python src_data/topic_import.py
"""

import csv
import glob
import os
import re

import config

SOURCE_DIR = os.path.join(config.PROJECT_PATH, 'training data')
OUT_FILE = os.path.join(config.DATA_PATH, 'topic_areas.csv')

# File name -> the area name the page shows. Ordered as the previous analysis
# ordered them, loosely by readership.
AREA_NAMES = {
    'Governance in Uganda': 'Governance',
    'Politics': 'Politics',
    'Ugandanpeople 2': 'Ugandan people',
    'Geography of Uganda': 'Geography',
    'society-of-uganda': 'Society & demographics',
    'Economy of Uganda': 'Economy',
    'Buildings and structures in Uganda': 'Buildings & infrastructure',
    'Environment of Uganda': 'Environment',
    'Health in Uganda': 'Health',
    'Education in Uganda': 'Education',
    'History of Uganda': 'History',
}

ARTICLE_NS = '(Article)'
FIELDS = ['qitem', 'area', 'title', 'their_views', 'size_bytes', 'last_change']


def _int(value):
    value = (value or '').strip()
    return int(value) if value.isdigit() else None


def read_source():
    """One row per (area, item), articles only."""
    rows, skipped = [], {'namespace': 0, 'no_qid': 0}
    for path in sorted(glob.glob(os.path.join(SOURCE_DIR, '*.csv'))):
        stem = re.sub(r'-with-views$', '',
                      os.path.splitext(os.path.basename(path))[0])
        area = AREA_NAMES.get(stem)
        if area is None:
            print(f'  ! no area name for {stem!r}, skipping the file')
            continue
        seen = set()
        with open(path, encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                if (row.get('namespace') or '').strip() != ARTICLE_NS:
                    skipped['namespace'] += 1
                    continue
                qitem = (row.get('item') or '').strip()
                if not qitem.startswith('Q'):
                    skipped['no_qid'] += 1
                    continue
                if qitem in seen:
                    continue
                seen.add(qitem)
                rows.append({
                    'qitem': qitem,
                    'area': area,
                    'title': (row.get('title') or '').strip(),
                    'their_views': _int(row.get('total_views')),
                    'size_bytes': _int(row.get('size_bytes')),
                    'last_change': (row.get('last_change') or '').strip(),
                })
        print(f'  {area:28} {len(seen):4} articles')
    return rows, skipped


def main():
    if not os.path.isdir(SOURCE_DIR):
        raise SystemExit(
            f'no {SOURCE_DIR}\n'
            'This step imports the previous cycle\'s per-category exports. '
            'Drop them in that folder, or skip this stage.')

    rows, skipped = read_source()
    if not rows:
        raise SystemExit('nothing imported')

    with open(OUT_FILE, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ('' if row[k] is None else row[k])
                             for k in FIELDS})

    items = {r['qitem'] for r in rows}
    multi = len(rows) - len(items)
    print(f'\nwrote {OUT_FILE}')
    print(f'  {len(rows)} memberships over {len(items)} distinct topics '
          f'in {len({r["area"] for r in rows})} areas')
    print(f'  {multi} of those memberships are a topic appearing in a second '
          f'area')
    print(f'  dropped {skipped["namespace"]} non-article rows '
          f'(categories and templates) and {skipped["no_qid"]} without a QID')


if __name__ == '__main__':
    main()
