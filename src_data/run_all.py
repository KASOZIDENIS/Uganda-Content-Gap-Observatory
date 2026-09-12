# -*- coding: utf-8 -*-
"""Run the whole Uganda gap pipeline in order.

    python run_all.py            # resume: skip stages already done this cycle
    python run_all.py --force    # recompute everything

Stages are checkpointed per calendar month, so re-running mid-month picks up
where an interrupted run left off. A new month starts a fresh cycle, which is
how the analysis stays current.
"""

import sys
import time

import article_features
import content_retrieval
import incubator_starter
import office_analysis
import roster_check
import official_registers
import osm_features
import topic_import
import topic_verify
import stats_generation
import ug_utils
import women_analysis


def main():
    force = '--force' in sys.argv
    started = time.time()

    print('=' * 70)
    print(f'UGANDA CONTENT GAP OBSERVATORY - cycle {ug_utils.cycle_year_month()}')
    print('=' * 70)

    content_retrieval.main(force)
    article_features.main(force)
    stats_generation.main(force)
    women_analysis.main(force)
    incubator_starter.main(force)
    office_analysis.main(force)
    roster_check.main(force)

    # The topic axis comes from the previous cycle's exports rather
    # than from a query, so the import is skipped when that folder is
    # not present instead of failing the run.
    try:
        topic_import.main()
        topic_verify.main(force)
    except SystemExit as reason:
        print(f'  topic areas skipped: {reason}')

    # OpenStreetMap is a third corpus rather than a Wikimedia one, and the
    # public Overpass instances are slow and freely hand out 429s, so this
    # runs last and its failure does not sink the cycle. It checkpoints per
    # feature class, so re-running resumes.
    try:
        osm_features.main(force)
    except Exception as reason:                        # noqa: BLE001
        print(f'  osm features skipped: {type(reason).__name__}: {reason}')

    # The government's own registers, parsed out of an XLSX and a PDF. Both
    # are third-party downloads, so a failure here does not sink the cycle.
    try:
        official_registers.main(force)
    except Exception as reason:                        # noqa: BLE001
        print(f'  official registers skipped: '
              f'{type(reason).__name__}: {reason}')

    print('\n' + '=' * 70)
    print(f'pipeline finished in {int(time.time() - started)}s')
    print('CSV outputs and uganda_diversity.db are in ../data/')
    print('then: python ../src_viz/export_data.py && '
          'python ../src_viz/build_pages.py')
    print('=' * 70)


if __name__ == '__main__':
    main()
