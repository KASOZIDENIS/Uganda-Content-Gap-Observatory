# -*- coding: utf-8 -*-
"""Configuration for the Uganda Content Gap Observatory.

Scope choice that shapes everything downstream: the CCC (Cultural Context
Content) is defined over Wikidata items that carry at least one Wikipedia
sitelink. Uganda has ~68k items with country=Uganda, but ~85% of them are
bulk-imported school/village/parish records with no article in any language.
Counting those as "missing" would drown the signal, so they are tracked
separately as the wikidata_only mass instead.
"""

import datetime
import html
import os

# ---------------------------------------------------------------- cycle
def cycle_year_month():
    """The data cycle a run belongs to, e.g. '2026-09'.

    Lives here rather than in ug_utils so that the page builders can stamp a
    cycle without importing the network layer.
    """
    return datetime.date.today().strftime('%Y-%m')


# ---------------------------------------------------------------- paths
PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_PATH, 'data')
DB_FILE = os.path.join(DATA_PATH, 'uganda_diversity.db')

os.makedirs(DATA_PATH, exist_ok=True)

# ---------------------------------------------------------------- published pages
# The published pages, which cross-link to each other as tabs. Kept here so the
# tab bar is defined in one place rather than repeated in every page. The href is
# the sibling filename, so the set browses from disk with no scripting and no
# account.
PAGES = [
    ('dashboard', 'Findings & data', 'uganda_content_gap.html'),
    ('plan', 'Action plan', 'uganda_gap_action_plan.html'),
    ('edition', 'Largest edition', 'uganda_largest_edition.html'),
    ('topics', 'Topic areas', 'uganda_topic_areas.html'),
    ('osm', 'OpenStreetMap', 'uganda_openstreetmap.html'),
    ('registers', 'Official registers', 'uganda_official_registers.html'),
    ('commons', 'Commons', 'uganda_commons.html'),
    ('folklore', 'Folklore', 'uganda_folklore.html'),
    ('offices', 'Women in office', 'uganda_women_in_office.html'),
    ('undocumented', 'Undocumented women', 'uganda_undocumented_women.html'),
    ('undocumented_men', 'Undocumented men', 'uganda_undocumented_men.html'),
]


def page_href(key):
    """The sibling filename for a page key, for linking one page to another."""
    return next(href for k, _label, href in PAGES if k == key)


def tab_bar(current):
    """Render the shared tab bar, marking `current` as the active page.

    render.tab_bar() renders the same PAGES list from the nav block the
    view models carry; this is the copy the pipeline itself uses.
    """
    tabs = []
    for key, label, href in PAGES:
        safe = html.escape(label)
        if key == current:
            tabs.append(f'<span class="tab active" aria-current="page">{safe}</span>')
        else:
            tabs.append(f'<a class="tab" href="{href}">{safe}</a>')
    return ('<nav class="tabs" aria-label="Uganda content gap pages">'
            + ''.join(tabs) + '</nav>')


# ---------------------------------------------------------------- endpoints
WDQS_ENDPOINT = 'https://query.wikidata.org/sparql'
PAGEVIEWS_API = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article'
CONTACT = 'denis@ripplenami.com'
USER_AGENT = f'UgandaContentGapObservatory/1.0 ({CONTACT}) python-requests'

# ---------------------------------------------------------------- territory
UGANDA = 'Q1036'

# Languages of Uganda that have a live Wikipedia, plus the official language.
# lg = Luganda, sw = Swahili (regional lingua franca), en = official language.
LOCAL_WIKIS = ['lg', 'sw']
REFERENCE_WIKI = 'en'
TARGET_WIKIS = ['en', 'lg', 'sw']

# Ugandan languages without a live Wikipedia, and how far along each one is.
# This is a three-state situation, not a binary one: treating every language
# here as "no project" understates progress and would send advocacy effort to
# the wrong place. Runyankore in particular is already through approval and
# only waiting on developers, so what it needs is content, not campaigning.
UGANDAN_LANGUAGES_WITHOUT_WIKIPEDIA = {
    # code: (name, status, incubator page or None)
    'nyn': ('Runyankore', 'approved',
            'https://incubator.wikimedia.org/wiki/Wp/nyn'),
    'ach': ('Acholi', 'incubating',
            'https://incubator.wikimedia.org/wiki/Wp/ach'),
    'cgg': ('Rukiga', 'none', None),
    'xog': ('Lusoga', 'none', None),
    'laj': ('Lango', 'none', None),
    'teo': ('Ateso', 'none', None),
    'myx': ('Masaaba', 'none', None),
    'ttj': ('Runyoro-Rutooro', 'none', None),
    'lgg': ('Lugbara', 'none', None),
    'alz': ('Alur', 'none', None),
}

# 'approved'   Language Committee has approved it; awaiting developer creation
# 'incubating' active test wiki on Incubator, request pending on Meta-Wiki
# 'none'       no test project found
LANGUAGE_STATUS_LABELS = {
    'approved': 'approved, awaiting creation',
    'incubating': 'in Incubator, request pending',
    'none': 'no project yet',
}


def languages_by_status(status):
    """Names of the Ugandan languages currently at a given project stage."""
    return [name for name, state, _ in UGANDAN_LANGUAGES_WITHOUT_WIKIPEDIA.values()
            if state == status]

# Peer countries for the representation comparison. Chosen as East African
# neighbours plus two larger anglophone African Wikipedia presences.
PEER_COUNTRIES = {
    'Q1036': 'Uganda',
    'Q114': 'Kenya',
    'Q924': 'Tanzania',
    'Q1037': 'Rwanda',
    'Q967': 'Burundi',
    'Q115': 'Ethiopia',
    'Q117': 'Ghana',
    'Q1033': 'Nigeria',
    'Q258': 'South Africa',
}

# Wikidata items for languages spoken *only or mainly* in Uganda, used by
# the language_wd retrieval strategy (works of/about these languages).
#
# Swahili (Q7913) is deliberately excluded. It is an official language of
# Uganda, but it is a regional lingua franca across East Africa, so using it
# to define Ugandan CCC pulls in ~26,600 mostly Kenyan and Tanzanian items -
# more than the entire genuine Uganda corpus. Uganda-specific languages
# contribute 268 items by comparison. Swahili remains a *target* wiki for the
# gap analysis; it is just not evidence that a topic is Ugandan.
UGANDAN_LANGUAGE_QIDS = [
    'Q33368',   # Luganda
    'Q35772',   # Runyankole
    'Q33705',   # Acholi
    'Q35818',   # Ateso
    'Q33587',   # Lusoga
    'Q36377',   # Lugbara
]

# ---------------------------------------------------------------- retrieval
# Title keywords for the keyword_title strategy (mirrors WDO's approach of
# catching articles whose title names the territory or its major places).
TITLE_KEYWORDS = [
    'Uganda', 'Ugandan', 'Kampala', 'Entebbe', 'Buganda', 'Busoga',
    'Bunyoro', 'Toro Kingdom', 'Ankole', 'Karamoja', 'Acholi',
]

# ---------------------------------------------------------------- rosters
# Office holders gathered outside Wikimedia, one file per cohort. A woman or
# man absent from both Wikidata and Wikipedia cannot be found by querying
# either, so the roster is the input and src_data/roster_check.py looks each
# name up. Add a cohort here and it flows through the stage and the pages.
ROSTERS = (
    ('women', 'roster_women_offices.csv', 'Ugandan women in senior office'),
    ('men', 'roster_men_offices.csv', 'Ugandan men in senior office'),
)


def roster_file(cohort):
    for key, name, _label in ROSTERS:
        if key == cohort:
            return name
    raise KeyError(cohort)


# ---------------------------------------------------------------- type buckets
# Wikidata type labels are matched as substrings to sort an item into one of
# four buckets. This lives here rather than in stats_generation because the
# presentation layer classifies rows too, and one keyword list beats two.
PLACE_WORDS = (
    'stream', 'hill', 'river', 'mountain', 'island', 'lake', 'waterfall',
    'settlement', 'village', 'town', 'municipality', 'district', 'sub-county',
    'county', 'parish', 'territorial entity', 'valley', 'swamp',
    'protected area', 'national park', 'peak', 'plain', 'forest',
)
# 'city' is deliberately absent: as a substring it also matches "electricity".
# 'settlement', 'town' and 'municipality' already cover populated places.
INSTITUTION_WORDS = (
    'school', 'university', 'college', 'hospital', 'clinic', 'business',
    'company', 'organization', 'organisation', 'club', 'team', 'bank',
    'agency', 'ministry', 'party', 'church', 'mosque', 'institute',
    'enterprise', 'newspaper', 'radio', 'station', 'hotel',
)

BUCKET_LABELS = {
    'people': 'People', 'places': 'Places & nature',
    'institutions': 'Institutions', 'other': 'Everything else',
}


def bucket_of(type_labels, is_person):
    """Sort one item into people / places / institutions / other."""
    if is_person:
        return 'people'
    joined = (type_labels or '').lower()
    if any(word in joined for word in PLACE_WORDS):
        return 'places'
    if any(word in joined for word in INSTITUTION_WORDS):
        return 'institutions'
    return 'other'


# ---------------------------------------------------------------- offices
# Wikidata records what office someone held as P39 (position held), and the
# position labels are free text, so seniority has to be inferred by matching
# them. Checked in order and the first hit wins, which is what resolves the
# overlaps: "Justice Minister of Uganda" is a cabinet post rather than a
# judicial one, and "permanent representative" is a diplomat rather than an MP.
#
# Anything that matches nothing here is deliberately not called an office.
# That drops academic and corporate roles (dean, chief executive officer,
# managing director), sports captaincies, and ceremonial positions such as
# First Lady, none of which are public office in the sense this page means.
OFFICE_TIERS = (
    ('executive', 'National executive', (
        'president of uganda', 'vice president', 'vice-president',
        'prime minister', 'minister', 'cabinet', 'attorney general')),
    ('judiciary', 'Judiciary', (
        'chief justice', 'justice', 'judge', 'magistrate')),
    ('diplomatic', 'Diplomatic service', (
        'ambassador', 'high commissioner', 'permanent representative',
        'consul', 'envoy')),
    ('legislature', 'Parliament', (
        'parliament', 'speaker', 'leader of opposition', 'representative',
        'senator', 'legislative')),
    ('public_service', 'Public service', (
        'permanent secretary', 'director general', 'director-general',
        'inspector general', 'solicitor general', 'auditor general',
        'commissioner', 'governor')),
    ('local_government', 'Local government', (
        'mayor', 'lc5', 'district chairperson', 'town clerk', 'municipal')),
)

# Tiers that count as holding public office, most senior first. The remainder
# is the 'other' bucket, which the page shows but does not count.
BIG_OFFICE_TIERS = tuple(key for key, _label, _words in OFFICE_TIERS)

TIER_LABELS = dict(
    [(key, label) for key, label, _words in OFFICE_TIERS]
    + [('other', 'Not a public office')])


def office_tier(position_label):
    """Sort one P39 position label into a tier, or 'other'."""
    text = (position_label or '').lower()
    for key, _label, words in OFFICE_TIERS:
        if any(word in text for word in words):
            return key
    return 'other'


def most_senior_tier(position_labels):
    """The most senior tier among the positions one person has held."""
    tiers = {office_tier(name) for name in position_labels}
    for key in BIG_OFFICE_TIERS:
        if key in tiers:
            return key
    return 'other'


# ---------------------------------------------------------------- tuning
SPARQL_CHUNK_SIZE = 700        # QIDs per chunked VALUES query
SPARQL_MIN_CHUNK = 80          # floor when backing off after a timeout
SPARQL_RETRIES = 4
SPARQL_PAUSE = 0.7             # seconds between WDQS calls, be a good citizen

# How many top-ranked articles get per-article pageview lookups. Pageviews
# are one HTTP call per article, so this is capped at what the worklists
# actually need rather than the whole corpus.
PAGEVIEW_TOP_N = 2000
PAGEVIEW_WORKERS = 5          # gentle enough that the API stops 429-ing us
PAGEVIEW_MONTHS = 6            # trailing window for the demand signal
