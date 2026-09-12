# Uganda Content Gap Observatory

A single-country content gap analysis for **Uganda**, modelled on the
[Wikipedia Diversity Observatory](https://meta.wikimedia.org/wiki/Wikipedia_Diversity_Observatory)
(WDO) by Marc Miquel and David Laniado.

WDO answers "which topics from each language's cultural context are missing
from other languages?" across ~300 Wikipedia editions. This project asks the
same question about one territory, and answers it from **public endpoints
only** - no Wikimedia Cloud VPS account, no database replicas, no dumps.

## What it measures

**Uganda CCC** (Cultural Context Content) is the set of Wikidata items about
Uganda that have at least one Wikipedia article. Six SPARQL strategies plus a
title-keyword search each independently propose items; the number of
strategies that agree becomes a confidence signal, playing the same role as
`num_retrieval_strategies` in WDO.

From that corpus the pipeline computes:

| Output | Question it answers |
|---|---|
| `ug_edition_composition` | **What is each edition's Uganda content actually made of?** |
| `ug_coverage_by_language` | How much Uganda content does each of ~340 editions carry? |
| `ug_spread_buckets` | How far does a Uganda topic travel across languages? |
| `ug_missing_lg`, `ug_missing_sw` | What should Luganda / Swahili Wikipedia write next? |
| `ug_incomplete_lg`, `ug_incomplete_sw` | Which local articles exist but only as stubs? |
| `ug_gender_gap`, `ug_women_biographies` | How lopsided are Ugandan biographies? |
| `ug_admin_units_coverage`, `ug_geolocated_items` | Which parts of Uganda are covered at all? |
| `ug_topical_coverage` | Which subject areas are strong or absent? |
| `ug_peer_countries` | How does Uganda compare with Kenya, Tanzania, Ghana...? |
| `ug_wikidata_only_by_type` | What exists as structured data but as no article anywhere? |
| `ug_ccc_full_corpus` | The flat corpus, for your own slicing |
| `ug_women_by_field` | Ugandan women per field: in English, in Luganda, in neither |
| `ug_women_translate_to_lg` | Women with an English article and no Luganda one |
| `ug_women_create_from_scratch` | Women with no article in any language |
| `ug_women_translate_<field>`, `ug_women_create_<field>` | The same two lists split per field |
| `ug_women_office_holders` | Every woman with a Ugandan public office recorded |
| `ug_women_office_no_article`, `ug_women_office_with_article` | Office holders Wikipedia has and has not written about |
| `ug_women_office_translate_to_lg` | Office holders with an English article and no Luganda one |
| `ug_women_office_by_position` | Coverage per office, so a campaign can target one |

### Two different worklists for women

`women_analysis.py` treats these as separate problems, because the work is
different:

- **translate**: an English article exists, a Luganda one does not. The
  source text is already written. Ranked by English pageviews.
- **create**: no article in any language. Nothing exists to translate from.
  Ranked by Wikidata statement count, since the better documented she already
  is, the easier she is to source.

A woman is counted in one primary field, chosen by priority (a specific sport
beats a general role, because "politician" is often one of several hats).
Full occupation lists survive in the CSVs.

"Ugandan woman" means Wikidata `P27 = Uganda` and `P21 = female`. Citizenship
alone is deliberate: adding a birth-place branch with the single-country guard
makes the query time out on WDQS, and citizenship is the standard reading.

### Starter lists for Incubator Wikipedias

Luganda is not the only Ugandan Wikipedia for much longer:

| Language | Status | Incubator |
|---|---|---|
| **Runyankore** (nyn) | Approved by the Language Committee, awaiting creation by developers (T429189) | [Wp/nyn](https://incubator.wikimedia.org/wiki/Wp/nyn) |
| **Acholi** (ach) | Eligible test wiki, request pending on Meta-Wiki | [Wp/ach](https://incubator.wikimedia.org/wiki/Wp/ach) |

`incubator_starter.py` generates a day-one worklist for each: Uganda-wide
essentials plus topics from the sub-region where the language is actually
spoken (Ankole for Runyankore, the Acholi sub-region for Acholi). The regional
half is the point: it is the content no other edition has a reason to write.

**Important limitation:** Incubator test wikis live at
`incubator.wikimedia.org/wiki/Wp/<code>/...` and are not Wikidata sitelinks, so
existing test-wiki content is invisible to this pipeline. These lists are
proposals, not gap measurements. Check them against the test wiki before
assigning work.

### The finding that shaped the report

Article counts alone are actively misleading here. The edition holding the most
Uganda articles is **Cebuano** (ahead of English), and it contains
**2** biographies of Ugandans; its Uganda corpus is thousands of bot-generated
streams, hills and sub-counties. **Luganda** is the mirror image: the most
Uganda-focused edition in the world by share, and roughly three-quarters
biographies with almost no geography.

That is why `ug_edition_composition` exists, and why the report leads with
composition rather than volume. Two editions with similar article counts can
describe entirely different countries.

## Layout

Deliberately parallel to WDO's own split between data and presentation.

```
src_data/
  config.py              territory constants, target wikis, tuning
  ug_utils.py            WDQS access, chunking, SQLite, run checkpointing
  content_retrieval.py   stage 1 - build the CCC and its features
  article_features.py    stage 2 - article size, reader demand, edition stats
  stats_generation.py    stage 3 - gap metrics and ranked worklists
  women_analysis.py      stage 4 - Ugandan women by field, two worklists
  incubator_starter.py   stage 5 - day-one lists for Incubator Wikipedias
  office_analysis.py     stage 6 - women in public office, from P39
  roster_check.py        stage 7 - check the rosters against Wikimedia
  topic_import.py        stage 8 - import last year's topic areas
  topic_verify.py        stage 9 - structural check on what it imported
  osm_features.py        stage 10 - OpenStreetMap's Uganda, cross-referenced
  official_registers.py  stage 11 - UBOS census and EC election registers
  run_all.py             orchestrator
  reset_stage.py         clear a stage's checkpoint so it re-runs
src_viz/                 SQL in, JSON view models out, HTML out
  data_dashboard.py      queries behind the findings page
  data_edition.py        queries behind the largest-edition page
  data_offices.py        queries behind the women-in-office page
  data_undocumented.py   queries behind the roster page
  data_topics.py         last year's readership joined to our coverage
  data_osm.py            OSM features beside Wikidata and Wikipedia
  data_registers.py      UBOS and EC registers beside Wikipedia
  dashboard_view.py      the dashboard's view model, much the largest
  export_data.py         writes data/ui/*.json and assets/css/tokens.css
  tokens.py              the palette, and the CSS variables generated from it
  build_pages.py         renders data/ui/*.json to the pages in the root
  page_*.py              one renderer per page
  render.py              tab bar, tiles, bars, tables, filter controls
  charts.py              the SVG bar chart and its card
assets/js/app.js         filters and chart toggles, plain browser JS
assets/css/
  tokens.css             design tokens, generated from tokens.py
  shell.css              chrome shared by all pages (reset, tab bar, links)
  components.css         tiles, bars, filters, list table (the list pages)
  dashboard.css          uganda_content_gap.html
  plan.css               uganda_gap_action_plan.html
  edition.css            uganda_largest_edition.html
  offices.css            uganda_women_in_office.html
  undocumented.css       uganda_undocumented_women.html
  topics.css             uganda_topic_areas.html
  osm.css                uganda_openstreetmap.html
  registers.css          uganda_official_registers.html
data/                    uganda_diversity.db + CSV exports
  roster_women_offices.csv   hand-maintained input for stage 7
  roster_men_offices.csv     the same, for the men's cohort
  topic_areas.csv            imported topic axis, written by stage 8
training data/           last cycle's per-category exports, input to stage 8
```

Three pages, all plain HTML linking those sheets and cross-linking by
filename, so the set opens straight from disk:

| Page | What it is |
|---|---|
| `uganda_content_gap.html` | the findings and charts, generated |
| `uganda_gap_action_plan.html` | the recommendations, hand-maintained |
| `uganda_largest_edition.html` | every Uganda article in the largest edition, generated |
| `uganda_women_in_office.html` | Ugandan women in public office and their article status, generated |
| `uganda_undocumented_women.html` | women in senior office with no Wikimedia record, generated |
| `uganda_undocumented_men.html` | men in senior office with no Wikimedia record, generated |
| `uganda_topic_areas.html` | reader demand by topic area against Luganda coverage, generated |
| `uganda_openstreetmap.html` | OSM features with no Wikidata or Wikipedia record, generated |
| `uganda_official_registers.html` | UBOS and EC register entries with no article, generated |

`tokens.css` is generated: the palette lives in `tokens.py` because the
chart bars reference it too, so the build writes it out rather than keeping
two copies. The tab bar comes from `config.PAGES`, so the generated pages pick up
a new page automatically; the hand-maintained plan page needs its nav edited.

The women-in-office page answers a different question from stage 4's field
breakdown: not what women work in, but who actually held office, taken from
Wikidata `P39` and split into those with an article, those with none, and
those needing a Luganda translation. Seniority is inferred by matching the
position label, and the keyword lists live in `config.OFFICE_TIERS`.

The edition page is the drill-down behind the dashboard's claim that the
largest Uganda encyclopedia holds two biographies. It lists all of that
edition's Uganda articles with the Wikidata type that put each one there, and
it reads the ranking from the data rather than naming an edition, so it
follows whichever edition leads in a given cycle.

## Reusing the previous cycle's analysis

`training data/` holds last year's content gap analysis: eleven per-category
exports of Uganda pages on English Wikipedia, each row carrying a Wikidata QID
and a pageview total, plus a write-up ranking the top ten per category.

It contributes the one thing this project had no equivalent of. Our own
categorisation is by Wikidata type (stream, hill, human) and, for women, by
field; none of that says "health" or "education", which is how a User Group
actually plans a campaign. So the topic areas are imported rather than
re-derived, and `uganda_topic_areas.html` is what the two halves produce
together:

| | their analysis | this project | the page |
|---|---|---|---|
| topic axis | 11 reader-facing areas | Wikidata types only | theirs |
| editions | English only | all 343 | ours |
| demand | pageviews per article | top 2,000 by edition count | theirs, labelled as theirs |
| coverage | not asked | every edition, per topic | ours |
| precision | category membership | structural Wikidata link | ours, applied to theirs |

Three things the join settles that neither half could alone:

- **81% of the readership their analysis measured, on topics that really are
  Ugandan, is on topics with no Luganda article.** Their ranking already knew
  what readers want; it never asked whether Uganda's own language had it.
- **74% of the views they reported are on topics with no structural link to
  Uganda.** Their single largest row is Elizabeth II at 8.6 million views,
  filed under "Governance in Uganda", which is 62% of everything they
  measured, while
  their write-up credits that dominance to Idi Amin and Museveni, who sit in a
  different file. Mount Kenya, Ngorongoro, Mount Meru and Virunga are filed
  under Geography of Uganda. This project already guards against that trap:
  Elizabeth II reaches the corpus by title keyword and is held off every
  worklist for it.
- **Their lists audit our recall.** Of their 1,194 articles, 145 are absent
  from our corpus; asking Wikidata directly settles that 2 are genuine misses
  worth adding (Lukiiko, Rubona in Bunyangabu) and 143 have no Ugandan link at
  all.

The import drops their 847 Category and 15 Template rows, which are navigation
rather than content, and keeps the 1,353 article rows. Their view window is
undocumented and runs roughly twice ours on the 191 topics both measured, so
the two are never added together. Replacing the folder with a fresh export is
how the page moves to a new cycle.

## The two roster pages

Every other page starts from Wikidata and asks what Wikipedia is missing.
Neither can answer "who is missing from Wikidata", because someone absent from
both is invisible to a query against either. So these two start from the other
end: a roster of real appointments gathered outside Wikimedia, which
`roster_check.py` then looks up name by name.

The cohorts live in `config.ROSTERS`, one CSV each, with the same columns:

    name, office, organisation, sector, rank, source_url

`source_url` is mandatory. It is what makes a row checkable by someone else,
and what an editor needs before writing anything. One stage checks every
cohort and one renderer draws both pages; what differs is the copy, which
lives in `COHORT_COPY` in `export_data.py`.

The men's roster covers the armed forces, the police, the bench, faith
leadership, media, sport, state enterprise, telecom and the revenue service,
seeded from official leadership pages (`updf.go.ug`, `upf.go.ug`,
`unoc.co.ug`, `mtn.co.ug`, `ura.go.ug`) and Ugandan press reporting.

What the check found, of 58 names:

- **37 have no Wikidata item and no Wikipedia article in any language.**
- **All 12 senior police names are absent**, including Inspector General of
  Police Abbas Byakagaba and his deputy James Ochaya. So is Jack Bakasumba,
  Chief of Joint Staff of the UPDF.
- Coverage thins a rung down: 14% of the people who head an institution are
  missing, against 78% of the executives and officers who run it for them.
- A pattern worth noting: searching English Wikipedia for Byakagaba surfaces
  his predecessor Martin Okoth Ochola, and for Don Wanyama of Vision Group it
  surfaces his predecessor Robert Kabushenga. Both predecessors have articles.
  Coverage of those offices stopped at the last handover.

The same caveats apply to both pages. Holding a big office is not the same as
being notable: Wikipedia needs significant coverage in independent reliable
sources, and an employer's own leadership page is not that. Wikidata's bar is
lower, which is why "item but no article" is reported separately. And a status
of "nothing on Wikimedia" is a statement about a search, not proof: a name
spelled differently on Wikidata will read as absent.

## The third map: OpenStreetMap

OSM is the most complete map of Uganda on the ground, and it is a different
corpus from either Wikidata or Wikipedia. Features there can carry a
`wikidata` and a `wikipedia` tag, so the overlap is machine-readable, and
`osm_features.py` reads it in four states: both tags, one tag, the other tag,
or neither.

**The distinction that matters on this page.** A missing tag is a statement
about OSM's tagging, not proof that Wikimedia holds nothing. Uganda's OSM data
is largely mapped and imported by people who never touch the wiki side, so
untagged is the default rather than the exception. The page therefore reports
two different numbers and never adds them together:

- **the cross-reference gap**, counted over every named feature, which is
  mostly fixable by mappers adding a tag
- **the documentation gap**, where the untagged names in the classes small
  enough to check were asked of Wikidata directly, which is the one that needs
  articles written

Scale, measured before the class list was written: Uganda has **61,061 named
villages** in OSM, 2,445 named hospitals, 854 named primary-road segments, 212
towns and 135 universities. Villages and schools are far too many to ask
Wikidata about name by name in one cycle, so they are reported as a tagging
gap and sampled on the page, with every row in
`data/ug_osm_undocumented.csv`.

Two implementation notes. Roads and rivers arrive as many OSM ways per route,
so linear features are grouped by name and carry a segment count, which is a
rough proxy for length and not a measurement of it: a road split finely scores
higher than a longer road split coarsely. And the fetch checkpoints per class,
because one country-wide Overpass query can take minutes and the public
instances hand out 429s and 504s freely. Three mirrors are tried in turn.

## The government's own registers

Two Ugandan state sources, neither with an API, both parsed straight from the
files they publish:

- **UBOS**, the 2024 census sub-county profiles. An XLSX carrying the whole
  administrative hierarchy: **146 districts, 312 counties, 2,207 sub-counties
  and 10,854 parishes**. The level of each row is encoded in the cell style
  rather than the text, which is how the parser tells them apart; the counts
  it recovers match the ones the census reports.
- **The Electoral Commission**, the schedule of results for directly elected
  members of parliament, 2025/2026. A PDF, but one whose table cells are
  separated by a font marker, which makes the columns recoverable: **348
  constituencies, 1,995 candidate rows, and the winner of each seat**.

Neither needed a new dependency. An XLSX is a zip of XML, and that PDF's
content streams are Flate-coded with the text in ordinary string literals, so
`zipfile`, `zlib` and `re` are enough.

**One source deliberately left out.** The Commission's 2021 results are
published the same way but render their text one glyph at a time with no field
marker, so a name comes out as `O CH ER O J I M BR ICK Y` with no way to tell
a kerning gap from a real space. Publishing mangled names of real people would
be worse than publishing none, so only the 2026 file is used. Adding a PDF
library such as `pdfplumber` would lift that restriction and bring in the
earlier parliaments.

Coverage is decided locally, by matching register names against corpus labels.
Every corpus item has at least one article by construction, so a match means
the entry is described somewhere. The comparison ignores words like district,
county and parish that carry no identifying weight, and it is deliberately
strict: an article filed under another spelling reads as missing, so "no
article" is a search result worth checking rather than proof of absence.

## Running it

```bash
pip install -r requirements.txt
cd src_data
python run_all.py                 # ~15-20 min on a cold cache
python ../src_viz/export_data.py  # SQLite -> data/ui/*.json
python ../src_viz/build_pages.py  # data/ui/*.json -> the pages
```

`export_data.py` reads only `uganda_diversity.db`, so once the pipeline has
run the view models rebuild offline in a second, and `build_pages.py` turns
those into HTML in the project root. Neither step touches the network, and
there is no toolchain to install beyond `requirements.txt`.

Pass page keys to rebuild only some of them, which is worth doing while
iterating on one page:

```bash
python src_viz/build_pages.py dashboard      # skips the 2 MB edition table
```

## The UI

`build_pages.py` renders each page whole, in Python. `render.py` holds the
shared furniture (tab bar, stat tiles, bars, tables, the filter controls),
`charts.py` the SVG bar chart and the card around it, and one `page_*.py` per
page puts those together.

Rendering the whole page rather than mounting anything in the browser is
deliberate, for two reasons that matter here. The pages are opened from disk
and passed around as files, so a blank page without JavaScript would be a real
regression. And the largest of them is a 6,765-row table, which has no
business being built client-side.

`assets/js/app.js` is the only JavaScript, about 150 lines of it, and it adds
behaviour to markup that is already there: the search box and filter chips,
and each chart card's Chart/Table toggle and hover tooltip. Nothing is
re-rendered and no page data is shipped a second time. The filters read
categories from each row's `data-` attributes and search text from its
`textContent`, both already in the document; tooltip text rides on each bar as
a `data-tip` attribute, read by one delegated listener per chart. With
JavaScript off the pages lose the filtering and the toggle, and keep every
number: both the chart and its table are in the markup.

Chart bars are filled with `var(--s1)` and `var(--ord3)` rather than hex
values, so a theme change is resolved by the browser. The previous version had
to redraw every chart on a `prefers-color-scheme` event.

Every stage is checkpointed per calendar month in the `run_log` table, so an
interrupted run resumes instead of restarting, and re-running in a new month
recomputes with fresh data. `--force` recomputes regardless.

To redo one stage only:

```bash
python reset_stage.py --list             # what has run this cycle
python reset_stage.py fetch_pageviews    # clear that stage
python article_features.py               # and re-run it
```

No number in the report is hardcoded: edition sizes and active-editor counts
come from `fetch_edition_stats`, so the write-up stays true after a refresh.

## Ranking

Worklists are ordered by a `priority` score: the mean of two percentile
ranks, one for **importance** (`sitelink_count` - how many editions already
consider the topic article-worthy) and one for **demand** (trailing
`PAGEVIEW_MONTHS` of English Wikipedia pageviews). Using percentile ranks
rather than raw values keeps a handful of very high-traffic articles from
swamping the importance signal.

Pageviews cost one HTTP request per article, so they are fetched only for the
top `PAGEVIEW_TOP_N` items by sitelink count - the range the worklists
actually draw from.

## Two scope decisions worth knowing

**Article-less items are excluded from the CCC.** Uganda has ~68,600 Wikidata
items with `country = Uganda`, but ~85% are bulk-imported primary schools,
villages and parishes with no article in any language. Treating those as
"missing articles" would bury every real finding, so they are counted
separately in `ug_wikidata_only_by_type` - where they are a finding in their
own right.

**Swahili is not used to identify Ugandan content.** It is an official
language of Uganda, but as an East African lingua franca it is spoken far
more widely, and using it as evidence of Ugandan-ness pulls in ~26,600 mostly
Kenyan and Tanzanian items - more than the entire genuine Uganda corpus.
Uganda-specific languages (Luganda, Runyankole, Acholi, Ateso, Lusoga,
Lugbara) contribute 268 items by comparison. Swahili remains a *target* wiki
for the gap analysis; it just is not a signal that a topic is Ugandan.

## How this differs from WDO

| | WDO | This project |
|---|---|---|
| Scope | ~300 language editions | one territory, 3 target wikis |
| Source | Wikimedia dumps + DB replicas | Wikidata Query Service + MediaWiki API |
| CCC decision | RandomForest classifier over ~100 features | agreement between 7 explicit strategies |
| Runs on | Wikimedia Cloud VPS | any laptop |
| Cycle | monthly, multi-day | monthly, ~20 minutes |

The classifier is the real loss. WDO trains per language on manually
assessed ground truth, which catches culturally Ugandan topics carrying no
explicit Wikidata link to Uganda. The keyword strategy here recovers some of
that, but recall is certainly lower. Anything relying on completeness of the
corpus should be read as a floor, not an exact count.

## Licence

Analysis code is free to reuse. Underlying Wikidata and Wikipedia data is
CC0 / CC BY-SA respectively.
