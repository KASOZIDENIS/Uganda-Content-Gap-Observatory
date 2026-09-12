# -*- coding: utf-8 -*-
"""Topic areas: last year's readership joined to this year's coverage.

The previous cycle's analysis ranked Uganda articles on English Wikipedia by
pageviews and published a top ten per category. It is a useful demand signal
and it supplies a topic axis this project lacks. What it never asked is
whether any of those well-read topics exist in Uganda's own language.

That join is the whole point of this module:

  demand    their view totals, per topic
  coverage  our sitelinks table, which knows all 343 editions
  gap       demand on topics with no Luganda article, which is the number a
            campaign should be aimed at

It also reads back the other way. 145 of their articles are not in our corpus
at all, which is an independent audit of the recall floor the dashboard
already warns about, and a list of items worth adding.

Reads data/topic_areas.csv, written by src_data/topic_import.py.
"""

import csv
import os

import config

ROSTER = os.path.join(config.DATA_PATH, 'topic_areas.csv')
OFFCORPUS = os.path.join(config.DATA_PATH, 'topic_offcorpus.csv')

# The structural test the worklists use. A topic that reaches the corpus
# only by title keyword or a cross-border ethnicity is there for recall
# and is not evidence of a Ugandan topic on its own: Elizabeth II arrives
# that way, carrying 8.6 million views with her.
CORE_STRATEGIES = ('country_wd', 'citizenship_wd', 'location_wd',
                   'birth_death_wd')

# Areas in the order the page shows them: by unserved demand, computed below,
# so this is only the tie-break for areas with none.
STUB_BYTES = 2000


def _int(value):
    value = (value or '').strip()
    return int(value) if value.lstrip('-').isdigit() else None


def load(conn):
    if not os.path.exists(ROSTER):
        raise SystemExit(
            f'no {ROSTER}\nrun: python src_data/topic_import.py')

    with open(ROSTER, encoding='utf-8-sig', newline='') as handle:
        memberships = list(csv.DictReader(handle))

    # Coverage, straight from the sitelinks table.
    in_lg = {q for (q,) in conn.execute(
        "SELECT qitem FROM sitelinks WHERE languagecode='lg'")}
    in_sw = {q for (q,) in conn.execute(
        "SELECT qitem FROM sitelinks WHERE languagecode='sw'")}
    corpus = dict(conn.execute('SELECT qitem, sitelink_count FROM ccc_items'))
    strategies = dict(conn.execute('SELECT qitem, strategies FROM ccc_items'))

    # Verdicts for imported topics our corpus does not hold, from
    # src_data/topic_verify.py. No file means that stage has not run.
    verdicts = {}
    if os.path.exists(OFFCORPUS):
        with open(OFFCORPUS, encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                verdicts[row['qitem']] = row['verdict']
    our_views = dict(conn.execute(
        'SELECT qitem, views FROM pageviews'))
    lg_bytes = dict(conn.execute(
        "SELECT qitem, num_bytes FROM article_sizes WHERE languagecode='lg'"))
    en_title = dict(conn.execute(
        "SELECT qitem, title FROM sitelinks WHERE languagecode='en'"))
    lg_title = dict(conn.execute(
        "SELECT qitem, title FROM sitelinks WHERE languagecode='lg'"))

    topics = {}
    for row in memberships:
        qitem = row['qitem']
        topic = topics.setdefault(qitem, {
            'qitem': qitem,
            'title': row['title'],
            'areas': [],
            'theirViews': _int(row['their_views']) or 0,
            'hasTheirViews': _int(row['their_views']) is not None,
            'enTitle': en_title.get(qitem, ''),
            'lgTitle': lg_title.get(qitem, ''),
            'inLuganda': qitem in in_lg,
            'inSwahili': qitem in in_sw,
            'inCorpus': qitem in corpus,
            'editions': corpus.get(qitem, 0),
            'ourViews': our_views.get(qitem),
            'lgBytes': lg_bytes.get(qitem),
            # Structurally Ugandan: either a core strategy reached it, or
            # the verification stage found a country, location,
            # citizenship or birth link.
            'core': (any(name in (strategies.get(qitem) or '')
                         for name in CORE_STRATEGIES)
                     if qitem in corpus
                     else verdicts.get(qitem) == 'recall_miss'),
        })
        topic['areas'].append(row['area'])

    # A Luganda article that is a stub is covered on paper only, so the page
    # separates "has one" from "has one worth reading".
    for topic in topics.values():
        topic['lgStub'] = (topic['inLuganda'] and topic['lgBytes'] is not None
                           and topic['lgBytes'] < STUB_BYTES)

    areas = {}
    for topic in topics.values():
        for area in topic['areas']:
            bucket = areas.setdefault(area, {
                'area': area, 'topics': 0, 'reportedViews': 0,
                'coreTopics': 0, 'structuralViews': 0, 'offTopicViews': 0,
                'inLuganda': 0, 'missing': 0, 'unserved': 0, 'stubs': 0,
                'offTopic': 0,
            })
            bucket['topics'] += 1
            bucket['reportedViews'] += topic['theirViews']
            if not topic['core']:
                bucket['offTopic'] += 1
                bucket['offTopicViews'] += topic['theirViews']
                continue
            # Everything below counts structurally Ugandan topics only, which
            # is what a campaign can actually be aimed at.
            bucket['coreTopics'] += 1
            bucket['structuralViews'] += topic['theirViews']
            if topic['inLuganda']:
                bucket['inLuganda'] += 1
                if topic['lgStub']:
                    bucket['stubs'] += 1
            else:
                bucket['missing'] += 1
                bucket['unserved'] += topic['theirViews']
    for bucket in areas.values():
        bucket['covered'] = (100.0 * bucket['inLuganda'] / bucket['coreTopics']
                             if bucket['coreTopics'] else 0)
        bucket['unservedShare'] = (
            100.0 * bucket['unserved'] / bucket['structuralViews']
            if bucket['structuralViews'] else 0)
        bucket['offTopicShare'] = (
            100.0 * bucket['offTopicViews'] / bucket['reportedViews']
            if bucket['reportedViews'] else 0)

    everything = list(topics.values())
    core = [t for t in everything if t['core']]
    reported = sum(t['theirViews'] for t in everything)
    structural = sum(t['theirViews'] for t in core)
    unserved = sum(t['theirViews'] for t in core if not t['inLuganda'])

    # The worklist their ranking was one join away from: structurally Ugandan,
    # most-read first, and absent from Luganda.
    #
    # One entry per (topic, area), not per topic. 102 of these topics are
    # filed under more than one area, and a Geography campaign should see
    # Entebbe International Airport even though its first area is Buildings.
    # Counting per membership is also what makes the per-area table above the
    # list and the filter chips beside it agree: keyed on a single primary
    # area they disagreed by 112 rows.
    missing_core = [t for t in core if not t['inLuganda']]
    worklist = sorted(
        ({**t, 'area': area} for t in missing_core for area in t['areas']),
        key=lambda t: (-t['theirViews'], t['area']))

    # Read the other way, their categories audit this project too.
    recall_misses = sorted((t for t in everything
                            if t['core'] and not t['inCorpus']),
                           key=lambda t: -t['theirViews'])
    over_collected = sorted((t for t in everything if not t['core']),
                            key=lambda t: -t['theirViews'])

    return {
        'topics': everything,
        'areas': sorted(areas.values(), key=lambda a: -a['unserved']),
        'nTopics': len(everything),
        'nCore': len(core),
        'nMemberships': len(memberships),
        'nAreas': len(areas),
        'nInLuganda': sum(1 for t in core if t['inLuganda']),
        'nMissing': sum(1 for t in core if not t['inLuganda']),
        'nStubs': sum(1 for t in core if t['lgStub']),
        'nNoViews': sum(1 for t in everything if not t['hasTheirViews']),
        'nOurViews': sum(1 for t in everything if t['ourViews'] is not None),
        'reportedViews': reported,
        'structuralViews': structural,
        'offTopicViews': reported - structural,
        'unservedViews': unserved,
        'servedViews': structural - unserved,
        'worklist': worklist,
        'nWorklistRows': len(worklist),
        'nWorklistTopics': len(missing_core),
        'recallMisses': recall_misses,
        'overCollected': over_collected,
        'nOverCollected': len(over_collected),
        'verified': bool(verdicts),
    }
