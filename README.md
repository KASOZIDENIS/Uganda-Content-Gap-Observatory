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
  run_all.py             orchestrator
  reset_stage.py         clear a stage's checkpoint so it re-runs
src_viz/
  render.py              esc/fmt and the stylesheet link block, shared
  build_dashboard.py     renders the findings to uganda_content_gap.html
  build_edition_list.py  renders uganda_largest_edition.html
assets/css/
  tokens.css             design tokens, generated from build_dashboard.py
  shell.css              chrome shared by all pages (reset, tab bar, links)
  dashboard.css          uganda_content_gap.html
  plan.css               uganda_gap_action_plan.html
  edition.css            uganda_largest_edition.html
data/                    uganda_diversity.db + CSV exports
```

Three pages, all plain HTML linking those sheets and cross-linking by
filename, so the set opens straight from disk:

| Page | What it is |
|---|---|
| `uganda_content_gap.html` | the findings and charts, generated |
| `uganda_gap_action_plan.html` | the recommendations, hand-maintained |
| `uganda_largest_edition.html` | every Uganda article in the largest edition, generated |

`tokens.css` is generated: the palette lives in `build_dashboard.py` because
the chart JS needs it too, so the build writes it out rather than keeping two
copies. The tab bar comes from `config.PAGES`, so the generated pages pick up
a new page automatically; the hand-maintained plan page needs its nav edited.

The edition page is the drill-down behind the dashboard's claim that the
largest Uganda encyclopedia holds two biographies. It lists all of that
edition's Uganda articles with the Wikidata type that put each one there, and
it reads the ranking from the data rather than naming an edition, so it
follows whichever edition leads in a given cycle.

## Running it

```bash
pip install -r requirements.txt
cd src_data
python run_all.py                 # ~15-20 min on a cold cache
python ../src_viz/build_dashboard.py
python ../src_viz/build_edition_list.py
```

Both builders read only `uganda_diversity.db`, so once the pipeline has run
the pages rebuild offline in a second.

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
