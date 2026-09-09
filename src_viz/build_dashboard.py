# -*- coding: utf-8 -*-
"""Render the Uganda gap findings to an HTML page.

Charts are inline SVG drawn by a small amount of vanilla JS from data
embedded in the page, so there are no third-party dependencies. Every chart
also ships a server-rendered table view, so values stay readable with JS off.

Styling lives in assets/css/ (tokens, shell, dashboard). tokens.css is written
by this module from the LIGHT/DARK palettes below, which the chart JS also
reads, so the palette is defined once.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402
import ug_utils    # noqa: E402
import render     # noqa: E402
from render import esc, fmt   # noqa: E402

OUT_FILE = os.path.join(config.PROJECT_PATH, 'uganda_content_gap.html')
# Both pages read their palette from this generated sheet, so LIGHT/DARK
# below stay the single source of truth for the chart JS and the CSS alike.
TOKENS_FILE = os.path.join(config.PROJECT_PATH, 'assets', 'css', 'tokens.css')

# Validated palette slots. Checked with the dataviz validator in both modes:
# categorical slots 1-3 pass all-pairs; the 5-step ordinal ramp passes with
# light-mode steps 250-650 and dark-mode steps 100-500.
LIGHT = {
    'surface': '#fcfcfb', 'page': '#f9f9f7',
    'text': '#0b0b0b', 'text2': '#52514e', 'muted': '#898781',
    'grid': '#e1e0d9', 'baseline': '#c3c2b7',
    's1': '#2a78d6', 's2': '#eb6834', 's3': '#1baf7a',
    'neutral': '#cbcac3',
    'ord': ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'],
}
DARK = {
    'surface': '#1a1a19', 'page': '#0d0d0d',
    'text': '#ffffff', 'text2': '#c3c2b7', 'muted': '#898781',
    'grid': '#2c2c2a', 'baseline': '#383835',
    's1': '#3987e5', 's2': '#d95926', 's3': '#199e70',
    'neutral': '#4f4f4b',
    'ord': ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf'],
}

# Status colours used by the action plan's CSS only, so they are kept out of
# LIGHT/DARK: those two are serialised into the page for the chart JS, which
# has no use for them. Same value in both modes, contrast-checked on both.
STATUS = {'good': '#0ca30c', 'critical': '#d03b3b'}

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


# --------------------------------------------------------------- html pieces
def table_view(headers, body_rows, align_right=()):
    head = ''.join(f'<th{" class=num" if i in align_right else ""}>{esc(h)}</th>'
                   for i, h in enumerate(headers))
    body = ''.join(
        '<tr>' + ''.join(
            f'<td{" class=num" if i in align_right else ""}>{c}</td>'
            for i, c in enumerate(row)) + '</tr>'
        for row in body_rows)
    return (f'<div class="tableview" hidden><table><thead><tr>{head}</tr>'
            f'</thead><tbody>{body}</tbody></table></div>')


def card(title, subtitle, chart_id, table_html, note=''):
    note_html = f'<p class="note">{note}</p>' if note else ''
    return f"""
    <section class="card">
      <div class="card-head">
        <div><h3>{esc(title)}</h3><p class="sub">{subtitle}</p></div>
        <button class="toggle" type="button" aria-pressed="false">Table</button>
      </div>
      <div class="chart" id="{chart_id}"></div>
      {table_html}{note_html}
    </section>"""


def wiki_link(lang, title):
    if not title:
        return '<span class="dim">n/a</span>'
    url = f'https://{lang}.wikipedia.org/wiki/' + str(title).replace(' ', '_')
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a>'


def worklist(rows, lang_name):
    if not rows:
        return ('<p class="note">No worklist available: run the pipeline '
                'first.</p>')
    body = ''.join(
        f'<tr><td class="num">{i}</td>'
        f'<td>{esc(r["label"] or r["en_title"] or "")}</td>'
        f'<td>{wiki_link("en", r["en_title"])}</td>'
        f'<td class="num">{fmt(r["sitelink_count"])}</td>'
        f'<td class="num">{fmt(r["views"])}</td>'
        f'<td class="num"><strong>{r["priority"]}</strong></td>'
        f'<td class="dim">{esc((r["type_labels"] or "")[:44])}</td></tr>'
        for i, r in enumerate(rows, 1))
    return f"""<div class="scroller"><table class="worklist">
    <thead><tr><th class="num">#</th><th>Topic</th>
    <th>English article</th><th class="num">Editions</th>
    <th class="num">Views</th><th class="num">Priority</th><th>Type</th>
    </tr></thead><tbody>{body}</tbody></table></div>"""


# --------------------------------------------------------------- page
def tokens_css():
    """Render the design tokens from LIGHT/DARK into a standalone stylesheet.

    The palettes below feed both the chart JS and the page CSS, so the token
    sheet is generated rather than hand-kept in sync.
    """

    def block(palette, indent, border, shadow, wash, scheme):
        pad = ' ' * indent
        return (
            f"{pad}--surface: {palette['surface']}; --page: {palette['page']};\n"
            f"{pad}--text: {palette['text']}; --text2: {palette['text2']};"
            f" --muted: {palette['muted']};\n"
            f"{pad}--grid: {palette['grid']}; --baseline: {palette['baseline']};\n"
            f"{pad}--s1: {palette['s1']}; --s2: {palette['s2']};"
            f" --s3: {palette['s3']};\n"
            f"{pad}--good: {STATUS['good']}; --critical: {STATUS['critical']};\n"
            f"{pad}--border: {border}; --shadow: {shadow};\n"
            f"{pad}--wash: {wash};\n"
            f"{pad}color-scheme: {scheme};\n")

    light = block(LIGHT, 2, 'rgba(11,11,11,0.10)',
                  '0 1px 2px rgba(11,11,11,0.04)', 'rgba(11,11,11,0.035)', 'light')
    dark_nested = block(DARK, 4, 'rgba(255,255,255,0.10)', 'none',
                        'rgba(255,255,255,0.05)', 'dark')
    dark_flat = block(DARK, 2, 'rgba(255,255,255,0.10)', 'none',
                      'rgba(255,255,255,0.05)', 'dark')
    return (
        '/* tokens.css - generated by src_viz/build_dashboard.py from its\n'
        '   LIGHT/DARK palettes. Do not edit by hand; edit the palettes. */\n'
        ':root {\n' + light + '}\n'
        '@media (prefers-color-scheme: dark) {\n'
        '  :root:not([data-theme="light"]) {\n' + dark_nested + '  }\n'
        '}\n'
        ':root[data-theme="dark"] {\n' + dark_flat + '}\n')


def build(d):
    ccc = d['ccc_total']
    per = d['per_wiki']
    wd_total = d['wd_no_article'] + d['wd_with_article']
    spread = bucket_spread(d['spread_raw'])

    comp = d['composition']
    comp_top = [r for r in comp if r['total'] >= 200][:10]
    for lc in config.TARGET_WIKIS:
        if not any(r['languagecode'] == lc for r in comp_top):
            extra = next((r for r in comp if r['languagecode'] == lc), None)
            if extra:
                comp_top.append(extra)
    comp_top.sort(key=lambda r: -r['total'])

    top_edition = d['coverage'][0] if d['coverage'] else {'languagecode': '', 'n': 0}
    top_comp = next((r for r in comp if r['languagecode'] == top_edition['languagecode']),
                    None)
    lg_comp = next((r for r in comp if r['languagecode'] == 'lg'), None)

    admin = d['admin_units']
    admin_en = sum(1 for r in admin if r.get('in_en'))
    admin_lg = sum(1 for r in admin if r.get('in_lg'))
    stub_lg = d['stubs'].get('lg', {})

    stub_sw = d['stubs'].get('sw', {})
    stub_rate_lg = pct(stub_lg.get('stubs', 0), stub_lg.get('total', 0), 0)
    stub_rate_sw = pct(stub_sw.get('stubs', 0), stub_sw.get('total', 0), 0)

    lg_stats = d['edition_stats'].get('lg', {})
    lg_articles = lg_stats.get('articles') or 0
    lg_editors = lg_stats.get('active_editors')
    lg_share = pct(per.get('lg', 0), lg_articles)
    editors_phrase = (f'roughly {lg_editors} active editors' if lg_editors
                      else 'a very small editing community')

    charts = {
        'composition': [
            {'label': r['languagecode'],
             'v': [r['people'], r['places'], r['institutions'] + r['other']]}
            for r in comp_top],
        'coverage': [
            {'label': r['languagecode'] + ('  (bot)' if r['languagecode'] in BOT_HEAVY
                                           else ''),
             'v': r['n'],
             'hi': r['languagecode'] in config.TARGET_WIKIS}
            for r in d['coverage']],
        'spread': spread,
        'gender': [{'label': r['wiki'], 'v': [r['men'], r['women']]}
                   for r in d['gender_by_wiki']],
        'peers': [{'label': r['country'], 'v': r['items_with_article'],
                   'hi': r['country'] == 'Uganda'} for r in d['peers']],
        'peerWomen': [{'label': r['country'], 'v': r['pct_women'],
                       'hi': r['country'] == 'Uganda'} for r in d['peers']],
        'strategies': [{'label': r['strategy'], 'v': r['n']}
                       for r in d['strategies']],
        'womenFields': [
            {'label': r['field'],
             'v': [r['in_english'], r['in_luganda'], r['no_article_anywhere']]}
            for r in d['women_fields'] if r['field'] != 'ALL FIELDS'],
        'wdTypes': [{'label': r['type_label'],
                     'v': [r['no_article'], r['with_article']]}
                    for r in d['wd_types']],
    }

    all_women = next((r for r in d['women_fields']
                      if r['field'] == 'ALL FIELDS'), None)
    football = next((r for r in d['women_fields']
                     if r['field'] == 'Football'), None)
    lg_sizes = d['women_lg_sizes']

    def women_table(rows, mode):
        if not rows:
            return '<p class="note">Run <code>women_analysis.py</code> to build this.</p>'
        if mode == 'translate':
            body = ''.join(
                f'<tr><td class="num">{i}</td><td>{esc(r["label"])}</td>'
                f'<td class="dim">{esc(r["field"])}</td>'
                f'<td>{wiki_link("en", r["en_title"])}</td>'
                f'<td class="num">{fmt(r["sitelink_count"])}</td>'
                f'<td class="num">{fmt(r["views"])}</td>'
                f'<td class="dim">{esc((r["occupation_names"] or "")[:38])}</td></tr>'
                for i, r in enumerate(rows, 1))
            head = ('<th class="num">#</th><th>Name</th><th>Field</th>'
                    '<th>English article</th><th class="num">Editions</th>'
                    '<th class="num">Views</th><th>Occupation</th>')
        else:
            body = ''.join(
                f'<tr><td class="num">{i}</td><td>{esc(r["label"])}</td>'
                f'<td class="dim">{esc(r["field"])}</td>'
                f'<td class="num">{fmt(r["statements"])}</td>'
                f'<td class="dim">{esc((r["description"] or "")[:52])}</td></tr>'
                for i, r in enumerate(rows, 1))
            head = ('<th class="num">#</th><th>Name</th><th>Field</th>'
                    '<th class="num">Wikidata facts</th><th>Described as</th>')
        return (f'<div class="scroller"><table class="worklist">'
                f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')

    approved = config.languages_by_status('approved')
    incubating = config.languages_by_status('incubating')
    no_project = config.languages_by_status('none')

    langs_note = []
    if approved:
        langs_note.append(
            f'<strong>{", ".join(approved)}</strong> is approved and awaiting '
            'creation by developers')
    if incubating:
        langs_note.append(
            f'<strong>{", ".join(incubating)}</strong> has an active Incubator '
            'test wiki with a request pending')
    if no_project:
        langs_note.append(
            f'{len(no_project)} more ({", ".join(no_project)}) have no project '
            'yet')
    langs_missing = '; '.join(langs_note) + '.'

    payload = json.dumps({'charts': charts, 'light': LIGHT, 'dark': DARK},
                         separators=(',', ':'))

    return f"""{render.head('Uganda Content Gap', 'dashboard.css')}

<div class="wrap">
{config.tab_bar('dashboard')}
<header class="top">
  <p class="eyebrow">Wikipedia content gap analysis &middot; Uganda &middot; cycle {esc(ug_utils.cycle_year_month())}</p>
  <h1>Two different Ugandas exist on Wikipedia, and neither one is complete</h1>
  <p class="lede">A single-territory content gap study modelled on the Wikipedia
  Diversity Observatory. Across Wikipedia's {fmt(d['editions'])} language
  editions there are {fmt(ccc)} Uganda-related topics, but the editions
  holding the most of them describe a country of rivers and hills with almost
  no people in it, while the one Ugandan-language edition describes people and
  almost no country.</p>
</header>

<h2>The headline</h2>
<div class="tiles">
  <div class="tile">
    <p class="k">Uganda topics</p>
    <div class="v">{fmt(ccc)}</div>
    <p class="d">with an article in at least one language</p>
  </div>
  <div class="tile alarm">
    <p class="k">No article anywhere</p>
    <div class="v">{fmt(d['wd_no_article'])}</div>
    <p class="d">{pct(d['wd_no_article'], wd_total)}% of Uganda's Wikidata items</p>
  </div>
  <div class="tile">
    <p class="k">Largest edition</p>
    <div class="v">{esc(top_edition['languagecode'])} &middot; {fmt(top_edition['n'])}</div>
    <p class="d">{'holds just ' + fmt(top_comp['people']) + ' biographies' if top_comp else 'articles'}
    &middot; <a href="{config.page_href('edition')}">see all
    {fmt(top_edition['n'])}</a></p>
  </div>
  <div class="tile">
    <p class="k">Luganda Wikipedia</p>
    <div class="v">{fmt(per.get('lg', 0))}</div>
    <p class="d">{lg_share}% of that entire {fmt(lg_articles)}-article edition
    is Uganda content</p>
  </div>
</div>

<h2>The finding</h2>
<p class="h2sub">The same corpus looks completely different depending on which
edition you read it in. Cebuano and Swahili hold thousands of Ugandan streams,
hills and sub-counties generated in bulk by bots. Luganda holds Ugandan
people, written by people.</p>

{card('What each edition’s Uganda content is made of',
      'Articles grouped by what the topic <em>is</em>. Editions with at least '
      '200 Uganda articles, plus English, Luganda and Swahili.',
      'chart-composition',
      table_view(['Edition', 'People', 'Places & nature', 'Everything else',
                  'Total', '% people'],
                 [[esc(r['languagecode']) + 'wiki', fmt(r['people']),
                   fmt(r['places']), fmt(r['institutions'] + r['other']),
                   fmt(r['total']), f"{pct(r['people'], r['total'])}%"]
                  for r in comp_top], align_right=(1, 2, 3, 4, 5)),
      note='&ldquo;Places &amp; nature&rdquo; covers settlements, administrative '
           'units and physical geography; &ldquo;everything else&rdquo; is '
           'institutions, organisations, works and topics. Buckets are matched '
           'on Wikidata type labels, so a handful of items land in '
           '&ldquo;everything else&rdquo; simply for having an unusual type. '
           f'Article length says the same thing: {stub_rate_lg:.0f}% of Luganda&rsquo;s '
           f'Uganda articles are under 2&nbsp;KB, against {stub_rate_sw:.0f}% of '
           'Swahili&rsquo;s, the signature of writing versus generation.')}

<div class="callout">
  <strong>{esc(top_edition['languagecode'])}wiki holds more Uganda articles than
  English does, and {fmt(top_comp['people']) if top_comp else 'almost none'} of
  them are about a Ugandan.</strong>
  Its Uganda corpus is bot-generated physical geography. Luganda Wikipedia, with
  {fmt(per.get('lg', 0))} Uganda articles and {editors_phrase}, is
  {pct(lg_comp['people'], lg_comp['total']) if lg_comp else 0}% biographies.
  Article counts alone cannot tell these two situations apart, which is
  why counting articles is not the same as measuring coverage.
</div>

{card('Uganda articles per Wikipedia edition',
      f'Top 20 of {fmt(d["editions"])} editions carrying any Uganda content. '
      'Editions relevant to Uganda are highlighted; <code>(bot)</code> marks '
      'those whose Uganda content is largely machine-generated.',
      'chart-coverage',
      table_view(['Edition', 'Uganda articles', '% of corpus'],
                 [[esc(r['languagecode']) + 'wiki', fmt(r['n']),
                   f"{pct(r['n'], ccc)}%"] for r in d['coverage']],
                 align_right=(1, 2)),
      note='Rank here reflects bot policy as much as editorial interest. An '
           'edition that ran a geography-import bot outranks one with an active '
           'human community writing about the country.')}

{card('How far a Uganda topic travels',
      f'{pct(d["only_one"], ccc)}% of the corpus exists in exactly one edition. '
      'A topic in one edition only has no translation path and no second reader.',
      'chart-spread',
      table_view(['Spread', 'Topics', '% of corpus'],
                 [[esc(r['label']), fmt(r['n']), f"{pct(r['n'], ccc)}%"]
                  for r in spread], align_right=(1, 2)))}

<h2>The local-language gap</h2>
<p class="h2sub">Luganda Wikipedia is the most Uganda-focused edition in the
world, and it is still missing {fmt(ccc - per.get('lg', 0))} of the
{fmt(ccc)} topics. It is also Uganda's only live Wikipedia, but not for
much longer: {langs_missing}</p>

<div class="tiles">
  <div class="tile alarm">
    <p class="k">Missing from Luganda</p>
    <div class="v">{fmt(ccc - per.get('lg', 0))}</div>
    <p class="d">Uganda topics with no Luganda article</p>
  </div>
  <div class="tile">
    <p class="k">Missing from Swahili</p>
    <div class="v">{fmt(ccc - per.get('sw', 0))}</div>
    <p class="d">Uganda topics with no Swahili article</p>
  </div>
  <div class="tile">
    <p class="k">Luganda stubs</p>
    <div class="v">{fmt(stub_lg.get('stubs', 0))}</div>
    <p class="d">of {fmt(stub_lg.get('total', 0))} Uganda articles are under 2&nbsp;KB
    ({pct(stub_lg.get('stubs', 0), stub_lg.get('total', 0), 0):.0f}%)</p>
  </div>
  <div class="tile">
    <p class="k">Ugandan sub-territories</p>
    <div class="v">{fmt(admin_lg)} / {fmt(len(admin))}</div>
    <p class="d">first-level units in Luganda ({fmt(admin_en)} in English)</p>
  </div>
</div>

<section class="card">
  <div class="card-head"><div>
    <h3>What Luganda Wikipedia should write next</h3>
    <p class="sub">Top 30 by priority: the mean of two percentile ranks
    (how many editions already carry the topic, and English Wikipedia pageviews
    over the trailing {config.PAGEVIEW_MONTHS} months). Drawn from the
    {fmt(d['core_eligible'])} topics with a structural link to Uganda, not the
    full {fmt(ccc)}.</p>
  </div></div>
  {worklist(d.get('missing_lg', []), 'Luganda')}
</section>

<section class="card">
  <div class="card-head"><div>
    <h3>What Swahili Wikipedia should write next</h3>
    <p class="sub">Same ranking, restricted to Uganda topics with no Swahili
    article.</p>
  </div></div>
  {worklist(d.get('missing_sw', []), 'Swahili')}
</section>

<h2>Who the corpus is about</h2>
<p class="h2sub">Of {fmt(d['bios'])} Ugandan biographies,
{pct(d['women'], d['bios'])}% are women, roughly double Wikipedia's
long-standing global figure of about 20%. This is the one dimension where
Uganda's coverage is ahead rather than behind.</p>

{card('Ugandan biographies by gender',
      'Men and women with a Ugandan connection, per edition. Both counts are '
      'direct-labelled; shares are in the table view.',
      'chart-gender',
      table_view(['Scope', 'Men', 'Women', '% women'],
                 [[esc(r['wiki']), fmt(r['men']), fmt(r['women']),
                   f"{pct(r['women'], r['men'] + r['women'])}%"]
                  for r in d['gender_by_wiki']], align_right=(1, 2, 3)),
      note='Read with one caveat: Uganda’s biographies are heavily '
           'contemporary (living politicians, athletes and activists), '
           'and recent biographies are better balanced everywhere on Wikipedia. '
           'Some of this lead is a recency effect rather than Uganda-specific '
           'editorial success. It is still a genuinely better ratio than the '
           'encyclopedia-wide figure.')}

{f'''
<h2>Ugandan women, field by field</h2>
<p class="h2sub">Wikidata knows {fmt(all_women['women'])} Ugandan women.
{fmt(all_women['in_english'])} have an English article and
{fmt(all_women['in_luganda'])} have a Luganda one, near parity. The
translation backlog is only {fmt(all_women['en_not_lg'])} people. The real gap
is that {fmt(all_women['no_article_anywhere'])} of them
({pct(all_women['no_article_anywhere'], all_women['women'])}%) have no article
in any language at all.</p>

<div class="tiles">
  <div class="tile">
    <p class="k">Ugandan women in Wikidata</p>
    <div class="v">{fmt(all_women['women'])}</div>
    <p class="d">by citizenship</p>
  </div>
  <div class="tile">
    <p class="k">To translate into Luganda</p>
    <div class="v">{fmt(all_women['en_not_lg'])}</div>
    <p class="d">English article exists, Luganda does not</p>
  </div>
  <div class="tile alarm">
    <p class="k">To write from scratch</p>
    <div class="v">{fmt(all_women['no_article_anywhere'])}</div>
    <p class="d">no article in any language</p>
  </div>
  <div class="tile">
    <p class="k">Luganda vs English</p>
    <div class="v">{fmt(all_women['in_luganda'])} / {fmt(all_women['in_english'])}</div>
    <p class="d">Luganda is at
    {pct(all_women['in_luganda'], all_women['in_english'])}% of English coverage</p>
  </div>
</div>

<div class="callout">
  <strong>For Ugandan women, Luganda Wikipedia has essentially caught up with
  English{', and in football it is ahead' if football and football['in_luganda'] > football['in_english'] else ''}.</strong>
  {f"Luganda carries {fmt(football['in_luganda'])} Ugandan women footballers to English's {fmt(football['in_english'])}, and " if football else ''}{fmt(d['women_lg_only'])}
  Ugandan women have a Luganda article and no English one at all.
  {f"These are not placeholder stubs: across all {fmt(lg_sizes.get('measured'))} Luganda women's biographies the median length is {fmt(lg_sizes.get('median_bytes'))} bytes, and only {lg_sizes.get('pct_stubs')}% fall under 2&nbsp;KB against {stub_rate_lg:.0f}% for Luganda's Uganda articles overall." if lg_sizes else ''}
  The pattern is consistent with a deliberate editing campaign rather than
  incidental growth, though this analysis measures the outcome and not the
  cause.
</div>

{card('Ugandan women by field',
      'For each field: how many have an English article, a Luganda article, '
      'and how many have no article anywhere. The third bar is the backlog.',
      'chart-women-fields',
      table_view(['Field', 'Women', 'In English', 'In Luganda',
                  'English but not Luganda', 'No article anywhere',
                  '% in Luganda'],
                 [[esc(r['field']), fmt(r['women']), fmt(r['in_english']),
                   fmt(r['in_luganda']), fmt(r['en_not_lg']),
                   fmt(r['no_article_anywhere']), f"{r['pct_in_luganda']}%"]
                  for r in d['women_fields']], align_right=(1, 2, 3, 4, 5, 6)),
      note='Each woman is counted in one primary field, chosen by priority: a '
           'specific sport wins over a general role, since "politician" is '
           'often one of several hats a public figure wears. Full occupation '
           'lists are kept in the CSV exports.')}

<section class="card">
  <div class="card-head"><div>
    <h3>Translate into Luganda</h3>
    <p class="sub">All {fmt(all_women['en_not_lg'])} Ugandan women with an
    English article and no Luganda one, most-read first. This is the entire
    backlog, not a sample of it.</p>
  </div></div>
  {women_table(d['women_translate'], 'translate')}
</section>

<section class="card">
  <div class="card-head"><div>
    <h3>Write from scratch</h3>
    <p class="sub">Top 25 of {fmt(all_women['no_article_anywhere'])} Ugandan
    women with no article in any language, ranked by how much Wikidata already
    records about them: the better documented she is, the easier she is
    to source.</p>
  </div></div>
  {women_table(d['women_create'], 'create')}
</section>
''' if all_women else ''}

{(card('Uganda next to comparable countries',
       'Wikidata items about each country holding an article in at least one '
       'language. Uganda is highlighted.',
       'chart-peers',
       table_view(['Country', 'With an article', 'In English', 'Biographies',
                   '% women'],
                  [[esc(r['country']), fmt(r['items_with_article']),
                    fmt(r['in_enwiki']), fmt(r['biographies']),
                    f"{r['pct_women']}%"] for r in d['peers']],
                  align_right=(1, 2, 3, 4)),
       note='A country with a larger diaspora, an older Wikipedia community or '
            'more aggressive bot imports scores higher for reasons unrelated to '
            'how well it is actually described. Read as an order of magnitude, '
            'not a league table.') +
      card('Share of women among biographies, by country',
           'The same peer set measured on gender balance rather than volume.',
           'chart-peer-women',
           table_view(['Country', 'Biographies', 'Women', '% women'],
                      [[esc(r['country']), fmt(r['biographies']),
                        fmt(r['women_biographies']), f"{r['pct_women']}%"]
                       for r in d['peers']], align_right=(1, 2, 3))))
     if d['peers'] else ''}

<h2>Method</h2>
<p class="h2sub">Seven independent strategies propose items for the corpus; the
number that agree on an item is a confidence signal, the role
<code>num_retrieval_strategies</code> plays in the Diversity Observatory.</p>

{card('Items proposed per retrieval strategy',
      'Strategies overlap heavily, so the corpus is their union, not their sum.',
      'chart-strategies',
      table_view(['Strategy', 'Items proposed'],
                 [[esc(r['strategy']), fmt(r['n'])] for r in d['strategies']],
                 align_right=(1,)))}

{card('The structured-data mass, by item type',
      'Uganda items with no article in any language, beside those that have one. '
      'These are excluded from the corpus above.',
      'chart-wdtypes',
      table_view(['Item type', 'No article anywhere', 'Has an article'],
                 [[esc(r['type_label']), fmt(r['no_article']),
                   fmt(r['with_article'])] for r in d['wd_types']],
                 align_right=(1, 2)),
      note='Treating these as a translation backlog would put roughly 15,000 '
           'primary schools at the top of every worklist. Uganda is well '
           'described as a database and thinly described as an encyclopedia; '
           'that is a data-quality finding, not a writing task.')}

<footer>
  <p><strong>How this was built.</strong> The corpus is Wikidata items about
  Uganda holding at least one Wikipedia sitelink, gathered by seven strategies
  over the Wikidata Query Service, with article sizes from the MediaWiki API and
  pageviews from the Wikimedia REST API.</p>
  <p><strong>Worklist eligibility.</strong> The corpus of {fmt(ccc)} is built for
  recall; the worklists are built for precision. Only the
  {fmt(d['core_eligible'])} topics with a <em>structural</em> Wikidata link to
  Uganda (its country, a location inside it, Ugandan citizenship, or
  birth or death there) are eligible. The weaker signals earn their place
  in the corpus but not on a worklist: a cross-border ethnicity pulls in Kenyan
  athletes, and an &ldquo;… in Uganda&rdquo; redirect pulled in Elizabeth II.
  Places reached by country must also be in Uganda <em>and only</em> Uganda,
  since the Nile counts Uganda among its countries and was lending a Ugandan
  connection to everyone who ever drowned in it. The cost is real in the other
  direction too: a genuinely Ugandan topic known only by keyword, such as the
  Entebbe raid, sits in the corpus with <code>is_core=0</code> and off the
  worklists. Filter <code>ug_ccc_full_corpus.csv</code> on that column to
  choose your own balance.</p>
  <p><strong>Other limits.</strong> Recall is a floor, not an exact count.
  Unlike the Diversity Observatory, this pipeline has no trained classifier, so
  culturally Ugandan topics with no Wikidata link to Uganda are under-counted.
  Pageviews are fetched for the top {fmt(config.PAGEVIEW_TOP_N)} topics by
  edition count, so demand ranking is reliable at the head of the worklists and
  thin in the tail. The bot/human distinction in the coverage chart is a
  per-edition judgement, not a per-article test. The keyword search returns a
  slightly different set between runs, so corpus totals move by a few dozen
  items cycle to cycle.</p>
  <p><strong>Reproduce.</strong> <code>python src_data/run_all.py</code> then
  <code>python src_viz/build_dashboard.py</code>. Stages checkpoint per month,
  so a new cycle refreshes everything. Full corpus and every table are in
  <code>data/*.csv</code>.</p>
  <p><strong>What to do about it.</strong> This page is the evidence. The
  recommendations that follow from it (prioritised, with a 90-day
  sequence and a baseline to measure against) are on the
  <a href="{config.page_href('plan')}">action plan</a>.</p>
  <p>Modelled on the <a href="https://meta.wikimedia.org/wiki/Wikipedia_Diversity_Observatory"
  target="_blank" rel="noopener">Wikipedia Diversity Observatory</a> by Marc
  Miquel and David Laniado. Source data from Wikidata (CC0) and Wikipedia
  (CC BY-SA).</p>
</footer>
</div>
<div class="tip" id="tip"></div>

<script>
const DATA = {payload};
const tip = document.getElementById('tip');

function showTip(evt, html) {{
  tip.innerHTML = html; tip.style.opacity = '1';
  const pad = 14, r = tip.getBoundingClientRect();
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - pad;
  if (y + r.height > innerHeight - 8) y = evt.clientY - r.height - pad;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}}
const hideTip = () => {{ tip.style.opacity = '0'; }};

function palette() {{
  const t = document.documentElement.dataset.theme;
  const dark = t === 'dark' ||
    (!t && matchMedia('(prefers-color-scheme: dark)').matches);
  return dark ? DATA.dark : DATA.light;
}}

const NS = 'http://www.w3.org/2000/svg';
function svgEl(tag, attrs) {{
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  return n;
}}
const nf = new Intl.NumberFormat('en-US');

/* 4px rounded data-end; the baseline end stays square. */
function barPath(x, y, w, h, r) {{
  r = Math.max(0, Math.min(r, w, h / 2));
  if (w <= 0.6) return `M${{x}} ${{y}} L${{x}} ${{y + h}} Z`;
  return `M${{x}} ${{y}} H${{x + w - r}} A${{r}} ${{r}} 0 0 1 ${{x + w}} ${{y + r}}`
       + ` V${{y + h - r}} A${{r}} ${{r}} 0 0 1 ${{x + w - r}} ${{y + h}} H${{x}} Z`;
}}

/* Horizontal bars, 1..3 series grouped. r.v is a number or an array. */
function hbar(mountId, rows, opts) {{
  const mount = document.getElementById(mountId);
  if (!mount || !rows || !rows.length) return;
  mount.textContent = '';
  const P = palette();
  const o = Object.assign({{
    labelW: 96, valueW: 78, rowH: 30, pad: 8, W: 780,
    fmt: v => nf.format(v), suffix: '', names: [], ordinal: false
  }}, opts || {{}});
  const colors = o.colors || [P.s1, P.s2, P.s3];
  const nSeries = Array.isArray(rows[0].v) ? rows[0].v.length : 1;

  const plotW = o.W - o.labelW - o.valueW;
  const H = o.pad * 2 + rows.length * o.rowH;
  const svg = svgEl('svg', {{
    viewBox: `0 0 ${{o.W}} ${{H}}`, role: 'img',
    'aria-label': o.aria || 'bar chart'
  }});
  const max = Math.max(...rows.map(r =>
    Array.isArray(r.v) ? Math.max(...r.v) : r.v)) || 1;
  const sx = v => Math.max(0, (v / max) * plotW);

  svg.appendChild(svgEl('line', {{
    x1: o.labelW, y1: o.pad - 3, x2: o.labelW,
    y2: o.pad + rows.length * o.rowH - 3,
    stroke: P.baseline, 'stroke-width': 1
  }}));

  rows.forEach((r, i) => {{
    const top = o.pad + i * o.rowH;
    const lt = svgEl('text', {{
      x: o.labelW - 10, y: top + o.rowH / 2, 'text-anchor': 'end',
      'dominant-baseline': 'central', fill: P.text2, 'font-size': 12.5
    }});
    lt.textContent = r.label;
    svg.appendChild(lt);

    const vals = Array.isArray(r.v) ? r.v : [r.v];
    const gap = 2;
    const bh = nSeries === 1 ? 14
      : Math.max(6, Math.floor((o.rowH - 10 - gap * (nSeries - 1)) / nSeries));
    const block = bh * nSeries + gap * (nSeries - 1);

    vals.forEach((v, k) => {{
      const y = top + (o.rowH - block) / 2 + k * (bh + gap);
      let col;
      if (nSeries > 1) col = colors[k];
      else if (o.ordinal) col = P.ord[Math.min(i, P.ord.length - 1)];
      else col = (r.hi === false) ? P.neutral : (r.hi ? P.s1 : colors[0]);
      const label = nSeries > 1
        ? `<b>${{nf.format(v)}}</b> &middot; ${{o.names[k] || ''}}<br>${{r.label}}`
        : `<b>${{o.fmt(v)}}${{o.suffix}}</b><br>${{r.label}}`;
      const p = svgEl('path', {{
        d: barPath(o.labelW, y, sx(v), bh, 4), fill: col
      }});
      p.addEventListener('mousemove', e => showTip(e, label));
      p.addEventListener('mouseleave', hideTip);
      svg.appendChild(p);
    }});

    /* Full-width hit band so hairline bars stay hoverable. */
    const summary = nSeries > 1
      ? vals.map((v, k) => `${{o.names[k] || ''}} <b>${{nf.format(v)}}</b>`).join('<br>')
      : `<b>${{o.fmt(vals[0])}}${{o.suffix}}</b>`;
    const hit = svgEl('rect', {{
      x: o.labelW, y: top, width: plotW, height: o.rowH, fill: 'transparent'
    }});
    hit.addEventListener('mousemove', e =>
      showTip(e, `${{r.label}}<br>${{summary}}`));
    hit.addEventListener('mouseleave', hideTip);
    svg.appendChild(hit);

    /* Direct value labels - text ink, never the series color. */
    const text = nSeries > 1
      ? vals.map(v => nf.format(v)).join(' / ')
      : o.fmt(vals[0]) + o.suffix;
    const vt = svgEl('text', {{
      x: o.labelW + Math.max(...vals.map(sx)) + 9, y: top + o.rowH / 2,
      'dominant-baseline': 'central', fill: P.text2, 'font-size': 12,
      'font-variant-numeric': 'tabular-nums'
    }});
    vt.textContent = text;
    svg.appendChild(vt);
  }});

  mount.appendChild(svg);

  if (nSeries > 1 && o.names.length) {{
    const lg = document.createElement('div');
    lg.className = 'legend';
    lg.innerHTML = o.names.map((nm, k) =>
      `<span><i class="swatch" style="background:${{colors[k]}}"></i>${{nm}}</span>`)
      .join('');
    mount.prepend(lg);
  }}
}}

function renderAll() {{
  const C = DATA.charts;
  hbar('chart-composition', C.composition, {{
    labelW: 74, valueW: 150, rowH: 38,
    names: ['People', 'Places &amp; nature', 'Everything else'],
    aria: 'Composition of each edition\\u2019s Uganda content'
  }});
  hbar('chart-coverage', C.coverage, {{
    labelW: 90, aria: 'Uganda articles per Wikipedia edition'
  }});
  hbar('chart-spread', C.spread, {{
    labelW: 132, ordinal: true, aria: 'Corpus by number of editions'
  }});
  hbar('chart-gender', C.gender, {{
    labelW: 96, valueW: 116, rowH: 34, names: ['Men', 'Women'],
    aria: 'Ugandan biographies by gender'
  }});
  hbar('chart-peers', C.peers, {{
    labelW: 108, aria: 'Items with an article, by country'
  }});
  hbar('chart-peer-women', C.peerWomen, {{
    labelW: 108, valueW: 62, suffix: '%', fmt: v => Number(v).toFixed(1),
    aria: 'Share of women among biographies, by country'
  }});
  hbar('chart-women-fields', C.womenFields, {{
    labelW: 168, valueW: 152, rowH: 40,
    names: ['In English', 'In Luganda', 'No article anywhere'],
    aria: 'Ugandan women by field and article status'
  }});
  hbar('chart-strategies', C.strategies, {{
    labelW: 136, aria: 'Items proposed per retrieval strategy'
  }});
  hbar('chart-wdtypes', C.wdTypes, {{
    labelW: 172, valueW: 128, rowH: 34,
    names: ['No article anywhere', 'Has an article'],
    colors: [palette().s2, palette().s1],
    aria: 'Uganda items without an article, by type'
  }});
}}
renderAll();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', renderAll);

document.querySelectorAll('.card').forEach(c => {{
  const btn = c.querySelector('.toggle');
  const tv = c.querySelector('.tableview');
  const ch = c.querySelector('.chart');
  if (!btn) return;
  if (!tv) {{ btn.remove(); return; }}
  btn.addEventListener('click', () => {{
    const on = btn.getAttribute('aria-pressed') === 'true';
    btn.setAttribute('aria-pressed', String(!on));
    tv.hidden = on;
    if (ch) ch.hidden = !on;
    btn.textContent = on ? 'Table' : 'Chart';
  }});
}});
</script>
"""


def main():
    conn = sqlite3.connect(config.DB_FILE)
    data = load(conn)
    conn.close()
    text = build(data)
    os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
    with open(TOKENS_FILE, 'w', encoding='utf-8') as handle:
        handle.write(tokens_css())
    with open(OUT_FILE, 'w', encoding='utf-8') as handle:
        handle.write(text)
    print(f'wrote {TOKENS_FILE}')
    print(f'wrote {OUT_FILE} ({len(text) // 1024} KB)')


if __name__ == '__main__':
    main()
