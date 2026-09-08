# -*- coding: utf-8 -*-
"""Configuration for the Uganda Content Gap Observatory.

Scope choice that shapes everything downstream: the CCC (Cultural Context
Content) is defined over Wikidata items that carry at least one Wikipedia
sitelink. Uganda has ~68k items with country=Uganda, but ~85% of them are
bulk-imported school/village/parish records with no article in any language.
Counting those as "missing" would drown the signal, so they are tracked
separately as the wikidata_only mass instead.
"""

import os

# ---------------------------------------------------------------- paths
PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_PATH, 'data')
DOCS_PATH = os.path.join(PROJECT_PATH, 'docs')
DB_FILE = os.path.join(DATA_PATH, 'uganda_diversity.db')

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(DOCS_PATH, exist_ok=True)

# ---------------------------------------------------------------- published pages
# The two pages, which cross-link to each other as tabs. Kept here so the tab
# bar is defined in one place rather than in each page. The href is the sibling
# filename, so the pair browses from disk with no scripting and no account.
PAGES = [
    ('dashboard', 'Findings &amp; data', 'uganda_content_gap.html'),
    ('plan', 'Action plan', 'uganda_gap_action_plan.html'),
]


def page_href(key):
    """The sibling filename for a page key, for linking between the two pages."""
    return next(href for k, _label, href in PAGES if k == key)


def tab_bar(current):
    """Render the shared tab bar, marking `current` as the active page."""
    tabs = []
    for key, label, href in PAGES:
        if key == current:
            tabs.append(f'<span class="tab active" aria-current="page">{label}</span>')
        else:
            tabs.append(f'<a class="tab" href="{href}">{label}</a>')
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
