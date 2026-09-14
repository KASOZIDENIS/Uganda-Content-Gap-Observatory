# -*- coding: utf-8 -*-
"""What OpenStreetMap knows about Uganda that Wikimedia has never described.

Two findings kept deliberately apart, because adding them together would
overstate the case: how little of OSM's Uganda is cross-referenced to
Wikimedia at all, and how much of it no Wikipedia describes.
"""

from render import (bars, callout, data_table, esc, eyebrow, filter_controls,
                    fmt, join, note, page_footer, plain_table, section_heading,
                    stat_tiles, tab_bar, td)


def _osm_link(f):
    # 'route' is the pipeline's label for a linear feature built from
    # many ways; osmId is one of them, and OSM serves only node, way
    # and relation, so /route/ would 404.
    kind = 'way' if f["osmType"] == 'route' else f["osmType"]
    url = f'https://www.openstreetmap.org/{kind}/{f["osmId"]}'
    return (f'<a href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(f["name"])}</a>')


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>OpenStreetMap has mapped a Uganda that Wikimedia has never '
        'described</h1>',
        f'<p class="lede">OSM carries {fmt(d["total"])} named Ugandan '
        f'features across {fmt(d["nClasses"])} classes of thing: villages, '
        f'schools, hospitals, trunk roads, rivers, protected areas. '
        f'<strong>{fmt(d["noArticle"])} of them have no Wikipedia article in '
        f'any language describing that place.</strong> A mapper can point to '
        f'each one on the ground; no encyclopedia can tell you anything about '
        f'it.</p>',
        f'<p class="stamp"><strong>Two different gaps, kept apart.</strong> '
        f'{fmt(d["untagged"])} features carry no <code>wikidata</code> or '
        f'<code>wikipedia</code> tag, but a missing tag only means nobody has '
        f'done the linking, which is a job for mappers. The number in the '
        f'headline is the stronger one: every untagged feature was matched by '
        f'position and name against this project&rsquo;s corpus, every item '
        f'of which has an article by construction, so a feature with no match '
        f'within two kilometres is one no Wikipedia covers.</p>',
        '</header>',
    ])


def _coverage(d):
    rows = [[
        {'text': c['label']},
        {'text': fmt(c['total'])},
        {'text': fmt(c['untagged'])},
        {'text': fmt(c['wikidataOnly'])},
        {'text': fmt(c['wikipediaOnly'])},
        {'text': fmt(c['both'])},
        {'text': f'{c["taggedShare"]:.1f}%', 'dim': True},
    ] for c in d['classes']]
    return join([
        section_heading(
            'The cross-reference gap',
            'Every named Ugandan feature, by whether it carries a '
            '<code>wikidata</code> tag, a <code>wikipedia</code> tag, both or '
            'neither. The last column is the share with any link at all, and '
            'it is how thin the connection between the two projects is.'),
        plain_table(
            [{'label': 'Class'}, {'label': 'Named in OSM', 'num': True},
             {'label': 'No tag', 'num': True},
             {'label': 'Wikidata only', 'num': True},
             {'label': 'Wikipedia only', 'num': True},
             {'label': 'Both', 'num': True},
             {'label': 'Linked', 'num': True}],
            rows),
    ])


def _documented(d):
    if not d['matched']:
        return join([
            section_heading('The documentation gap'),
            note('Run <code>python src_data/osm_features.py</code> to match '
                 'the untagged features against the corpus.'),
        ])
    rows = [[
        {'text': c['label']},
        {'text': fmt(c['total'])},
        {'text': fmt(c['described'])},
        {'text': fmt(c['itemNoArticle'])},
        {'text': fmt(c['noArticle']), 'strong': True},
        {'text': (f'{100.0 * (c["noArticle"] + c["itemNoArticle"]) / c["total"]:.0f}%'
                  if c['total'] else '0%'), 'dim': True},
    ] for c in d['classes']]
    return join([
        section_heading(
            'The documentation gap',
            'What Wikimedia actually holds. A feature tagged with an item '
            'was looked up directly; an untagged one was matched on position '
            'within two kilometres plus a shared name word. The middle column '
            'is the one to read twice: those places are in Wikidata and in '
            'no encyclopedia.'),
        plain_table(
            [{'label': 'Class'}, {'label': 'Named', 'num': True},
             {'label': 'Described already', 'num': True},
             {'label': 'Item, no article', 'num': True},
             {'label': 'Nothing at all', 'num': True},
             {'label': 'Undescribed', 'num': True}],
            rows),
        '<div class="spacer"></div>',
        bars([{'label': c['label'], 'value': c['noArticle'],
               'display': fmt(c['noArticle'])} for c in d['classes']
              if c['noArticle']]),
        note('Bars are features with nothing found at all. Villages dominate '
             'by an order of magnitude, which is what you would expect: OSM '
             'maps every settlement it can reach, and an encyclopedia has '
             'never had a reason to describe most of them.'),
    ])


def _worklist(d):
    if not d['worklist']:
        return ''
    classes = []
    counts = {}
    for f in d['worklist']:
        counts[f['classLabel']] = counts.get(f['classLabel'], 0) + 1
    for c in d['classes']:
        if counts.get(c['label']):
            classes.append(c['label'])

    columns = [
        {'label': '#', 'num': True}, {'label': 'Feature in OSM'},
        {'label': 'Class'}, {'label': 'Segments', 'num': True},
        {'label': 'Where it is'},
    ]

    def row(f, i):
        if f['lat'] is None:
            where = '<span class="dim">no centre point</span>'
        else:
            url = (f'https://www.openstreetmap.org/?mlat={f["lat"]:.5f}'
                   f'&mlon={f["lon"]:.5f}#map=14/{f["lat"]:.4f}/'
                   f'{f["lon"]:.4f}')
            where = (f'<a class="mono" href="{esc(url)}" target="_blank" '
                     f'rel="noopener">{f["lat"]:.3f}, {f["lon"]:.3f}</a>')
        return join([
            td(str(i + 1), 'num', 'dim'),
            td(f'<strong>{_osm_link(f)}</strong>'),
            td(esc(f['classLabel']), 'dim'),
            td(fmt(f['segments']) if f['segments'] > 1 else '', 'num', 'dim'),
            td(where, 'dim'),
        ])

    tail = ''
    if d['omitted']:
        tail = note(
            f'{fmt(d["omitted"])} more are omitted here: the bulk classes are '
            f'sampled at {fmt(d["sampleSize"])} each because a table of every '
            f'unmatched Ugandan village would be a twenty-megabyte page. '
            f'Every row is in <code>data/ug_osm_undocumented.csv</code>, which '
            f'is where this page stops being a summary and becomes a '
            f'worklist.')

    return join([
        section_heading(
            'What to write about',
            f'The features with no article anywhere. Roads and rivers first '
            f'within each class, by how many OSM ways carry the name, which '
            f'is the closest thing here to a length. Names link to OSM, '
            f'coordinates to the spot on the map.'),
        filter_controls(
            groups=[{'key': 'klass', 'label': 'Filter by class',
                     'allLabel': 'Every class',
                     'options': [{'value': c, 'label': c, 'count': counts[c]}
                                 for c in classes]}],
            total=len(d['worklist']), count_noun='features',
            search_placeholder=f'Filter {fmt(len(d["worklist"]))} features by '
                               f'name or class',
            search_label='Filter the worklist'),
        data_table(d['worklist'], columns, row,
                   row_attrs=lambda f: {'data-klass': f['classLabel']}),
        tail,
    ])


def _half(d):
    if not d['half']:
        return ''
    rows = [[
        {'text': f['name']},
        {'text': f['classLabel'], 'dim': True},
        {'text': f['qid'] or f['wikipediaTag']},
        {'text': ('needs a wikipedia tag' if f['state'] == 'wikidata_only'
                  else 'needs a wikidata tag'), 'dim': True},
    ] for f in d['half']]
    return join([
        section_heading(
            'Tagged one way but not the other',
            f'{fmt(d["nHalf"])} features carry one of the two tags and not '
            f"its partner, overwhelmingly Uganda's schools, which were "
            f'imported into OSM with item references en masse. The cheapest '
            f'fix on this page: the identifier is already there and the '
            f'matching tag is a single edit. The first '
            f'{fmt(len(d["half"]))} of them:'),
        plain_table(
            [{'label': 'Feature'}, {'label': 'Class'},
             {'label': 'Tag it has'}, {'label': 'What is missing'}],
            rows),
    ])


def render(d):
    return join([
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),

        section_heading('The headline'),
        stat_tiles([
            {'k': 'Named features in OSM', 'v': d['total'],
             'd': f'across {fmt(d["nClasses"])} classes, villages to rivers'},
            {'k': 'Nothing found at all', 'v': d['noArticle'], 'alarm': True,
             'd': 'no item, no article, no match within two kilometres'},
            {'k': 'Item but no article', 'v': d['itemNoArticle'],
             'd': 'Wikidata holds it, no Wikipedia in any language writes it '
                  'up'},
            {'k': 'Described already', 'v': d['described'],
             'd': f'of {fmt(d["total"])} named features; the other '
                  f'{esc(d["taggedShare"])}% carry some Wikimedia tag'},
        ]),

        callout(
            '<strong>These are two jobs, not one.</strong> The features that '
            'are described already but untagged need a mapper to add one tag. '
            'The features with no article need somebody to write one, and '
            'most of them are villages and schools that no encyclopedia has '
            'ever had a reason to cover. Only the second is a content gap in '
            'the sense the rest of this project means it.'),

        _coverage(d),
        _documented(d),
        _worklist(d),
        _half(d),

        page_footer([
            '<strong>Where this comes from.</strong> One Overpass query per '
            'class of feature over the Uganda admin boundary, asking for tags '
            'and a centre point rather than full geometry. Only named '
            'features count: an unnamed one cannot be documented in an '
            'encyclopedia anyway. Roads and rivers arrive as many OSM ways '
            'per route, so linear features are grouped by name.',

            '<strong>How the matching works, and why not by name.</strong> A '
            'first attempt asked Wikidata for each name together with '
            'country=Uganda and found almost nothing, for two reasons that '
            'both matter: &ldquo;Gulu&rdquo; also names places in Indonesia '
            'and Nigeria, and Gulu in Uganda carries no country statement at '
            'all, so the filter rejected the very item it should have found. '
            'The match is therefore geographic: within two kilometres of a '
            'corpus item that shares a name word. Every corpus item has at '
            'least one article by construction, so a match means the place is '
            'described somewhere.',

            '<strong>What the numbers are not.</strong> &ldquo;No article '
            'found&rdquo; is a search result, not a proof of absence: a place '
            'whose article sits under a different name, or whose Wikidata '
            'item carries no coordinates, will read as absent. Nor does this '
            'page claim those places have no Wikidata item, only no article; '
            'Uganda has 58,240 Wikidata items with no article in any '
            'language, and some of these will be among them. The segment '
            'count correlates with length but does not measure it: a road '
            'split finely scores higher than a longer road split coarsely.',

            '<strong>Rebuild.</strong> <code>python '
            'src_data/osm_features.py</code>, then <code>python '
            'src_viz/export_data.py</code> and <code>python '
            'src_viz/build_pages.py osm</code>. The fetch checkpoints per '
            'class, so an interrupted run resumes rather than starting over, '
            'and three Overpass mirrors are tried in turn because the public '
            'instances hand out 429s and 504s freely. Full exports are in '
            '<code>data/ug_osm_features.csv</code> and '
            '<code>data/ug_osm_undocumented.csv</code>.',
        ]),
        '</div>',
    ])
