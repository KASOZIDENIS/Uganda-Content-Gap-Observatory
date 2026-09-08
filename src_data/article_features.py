# -*- coding: utf-8 -*-
"""Stage 2: per article features - size and reader demand.

Two signals drive the worklists:

  sitelink_count  how many language editions already consider the topic
                  worth an article (an editorial importance proxy)
  pageviews       how many humans actually read it (a demand proxy)

WDO ranks its Top CCC lists on a comparable blend. Article size is also
collected so a topic that exists in Luganda as a two line stub can be told
apart from one that is genuinely covered.
"""

import datetime
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import config
import ug_utils

SCRIPT = 'article_features'


def _pageview_window():
    """Trailing complete-month window, as REST API timestamps."""
    today = datetime.date.today()
    end = today.replace(day=1) - datetime.timedelta(days=1)      # last complete month
    start = end.replace(day=1)
    for _ in range(config.PAGEVIEW_MONTHS - 1):
        start = (start - datetime.timedelta(days=1)).replace(day=1)
    return start.strftime('%Y%m%d') + '00', end.strftime('%Y%m%d') + '00'


def fetch_article_sizes(conn, force=False):
    """Batch-fetch byte length and image count for CCC articles per wiki."""
    with ug_utils.stage(conn, SCRIPT, 'fetch_article_sizes', force) as st:
        if st.skip:
            return

        conn.execute('DROP TABLE IF EXISTS article_sizes')
        conn.execute("""CREATE TABLE article_sizes (
            qitem text, languagecode text, title text, num_bytes int,
            PRIMARY KEY (qitem, languagecode))""")

        session = ug_utils.get_session()

        for languagecode in config.TARGET_WIKIS:
            pairs = conn.execute(
                'SELECT qitem, title FROM sitelinks WHERE languagecode=?',
                (languagecode,)).fetchall()
            if not pairs:
                print(f'  {languagecode}: no articles')
                continue

            by_title = {}
            for qitem, title in pairs:
                by_title.setdefault(title, qitem)
            titles = list(by_title)
            api = f'https://{languagecode}.wikipedia.org/w/api.php'
            rows, done = [], 0

            for i in range(0, len(titles), 50):
                batch = titles[i:i + 50]
                params = {'action': 'query', 'format': 'json', 'prop': 'info',
                          'titles': '|'.join(batch)}
                try:
                    payload = session.get(api, params=params, timeout=90).json()
                except Exception:                      # noqa: BLE001
                    continue
                query = payload.get('query', {})
                # normalized maps our requested title to the canonical one
                canonical = {n['to']: n['from']
                             for n in query.get('normalized', [])}
                for page in query.get('pages', {}).values():
                    title = page.get('title')
                    requested = canonical.get(title, title)
                    qitem = by_title.get(requested) or by_title.get(title)
                    if qitem and 'length' in page:
                        rows.append((qitem, languagecode, title, page['length']))
                done += len(batch)
                if done % 1000 < 50:
                    print(f'    {languagecode} sizes {done}/{len(titles)}')

            conn.executemany(
                'INSERT OR REPLACE INTO article_sizes VALUES (?,?,?,?)', rows)
            conn.commit()
            print(f'  {languagecode}: sized {len(rows)} articles')


def fetch_pageviews(conn, force=False):
    """Fetch trailing pageviews for the most widely covered CCC articles."""
    with ug_utils.stage(conn, SCRIPT, 'fetch_pageviews', force) as st:
        if st.skip:
            return

        start, end = _pageview_window()
        print(f'  window {start[:6]} .. {end[:6]} ({config.PAGEVIEW_MONTHS} months)')

        conn.execute('DROP TABLE IF EXISTS pageviews')
        conn.execute("""CREATE TABLE pageviews (
            qitem text, languagecode text, title text, views int,
            PRIMARY KEY (qitem, languagecode))""")

        # Reader demand is measured on the reference wiki, which is the one
        # with enough traffic for the numbers to mean anything.
        targets = conn.execute("""
            SELECT s.qitem, s.title FROM sitelinks s
            JOIN ccc_items c ON c.qitem = s.qitem
            WHERE s.languagecode = ?
            ORDER BY c.sitelink_count DESC
            LIMIT ?""", (config.REFERENCE_WIKI, config.PAGEVIEW_TOP_N)).fetchall()
        print(f'  requesting pageviews for {len(targets)} '
              f'{config.REFERENCE_WIKI}wiki articles')

        session = ug_utils.get_session()
        base = (f'{config.PAGEVIEWS_API}/{config.REFERENCE_WIKI}.wikipedia'
                f'/all-access/user')

        def fetch(pair):
            qitem, title = pair
            encoded = urllib.parse.quote(title.replace(' ', '_'), safe='')
            url = f'{base}/{encoded}/monthly/{start}/{end}'
            for attempt in range(5):
                try:
                    response = session.get(url, timeout=60)
                    if response.status_code == 404:
                        # No pageview record: a real answer, not a failure.
                        return (qitem, config.REFERENCE_WIKI, title, 0)
                    if response.status_code in (429, 503):
                        # Back off properly - retrying immediately just burns
                        # the retry budget and loses the article.
                        time.sleep(float(response.headers.get('Retry-After', 0))
                                   or 2 ** attempt)
                        continue
                    response.raise_for_status()
                    total = sum(item['views']
                                for item in response.json().get('items', []))
                    return (qitem, config.REFERENCE_WIKI, title, total)
                except Exception:                      # noqa: BLE001
                    time.sleep(2 ** attempt)
            return None

        rows, done = [], 0
        with ThreadPoolExecutor(max_workers=config.PAGEVIEW_WORKERS) as pool:
            for result in pool.map(fetch, targets):
                done += 1
                if result:
                    rows.append(result)
                if done % 250 == 0:
                    print(f'    pageviews {done}/{len(targets)}')

        conn.executemany(
            'INSERT OR REPLACE INTO pageviews VALUES (?,?,?,?)', rows)
        conn.commit()
        missed = len(targets) - len(rows)
        print(f'  stored pageviews for {len(rows)} articles'
              + (f' ({missed} unresolved)' if missed else ''))


def fetch_edition_stats(conn, force=False):
    """Total article and active-editor counts for the editions we report on.

    Needed to say what *share* of a small edition is Uganda content, and to
    keep those numbers from being hardcoded into the write-up.
    """
    with ug_utils.stage(conn, SCRIPT, 'fetch_edition_stats', force) as st:
        if st.skip:
            return

        codes = list(config.TARGET_WIKIS)
        for (languagecode,) in conn.execute("""
                SELECT languagecode FROM sitelinks GROUP BY languagecode
                ORDER BY COUNT(DISTINCT qitem) DESC LIMIT 20"""):
            if languagecode not in codes:
                codes.append(languagecode)

        conn.execute('DROP TABLE IF EXISTS edition_stats')
        conn.execute("""CREATE TABLE edition_stats (
            languagecode text PRIMARY KEY, articles int, pages int,
            active_editors int, edits int)""")

        session = ug_utils.get_session()
        rows = []
        for languagecode in codes:
            url = f'https://{languagecode}.wikipedia.org/w/api.php'
            params = {'action': 'query', 'meta': 'siteinfo',
                      'siprop': 'statistics', 'format': 'json'}
            try:
                stats = session.get(url, params=params,
                                    timeout=60).json()['query']['statistics']
            except Exception:                          # noqa: BLE001
                print(f'    {languagecode}: siteinfo unavailable')
                continue
            rows.append((languagecode, stats.get('articles'), stats.get('pages'),
                         stats.get('activeusers'), stats.get('edits')))

        conn.executemany(
            'INSERT OR REPLACE INTO edition_stats VALUES (?,?,?,?,?)', rows)
        conn.commit()
        print(f'  stored siteinfo for {len(rows)} editions')
        for languagecode in config.TARGET_WIKIS:
            row = conn.execute(
                'SELECT articles, active_editors FROM edition_stats WHERE languagecode=?',
                (languagecode,)).fetchone()
            if row:
                print(f'    {languagecode}wiki: {row[0]:,} articles, '
                      f'{row[1]} active editors')


def main(force=False):
    conn = ug_utils.connect()
    fetch_article_sizes(conn, force)
    fetch_pageviews(conn, force)
    fetch_edition_stats(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
