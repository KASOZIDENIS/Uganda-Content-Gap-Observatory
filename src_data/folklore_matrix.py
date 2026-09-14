# -*- coding: utf-8 -*-
"""Stage 13: folklore of Uganda, on two axes so nothing falls through.

Every other stage in this project asks "what is missing from a list we can
enumerate". Folklore has no such list. There is no query that returns Uganda's
oral traditions, because the thing being counted was never written down in the
first place, and what has been written down is scattered across inventories that
do not talk to each other.

So this stage builds the frame rather than the inventory, and measures Wikimedia
against the frame. Two axes:

  groups    the ethno-linguistic communities, under the four language families
            (Bantu, Nilotic/Luo, Ateker, Central Sudanic). A family axis makes
            "all cultures" checkable instead of aspirational: a community with
            no row is visibly absent rather than quietly forgotten.

  aspects   UNESCO's five domains of intangible cultural heritage as the
            controlled vocabulary, since that is what the heritage institutions
            already use, plus a tangible branch and the Uganda-specific
            sub-domains that the five domains flatten: kingship and titles,
            clans and totems, attire, cuisine, naming systems, traditional
            governance, games.

A cell of the matrix is not a guess. It is the set of English Wikipedia articles
whose title carries the community's name and whose text is about Uganda, sorted
into an aspect by vocabulary. Every number on the page traces to article titles
that can be listed, so a reader can check the cell rather than trust it.

**What this stage does not do.** It does not hold the national inventory. The
Ministry of Gender, Labour and Social Development has run community-based
inventories across more than forty communities, the Cross-Cultural Foundation of
Uganda publishes case studies, UCOMA's community museums hold granular local
records, and UBOS enumerates the communities themselves. None of those publish a
machine-readable inventory, so none are ingested here. They are named in
EXTERNAL_INVENTORIES as reconciliation targets, with their landing pages, and
the page says plainly that they are not yet loaded. An inventory nobody has
loaded must not be presented as one that has been.

    python src_data/folklore_matrix.py
"""

import csv
import os
import re
import time

import config
import ug_utils

SCRIPT = 'folklore_matrix'

EN_API = 'https://en.wikipedia.org/w/api.php'
LG_API = 'https://lg.wikipedia.org/w/api.php'

OUT_ARTICLES = os.path.join(config.DATA_PATH, 'ug_folklore_articles.csv')
OUT_MATRIX = os.path.join(config.DATA_PATH, 'ug_folklore_matrix.csv')
OUT_ANCHORS = os.path.join(config.DATA_PATH, 'ug_folklore_anchors.csv')

PAUSE = 0.08
SEARCH_LIMIT = 50

# ---------------------------------------------------------------- the groups
# key, label, family, search variants. Variants matter because the people, the
# language and the territory are different words in Bantu languages: the Ganda
# people are Baganda, their language Luganda, their kingdom Buganda, and an
# article may be filed under any of them.
FAMILIES = (
    ('bantu', 'Bantu'),
    ('nilotic', 'Nilotic / Luo'),
    ('ateker', 'Ateker / Nilo-Hamitic'),
    ('sudanic', 'Central Sudanic'),
)

GROUPS = (
    ('baganda', 'Baganda', 'bantu', ('Baganda', 'Buganda', 'Luganda', 'Ganda')),
    ('banyoro', 'Banyoro', 'bantu', ('Banyoro', 'Bunyoro', 'Nyoro', 'Runyoro')),
    ('batooro', 'Batooro', 'bantu', ('Batooro', 'Tooro', 'Toro', 'Rutooro')),
    ('basoga', 'Basoga', 'bantu', ('Basoga', 'Busoga', 'Soga', 'Lusoga')),
    ('bakonzo', 'Bakonzo', 'bantu', ('Bakonzo', 'Konjo', 'Konzo', 'Rwenzururu')),
    ('bagisu', 'Bagisu', 'bantu', ('Bagisu', 'Bamasaba', 'Gisu', 'Masaba')),
    ('bakiga', 'Bakiga', 'bantu', ('Bakiga', 'Kiga', 'Rukiga')),
    ('banyankole', 'Banyankole', 'bantu',
     ('Banyankole', 'Ankole', 'Nkore', 'Runyankole')),
    ('bagwere', 'Bagwere', 'bantu', ('Bagwere', 'Gwere', 'Lugwere')),
    ('banyarwanda', 'Banyarwanda', 'bantu', ('Banyarwanda', 'Kinyarwanda')),
    ('bafumbira', 'Bafumbira', 'bantu', ('Bafumbira', 'Kisoro')),
    ('basamia', 'Basamia-Bagwe', 'bantu', ('Samia', 'Bagwe', 'Lusamia')),
    ('banyole', 'Banyole', 'bantu', ('Banyole', 'Nyole', 'Lunyole')),
    ('bamba', 'Bamba', 'bantu', ('Bamba', 'Amba')),
    ('basongora', 'Basongora', 'bantu', ('Basongora', 'Songora')),
    ('batwa', 'Batwa', 'bantu', ('Batwa', 'Twa')),
    ('acholi', 'Acholi', 'nilotic', ('Acholi', 'Acoli')),
    ('lango', 'Lango', 'nilotic', ('Lango', 'Langi')),
    ('alur', 'Alur', 'nilotic', ('Alur',)),
    ('japadhola', 'Japadhola', 'nilotic', ('Japadhola', 'Adhola', 'Padhola')),
    ('kuku', 'Kuku', 'nilotic', ('Kuku',)),
    ('iteso', 'Iteso', 'ateker', ('Iteso', 'Teso', 'Ateso')),
    ('karamojong', 'Karamojong', 'ateker',
     ('Karamojong', 'Karimojong', 'Karamoja')),
    ('kumam', 'Kumam', 'ateker', ('Kumam',)),
    ('pokot', 'Pokot', 'ateker', ('Pokot',)),
    ('sabiny', 'Sabiny', 'ateker', ('Sabiny', 'Sebei', 'Kupsabiny')),
    ('ik', 'Ik', 'ateker', ('Ik people', 'Icetot')),
    ('lugbara', 'Lugbara', 'sudanic', ('Lugbara',)),
    ('madi', "Ma'di", 'sudanic', ("Ma'di", 'Madi')),
    ('kakwa', 'Kakwa', 'sudanic', ('Kakwa',)),
    ('aringa', 'Aringa', 'sudanic', ('Aringa',)),
)

# ---------------------------------------------------------------- the aspects
# key, label, parent UNESCO domain, vocabulary. The Uganda-specific sub-domains
# come first because they are narrower: "clan" should land in clans and totems
# rather than in the social practices domain that contains it.
UNESCO_DOMAINS = (
    ('oral', 'Oral traditions and expressions'),
    ('performing', 'Performing arts'),
    ('social', 'Social practices, rituals and festive events'),
    ('nature', 'Knowledge concerning nature and the universe'),
    ('craft', 'Traditional craftsmanship'),
    ('tangible', 'Tangible heritage'),
)

ASPECTS = (
    # No "queen" or "prince" here: they are generic enough to pull in football
    # clubs and schools, and "Acholi Queens FC" is not a folklore article.
    ('kingship', 'Kingship and titles', 'social',
     r'kabaka|omukama|kyabazinga|omugabe|\brwot\b|\bking\b|kingdom|throne|'
     r'royal|monarch|coronation|chiefdom|\bchief\b'),
    ('clans', 'Clans and totems', 'social', r'\bclans?\b|totem|lineage'),
    ('naming', 'Naming systems', 'oral', r'naming|empaako|praise name'),
    ('attire', 'Attire', 'craft',
     r'gomesi|kanzu|attire|dress|clothing|costume|barkcloth|bark cloth'),
    ('cuisine', 'Cuisine', 'nature',
     r'cuisine|\bfood\b|dish|matoke|luwombo|malwa|\bbrew|banana beer'),
    ('governance', 'Traditional governance', 'social',
     r'lukiiko|governance|council|traditional authority|institution'),
    ('games', 'Games', 'social', r'\bgames?\b|omweso|mweso|wrestling|\bplay\b'),
    ('language', 'Language', 'oral',
     r'language|dialect|orthography|alphabet|grammar|lexicon'),
    ('oral', 'Oral traditions and expressions', 'oral',
     r'oral|folklore|mytholog|legend|folk ?tale|proverb|riddle|storytell|'
     r'epic|poetry|praise|narrative'),
    ('performing', 'Performing arts', 'performing',
     r'music|dance|song|drum|lyre|trumpet|harp|flute|fiddle|ensemble|'
     r'theatre|performance|instrument'),
    ('social', 'Rituals and festive events', 'social',
     r'ritual|ceremon|festival|marriage|wedding|funeral|burial|initiation|'
     r'circumcision|imbalu|cleansing|feast|custom'),
    ('nature', 'Knowledge of nature and the universe', 'nature',
     r'medicine|herbal|healing|divination|rainmak|agricultur|farming|cattle|'
     r'hunting|fishing|calendar|astronom'),
    ('craft', 'Traditional craftsmanship', 'craft',
     r'craft|weav|basket|potter|blacksmith|ironwork|carving|beadwork|\bmat\b|'
     r'smelting'),
    ('tangible', 'Sites, monuments and regalia', 'tangible',
     r'tomb|shrine|palace|monument|heritage site|museum|architecture|regalia|'
     r'\brock art\b'),
    ('people', 'The community itself', 'oral',
     r'people|ethnic|tribe|community'),
)
ASPECT_PATTERNS = tuple((k, re.compile(v, re.I)) for k, _l, _p, v in ASPECTS)

# A community name in the title does not make an article folklore. Football
# clubs, schools, hotels and constituencies carry these names too, and letting
# them through would inflate every cell with things nobody would call heritage.
EXCLUDE = re.compile(
    r'\bF\.?C\.?\b|\bSC\b|football club|\bFC\b|\bInn\b|hotel|airport|'
    r'\bschool\b|college|universit|hospital|\bbank\b|constituency|county|'
    r'district|\bsub-?county\b|diocese|archdiocese|parish|\bairstrip\b|'
    r'\broad\b|\bward\b|\bwar\b|rebellion|insurgency|\bLRA\b|battalion',
    re.I)

# ------------------------------------------------------- authoritative anchors
# The six UNESCO inscriptions. Curated rather than scraped: ich.unesco.org
# renders its element pages in JavaScript and returns HTTP 200 with an empty
# shell for any URL at all, including deliberate nonsense, so a deep link there
# cannot be verified from a script and none is published. Each element's
# Wikimedia coverage IS checked live, which is the part this project measures.
# The Wikidata item for each is curated rather than searched. Searching fails
# both ways on names like these: wbsearchentities matches a prefix, so the full
# title finds nothing, while a distinctive fragment like "Tombs" returns
# Q7818709, the Tombs of the Nobles in Thebes. Each id below was resolved and
# checked against its label, description and P17 before being written down.
# Holding the id also makes coverage exact, since sitelinks can then be read
# straight off the item instead of guessed at by search.
# Each anchor carries every Wikidata item that stands for it, because Wikidata
# frequently holds two: one for the UNESCO inscription and one for the practice
# itself. Empaako is the clear case, Q96213222 being the inscription with no
# sitelinks at all and Q48748634 the practice carrying the English, French and
# Turkish articles. Reading only the inscription item would report Empaako as
# undocumented when an English article plainly exists. Coverage is the union
# across the items.
ICH_ELEMENTS = (
    ('Barkcloth making in Uganda', 2008, 'Representative List',
     'baganda', 'craft', ('Q112633680',)),
    ('Bigwala gourd trumpet music and dance of the Busoga Kingdom', 2012,
     'Urgent Safeguarding', 'basoga', 'performing', ('Q28154356',)),
    ('Empaako tradition of the Batooro, Banyoro, Batuku, Batagwenda '
     'and Banyabindi', 2013, 'Urgent Safeguarding', 'batooro', 'naming',
     ('Q96213222', 'Q48748634')),
    ('Male-child cleansing ceremony of the Lango', 2014,
     'Urgent Safeguarding', 'lango', 'social', ('Q96213125',)),
    ('Koogere oral tradition of the Basongora, Banyabindi and Batooro', 2015,
     'Urgent Safeguarding', 'basongora', 'oral', ('Q50922851',)),
    ("Ma'di bowl lyre music and dance", 2016, 'Urgent Safeguarding',
     'madi', 'performing', ('Q113016315',)),
)

WORLD_HERITAGE = (
    ('Tombs of Buganda Kings at Kasubi', 2001, 'World Heritage',
     'baganda', 'tangible', ('Q309426',)),
    ('Rwenzori Mountains National Park', 1994, 'World Heritage',
     'bakonzo', 'tangible', ('Q838928',)),
    ('Bwindi Impenetrable National Park', 1994, 'World Heritage',
     'batwa', 'tangible', ('Q500397',)),
)

# Sitelinks that are not Wikipedias. Counting commonswiki as a language would
# say Barkcloth making is documented in two when it has one article, in French.
NOT_WIKIPEDIA = {'commonswiki', 'specieswiki', 'metawiki', 'wikidatawiki',
                 'sourceswiki', 'mediawikiwiki'}

# Named, not ingested. Each is a real inventory this analysis should be
# reconciled against; none publishes machine-readable data, so the page lists
# them as outstanding work rather than pretending they are loaded.
EXTERNAL_INVENTORIES = (
    ('National ICH inventory',
     'Ministry of Gender, Labour and Social Development',
     'https://mglsd.go.ug/',
     'Community-based inventories across more than forty ethno-linguistic '
     'communities, including individual community inventories such as the '
     'Basoga Community Inventory of Intangible Heritage (2010).'),
    ('UNESCO ICH inventory', 'UNESCO',
     'https://ich.unesco.org/en/state/uganda-UG',
     'Six inscribed elements, each with a detailed nomination file. The '
     'element pages render in JavaScript, so the nomination files need '
     'fetching by hand rather than by crawl.'),
    ('Heritage case studies and built-heritage documentation',
     'Cross-Cultural Foundation of Uganda (CCFU)',
     'https://crossculturalfoundation.or.ug/',
     'UNESCO-accredited NGO documenting cultural institutions, languages, '
     'governance and herbal medicine, and running the National Heritage '
     'Awards. The most natural institutional partner here.'),
    ('Community museum holdings',
     'Uganda Community Museums Association (UCOMA)',
     'https://ucoma.or.ug/',
     'Granular local holdings across the regions, the layer most likely to '
     'hold what no national inventory records.'),
    ('Enumerated ethnic groups, populations and languages',
     'Uganda Bureau of Statistics', 'https://www.ubos.org/',
     'The census backbone for "all cultures": which communities exist and how '
     'many people belong to them. This project already parses the UBOS '
     'administrative hierarchy; the ethnicity tables are not yet loaded.'),
)


def _api(base, params):
    session = ug_utils.get_session()
    query = dict(params, format='json', formatversion=2)
    for attempt in range(4):
        try:
            response = session.get(base, params=query, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def aspect_of(title):
    """The aspect an article title falls in, or '' when none matches.

    Returns '' for titles EXCLUDE rejects, so a football club named after a
    community never lands in a heritage cell.
    """
    if EXCLUDE.search(title):
        return ''
    for key, pattern in ASPECT_PATTERNS:
        if pattern.search(title):
            return key
    return ''


def fetch_articles(conn, force=False):
    """Every Uganda-related article whose title carries a community name."""
    with ug_utils.stage(conn, SCRIPT, 'fetch_articles', force) as st:
        if st.skip:
            return
        conn.execute('DROP TABLE IF EXISTS folklore_articles')
        conn.execute("""CREATE TABLE folklore_articles (
            title text, group_key text, family text, aspect text,
            PRIMARY KEY (title, group_key))""")

        families = dict(FAMILIES)
        rows, seen_titles = [], set()
        for key, label, family, variants in GROUPS:
            # "Uganda" in the query is what keeps the Mexican university out of
            # the Iteso row: intitle alone matches ITESO, the Guadalajara
            # institution, which has nothing to do with the Teso people.
            terms = ' OR '.join(f'"{v}"' if ' ' in v else v for v in variants)
            payload = _api(EN_API, {
                'action': 'query', 'list': 'search',
                'srsearch': f'intitle:({terms}) Uganda',
                'srlimit': SEARCH_LIMIT, 'srnamespace': 0})
            hits = payload.get('query', {}).get('search', [])
            for hit in hits:
                title = hit['title']
                rows.append((title, key, family, aspect_of(title)))
                seen_titles.add(title)
            print(f'    {label:<16} {len(hits):3d} articles')
            time.sleep(PAUSE)

        conn.executemany(
            'INSERT OR IGNORE INTO folklore_articles VALUES (?,?,?,?)', rows)
        conn.commit()
        print(f'    {len(rows)} rows, {len(seen_titles)} distinct articles')


def check_anchors(conn, force=False):
    """Do the inscribed elements have Wikimedia coverage at all?"""
    with ug_utils.stage(conn, SCRIPT, 'check_anchors', force) as st:
        if st.skip:
            return
        conn.execute('DROP TABLE IF EXISTS folklore_anchors')
        conn.execute("""CREATE TABLE folklore_anchors (
            name text PRIMARY KEY, year integer, listing text,
            group_key text, aspect text, en_title text, lg_title text,
            qid text, languages integer)""")

        anchors = list(ICH_ELEMENTS) + list(WORLD_HERITAGE)
        every_qid = sorted({q for a in anchors for q in a[5]})
        payload = _api('https://www.wikidata.org/w/api.php', {
            'action': 'wbgetentities', 'ids': '|'.join(every_qid),
            'props': 'sitelinks'})
        entities = payload.get('entities', {})

        rows = []
        for name, year, listing, group_key, aspect, qids in anchors:
            links = {}
            for qid in qids:
                links.update(entities.get(qid, {}).get('sitelinks', {}) or {})
            en_title = links.get('enwiki', {}).get('title', '')
            lg_title = links.get('lgwiki', {}).get('title', '')
            # every Wikipedia, not just the two, so "documented nowhere" is a
            # claim about all of Wikipedia rather than about English alone
            languages = len([k for k in links
                             if k.endswith('wiki') and k not in NOT_WIKIPEDIA])
            rows.append((name, year, listing, group_key, aspect,
                         en_title, lg_title, ' '.join(qids), languages))
            print(f'    {name[:44]:<44} en={"yes" if en_title else "NO ":<3} '
                  f'lg={"yes" if lg_title else "NO ":<3} '
                  f'{languages:2d} wikipedias  {" ".join(qids)}')

        conn.executemany(
            'INSERT INTO folklore_anchors VALUES (?,?,?,?,?,?,?,?,?)', rows)
        conn.commit()


# Words too generic to confirm that a search hit is really about the element.
GENERIC = {'of', 'the', 'and', 'in', 'uganda', 'making', 'tradition', 'music',
           'dance', 'ceremony', 'oral', 'national', 'park', 'kings', 'at'}


def _tokens(text):
    return {w for w in re.findall(r"[a-z']+", text.lower())
            if w not in GENERIC and len(w) > 2}


def _best_match(base, name):
    """A search hit whose title shares a distinctive word with the element."""
    try:
        payload = _api(base, {'action': 'query', 'list': 'search',
                              'srsearch': name, 'srlimit': 5, 'srnamespace': 0})
    except Exception:
        return ''
    want = _tokens(name)
    for hit in payload.get('query', {}).get('search', []):
        if want & _tokens(hit['title']):
            return hit['title']
    return ''


def _name_probes(name):
    """Progressively shorter openings of an official name.

    wbsearchentities matches a prefix, not a phrase, so the full UNESCO title
    finds nothing: "Bigwala gourd trumpet music and dance of the Busoga
    Kingdom" returns no item while "Bigwala" returns Q28154356. Searching the
    long name alone reports an item as missing when it exists, which is the
    one error this page cannot afford.
    """
    name = name.strip()
    probes = [name, name.split(',')[0].strip()]
    words = name.replace(',', ' ').split()
    for n in (4, 3, 2, 1):
        if len(words) >= n:
            probes.append(' '.join(words[:n]))
    seen, out = set(), []
    for p in probes:
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


# Words that tie a candidate item to Uganda. A shared token is not enough on
# its own: searching "Tombs of Buganda Kings at Kasubi" offers Q7818709, the
# Tombs of the Nobles, an Ancient Egyptian necropolis in Thebes, which shares
# "tombs" and nothing else. Every accepted item must name Uganda or one of its
# communities somewhere in its label or description.
UGANDA_WORDS = ({'uganda', 'ugandan'}
                | {label.lower() for _k, label, _f, _v in GROUPS}
                | {v.lower() for _k, _l, _f, variants in GROUPS
                   for v in variants})


def _is_ugandan(*texts):
    words = set()
    for t in texts:
        words |= {w for w in re.findall(r"[a-z']+", (t or '').lower())}
    return bool(words & UGANDA_WORDS)


def _wikidata_qid(name):
    want = _tokens(name)
    for probe in _name_probes(name):
        try:
            payload = _api('https://www.wikidata.org/w/api.php',
                           {'action': 'wbsearchentities', 'search': probe[:60],
                            'language': 'en', 'limit': 5})
        except Exception:
            return ''
        for hit in payload.get('search', []):
            label = hit.get('label', '')
            desc = (hit.get('description') or '').lower()
            # A museum named after a tradition is not the tradition: the
            # Koogere search offers a museum item before the oral tradition.
            if 'museum' in desc and 'museum' not in name.lower():
                continue
            if want & _tokens(label) and _is_ugandan(label, desc):
                return hit['id']
        time.sleep(PAUSE)
    return ''


def export(conn, force=False):
    with ug_utils.stage(conn, SCRIPT, 'export', force) as st:
        if st.skip:
            return

        def dump(path, header, rows):
            with open(path, 'w', encoding='utf-8', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerows(rows)
            print(f'    -> {os.path.basename(path)} ({len(rows)} rows)')

        dump(OUT_ARTICLES, ['title', 'group', 'family', 'aspect'],
             conn.execute("""SELECT title, group_key, family, aspect
                             FROM folklore_articles
                             ORDER BY family, group_key, title""").fetchall())

        labels = {k: l for k, l, _f, _v in GROUPS}
        aspect_labels = {k: l for k, l, _p, _v in ASPECTS}
        counts = {(g, a): n for g, a, n in conn.execute(
            """SELECT group_key, aspect, COUNT(*) FROM folklore_articles
               WHERE aspect != '' GROUP BY 1, 2""")}
        matrix = []
        for key, label, family, _v in GROUPS:
            for akey, alabel, _parent, _v2 in ASPECTS:
                matrix.append((family, label, aspect_labels.get(akey, akey),
                               counts.get((key, akey), 0)))
        dump(OUT_MATRIX, ['family', 'group', 'aspect', 'articles'], matrix)

        dump(OUT_ANCHORS,
             ['name', 'year', 'listing', 'group', 'aspect', 'en_title',
              'lg_title', 'wikidata', 'languages'],
             conn.execute("""SELECT name, year, listing, group_key, aspect,
                                    en_title, lg_title, qid, languages
                             FROM folklore_anchors
                             ORDER BY year""").fetchall())


def main(force=False):
    conn = ug_utils.connect()
    fetch_articles(conn, force)
    check_anchors(conn, force)
    export(conn, force)
    conn.close()


if __name__ == '__main__':
    import sys
    main(force='--force' in sys.argv)
