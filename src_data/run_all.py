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

    print('\n' + '=' * 70)
    print(f'pipeline finished in {int(time.time() - started)}s')
    print('CSV outputs and uganda_diversity.db are in ../data/')
    print('build the dashboard with: python ../src_viz/build_dashboard.py')
    print('=' * 70)


if __name__ == '__main__':
    main()
