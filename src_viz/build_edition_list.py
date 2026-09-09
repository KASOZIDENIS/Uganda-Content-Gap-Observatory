# -*- coding: utf-8 -*-
"""Render the full item list for the edition holding the most Uganda articles.

The dashboard states that the largest Uganda encyclopedia in the world holds
two biographies. This page is the evidence: every one of that edition's Uganda
articles, with the Wikidata type that put it there.

Which edition that is comes from the data, not from a constant, so the page
follows the ranking if another edition overtakes it in a later cycle.

Reads only SQLite, so it needs no network and no pipeline dependencies.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src_data'))

import config      # noqa: E402
import ug_utils    # noqa: E402
import render      # noqa: E402
from render import esc, fmt   # noqa: E402

OUT_FILE = os.path.join(config.PROJECT_PATH, 'uganda_largest_edition.html')

# Worklist-grade strategies. An item reached only by the weaker ones is in the
# corpus for recall, and is worth flagging here because it is the reason a
# Uganda list can contain Finland.
CORE_STRATEGIES = ('country_wd', 'citizenship_wd', 'location_wd',
                   'birth_death_wd')

# People first, then the buckets that thin out fastest. The ordering is the
# argument: whoever opens this page should hit the biographies immediately.
BUCKET_ORDER = ('people', 'institutions', 'other', 'places')


def load(conn):
    """Everything the page needs, for whichever edition ranks first."""
    languagecode, total = conn.execute("""
        SELECT languagecode, COUNT(DISTINCT qitem) AS n FROM sitelinks
        GROUP BY languagecode ORDER BY n DESC LIMIT 1""").fetchone()

    labels = dict(conn.execute('SELECT qitem, label FROM entity_labels'))
    stats = conn.execute(
        'SELECT articles, active_editors FROM edition_stats WHERE languagecode=?',
        (languagecode,)).fetchone()

    items = []
    for qitem, title, label, sitelinks, gender, types, strategies in conn.execute("""
            SELECT c.qitem, s.title, c.label, c.sitelink_count,
                   c.gender_qid, c.types, c.strategies
            FROM sitelinks s JOIN ccc_items c ON c.qitem = s.qitem
            WHERE s.languagecode = ?""", (languagecode,)):
        type_names = [labels.get(q, q) for q in (types or '').split('|') if q]
        bucket = config.bucket_of(', '.join(type_names), gender is not None)
        items.append({
            'qitem': qitem,
            'title': title,
            'label': label,
            'sitelinks': sitelinks or 0,
            'types': type_names,
            'bucket': bucket,
            'core': any(name in (strategies or '') for name in CORE_STRATEGIES),
        })

    items.sort(key=lambda it: (BUCKET_ORDER.index(it['bucket']),
                               -it['sitelinks'], (it['label'] or it['title'] or '')))

    counts = {b: sum(1 for it in items if it['bucket'] == b) for b in BUCKET_ORDER}

    # The headline is not "how many places" but how few distinct kinds of
    # thing account for nearly all of it, so tally the primary type.
    primary = {}
    for it in items:
        name = it['types'][0] if it['types'] else 'no type recorded'
        primary[name] = primary.get(name, 0) + 1

    return {
        'languagecode': languagecode,
        'total': total,
        'items': items,
        'counts': counts,
        'primary': sorted(primary.items(), key=lambda kv: -kv[1]),
        'edition_articles': stats[0] if stats else None,
        'weak_only': sum(1 for it in items if not it['core']),
        # No English label at all is itself a marker of bulk creation, and at
        # this share a blank cell would read as a rendering fault.
        'unlabelled': sum(1 for it in items if not it['label']),
    }


def wiki_link(languagecode, title):
    url = f'https://{languagecode}.wikipedia.org/wiki/' + str(title).replace(' ', '_')
    return (f'<a href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(title)}</a>')


def type_bars(primary, total, limit=14):
    """The primary-type tally as CSS bars, no JS needed."""
    rows = primary[:limit]
    top = rows[0][1] if rows else 1
    out = ['<div class="bars">']
    for name, count in rows:
        width = 100.0 * count / top
        out.append(
            f'<div class="bar-row"><div class="bar-label">{esc(name)}</div>'
            f'<div class="bar-track"><div class="bar-fill" '
            f'style="width:{width:.1f}%"></div></div>'
            f'<div class="bar-val">{fmt(count)}</div></div>')
    shown = sum(c for _, c in rows)
    out.append('</div>')
    if len(primary) > limit:
        out.append(
            f'<p class="note">These {len(rows)} types account for '
            f'{fmt(shown)} of {fmt(total)} articles '
            f'({100.0 * shown / total:.0f}%). '
            f'The remaining {fmt(total - shown)} are spread over '
            f'{fmt(len(primary) - limit)} further types.</p>')
    return '\n'.join(out)


def item_rows(d):
    """One table row per article. Rendered server-side so the list survives
    with JavaScript off; the filter box only hides rows.

    No per-row search attribute: duplicating each row's text into a data-*
    added roughly half a megabyte to the page, and the filter can read
    textContent once on load instead.
    """
    out = []
    for i, it in enumerate(d['items'], 1):
        types = ', '.join(it['types'][:3]) or 'no type recorded'
        label = (esc(it['label']) if it['label'] else
                 '<span class="nolabel">no English label</span>')
        flag = ('' if it['core'] else
                ' <span class="weak" title="Reached only by a weak retrieval '
                'strategy, so its link to Uganda may be incidental">weak link</span>')
        out.append(
            f'<tr data-bucket="{it["bucket"]}">'
            f'<td class="num dim">{i}</td>'
            f'<td>{wiki_link(d["languagecode"], it["title"])}{flag}</td>'
            f'<td class="dim">{label}</td>'
            f'<td class="dim">{esc(types)}</td>'
            f'<td class="num">{fmt(it["sitelinks"])}</td>'
            f'<td><span class="chip {it["bucket"]}">'
            f'{esc(config.BUCKET_LABELS[it["bucket"]])}</span></td>'
            f'<td class="dim mono">{esc(it["qitem"])}</td></tr>')
    return '\n'.join(out)


def build(d):
    code = d['languagecode']
    counts = d['counts']
    people = counts['people']
    places_share = 100.0 * counts['places'] / d['total'] if d['total'] else 0
    top_type, top_type_n = d['primary'][0] if d['primary'] else ('', 0)
    share_of_edition = (
        f"{100.0 * d['total'] / d['edition_articles']:.1f}% of the edition"
        if d['edition_articles'] else 'share of edition unknown')

    filters = ''.join(
        f'<button type="button" class="chipfilter" data-filter="{b}">'
        f'{esc(config.BUCKET_LABELS[b])} <span class="n">{fmt(counts[b])}</span>'
        f'</button>'
        for b in BUCKET_ORDER if counts[b])

    return f"""{render.head(f'{code}wiki Uganda Articles', 'edition.css')}
<script>document.documentElement.classList.add('js')</script>

<div class="wrap">
{config.tab_bar('edition')}

<header>
  <p class="eyebrow">Uganda content gap analysis &middot; cycle
  {esc(ug_utils.cycle_year_month())}</p>
  <h1>All {fmt(d['total'])} Uganda articles in {esc(code)}wiki, and what
  they are about</h1>
  <p class="lede">{esc(code)}wiki holds more Uganda articles than any other
  Wikipedia edition, including English. {fmt(people)} of them
  {'is a biography' if people == 1 else 'are biographies'}. This page lists
  every one so that claim can be checked rather than taken on trust.</p>
  <p class="stamp"><strong>Every row is generated from the same database as
  the dashboard.</strong> The edition shown is whichever one ranks first this
  cycle, so this page follows the ranking rather than naming an edition in
  advance. Back to the
  <a href="{config.page_href('dashboard')}">findings</a>.</p>
</header>

<h2>The shape of it</h2>
<div class="tiles">
  <div class="tile">
    <p class="k">Uganda articles</p>
    <div class="v">{fmt(d['total'])}</div>
    <p class="d">{esc(share_of_edition)}</p>
  </div>
  <div class="tile alarm">
    <p class="k">Biographies</p>
    <div class="v">{fmt(people)}</div>
    <p class="d">{100.0 * people / d['total'] if d['total'] else 0:.2f}% of the
    Uganda articles</p>
  </div>
  <div class="tile">
    <p class="k">Places &amp; nature</p>
    <div class="v">{fmt(counts['places'])}</div>
    <p class="d">{places_share:.1f}% of the Uganda articles</p>
  </div>
  <div class="tile">
    <p class="k">Commonest single type</p>
    <div class="v">{fmt(top_type_n)}</div>
    <p class="d">{esc(top_type)}</p>
  </div>
</div>

<h2>What the articles are about</h2>
<p class="h2sub">Counted on each item's first Wikidata type. A collection
dominated by streams, hills and sub-counties is the signature of bot
generation from a geographic registry, not of editors choosing what to
write about.</p>
{type_bars(d['primary'], d['total'])}

<h2>Every article</h2>
<p class="h2sub">Sorted so the biographies come first, then by how many
language editions carry the topic. Titles link to {esc(code)}wiki.
{fmt(d['weak_only'])} of these reached the corpus only through a weak
retrieval strategy and are marked accordingly: they are why a Uganda list
can contain a country or a head of state who is not Ugandan.
{fmt(d['unlabelled'])} of them carry no English label in Wikidata at all,
which is its own signal of how they were created.</p>

<div class="controls">
  <input type="search" id="find" class="find"
         placeholder="Filter {fmt(d['total'])} articles by title, English label or type"
         aria-label="Filter articles">
  <div class="chipfilters" role="group" aria-label="Filter by category">
    <button type="button" class="chipfilter active" data-filter="all">All
    <span class="n">{fmt(d['total'])}</span></button>
    {filters}
  </div>
  <p class="count" id="count" aria-live="polite"></p>
</div>

<div class="scroller">
<table class="itemlist">
  <thead><tr>
    <th class="num">#</th><th>{esc(code)}wiki title</th><th>English label</th>
    <th>Wikidata type</th><th class="num">Editions</th><th>Category</th>
    <th>Item</th>
  </tr></thead>
  <tbody id="rows">
{item_rows(d)}
  </tbody>
</table>
</div>

<footer>
  <p><strong>Method.</strong> The corpus is Wikidata items about Uganda
  carrying at least one Wikipedia sitelink; this page is the subset with a
  sitelink to {esc(code)}wiki. Category is assigned by substring-matching the
  item's Wikidata type labels, which is approximate: an airport lands in
  &ldquo;everything else&rdquo; rather than in institutions, for instance.
  Counts here match the dashboard because both use the same rule.</p>
  <p>Article text and titles from Wikipedia (CC BY-SA), structured data from
  Wikidata (CC0). Rebuild with <code>python
  src_viz/build_edition_list.py</code>.</p>
</footer>
</div>

<script>
const rows = Array.from(document.querySelectorAll('#rows tr'));
// One pass over the table builds the search index, so keystrokes never touch
// the DOM for text and the page ships no duplicated row text.
const hay = rows.map(tr => tr.textContent.toLowerCase());
const find = document.getElementById('find');
const count = document.getElementById('count');
const buttons = Array.from(document.querySelectorAll('.chipfilter'));
let bucket = 'all';

function apply() {{
  const q = find.value.trim().toLowerCase();
  let shown = 0;
  for (let i = 0; i < rows.length; i++) {{
    const tr = rows[i];
    const okBucket = bucket === 'all' || tr.dataset.bucket === bucket;
    const okText = !q || hay[i].includes(q);
    const visible = okBucket && okText;
    tr.hidden = !visible;
    if (visible) shown++;
  }}
  count.textContent = shown === rows.length
    ? `showing all ${{shown.toLocaleString()}} articles`
    : `showing ${{shown.toLocaleString()}} of ${{rows.length.toLocaleString()}}`;
}}

find.addEventListener('input', apply);
for (const b of buttons) {{
  b.addEventListener('click', () => {{
    bucket = b.dataset.filter;
    buttons.forEach(x => x.classList.toggle('active', x === b));
    apply();
  }});
}}
apply();
</script>
"""


def main():
    conn = sqlite3.connect(config.DB_FILE)
    data = load(conn)
    conn.close()
    text = build(data)
    with open(OUT_FILE, 'w', encoding='utf-8') as handle:
        handle.write(text)
    print(f"wrote {OUT_FILE} ({len(text) // 1024} KB, "
          f"{data['total']} rows for {data['languagecode']}wiki)")


if __name__ == '__main__':
    main()
