# -*- coding: utf-8 -*-
"""What Wikimedia Commons holds about Uganda.

The fourth corpus in this project, and the only one measured in files rather
than articles or items. Commons organises everything by hand-built categories,
so the page's main job is to state clearly that its totals are a function of how
deep the category walk went.
"""

from render import (bars, callout, esc, eyebrow, fmt, join, note, page_footer,
                    plain_table, section_heading, stat_tiles, tab_bar)


def _header(d):
    return join([
        '<header>',
        eyebrow(f'Uganda content gap analysis &middot; cycle {esc(d["cycle"])}'),
        '<h1>Uganda on Commons is a photo album, not an archive</h1>',
        f'<p class="lede">Walking the category graph out from '
        f'<code>Category:Uganda</code> reaches {fmt(d["nFiles"])} files across '
        f'{fmt(d["nCategories"])} categories. '
        f'<strong>{d["photoShare"]:.1f}% of them are photographs.</strong> '
        f'Maps, diagrams, audio and video together make up the rest, which is '
        f'what makes this a collection of pictures rather than a body of '
        f'reference media.</p>',
        '<p class="stamp"><strong>Every total on this page carries a depth.</strong> '
        'Commons categories are a graph with cycles, not a tree, and following '
        'it far enough from any starting point eventually reaches the whole of '
        'Commons. This walk stopped at depth '
        f'{d["maxDepth"]}. A file or category count taken from a category walk '
        'is a statement about how far the walk went, and is quoted here with '
        'that number attached.</p>',
        '</header>',
    ])


def _depth(d):
    rows = [[
        {'text': f'Depth {r["depth"]}'},
        {'text': fmt(r['categories'])},
        {'text': fmt(r['files']), 'dim': True},
    ] for r in d['depths']]
    parts = [
        section_heading(
            'Why the totals carry a depth',
            'Categories found at each step out from <code>Category:Uganda</code>. '
            'The count grows by roughly four times a level and does not '
            'converge, because Ugandan categories sit under continental, '
            'chronological and file-format parents that lead back out into the '
            'rest of Commons.'),
        plain_table(
            [{'label': 'Step from the root'},
             {'label': 'Categories', 'num': True},
             {'label': 'File memberships', 'num': True}],
            rows),
        note('File memberships count a file once per category it sits in, so '
             'they exceed the number of distinct files. The totals elsewhere on '
             'this page are deduplicated by file title.'),
    ]
    if d['truncated']:
        parts.append(note(
            f'{fmt(d["truncated"])} categories were still unexplored when the '
            f'walk stopped at depth {d["maxDepth"]}. They are counted in the '
            f'totals; their children are not.'))
    return join(parts)


def _media(d):
    rows = [[
        {'text': m['label']},
        {'text': fmt(m['files'])},
        {'text': f'{m["share"]:.1f}%', 'dim': True},
    ] for m in d['media']]
    parts = [
        section_heading(
            'What kind of files they are',
            'Media type derived from the file extension, then checked against '
            'the Commons API on a random sample.'),
        plain_table(
            [{'label': 'Media type'}, {'label': 'Files', 'num': True},
             {'label': 'Share', 'num': True}],
            rows),
        '<div class="spacer"></div>',
        bars([{'label': m['label'], 'value': m['files'],
               'display': fmt(m['files'])} for m in d['media'] if m['files']]),
    ]
    check = d.get('check')
    if check:
        parts.append(note(
            f'The type above comes from the file extension, which costs nothing, '
            f'rather than from one API call per fifty files. On a random sample '
            f'of {fmt(check["sampled"])} files the extension agreed with the '
            f'value Commons itself reports '
            f'{fmt(check["agreed"])} times out of '
            f'{fmt(check["agreed"] + check["disagreed"])} resolved, '
            f'{check["accuracy"]:.1f}%. The shares above should be read with '
            f'that margin.'))
    return join(parts)


def _themes(d):
    rows = [[
        {'text': t['label']},
        {'text': fmt(t['categories']), 'dim': True},
        {'text': fmt(t['files'])},
        {'text': f'{t["share"]:.1f}%', 'dim': True},
    ] for t in d['themes']]
    return join([
        section_heading(
            'What they are about',
            'Each file is attributed to the theme of the first category that '
            'reached it, matched on the category title. A file in several '
            'categories is counted once, so a theme here is the route the walk '
            'took to a file rather than the only subject it belongs to.'),
        plain_table(
            [{'label': 'Theme'}, {'label': 'Categories', 'num': True},
             {'label': 'Files', 'num': True}, {'label': 'Share', 'num': True}],
            rows),
        '<div class="spacer"></div>',
        bars([{'label': t['label'], 'value': t['files'],
               'display': fmt(t['files'])} for t in d['themes'] if t['files']]),
    ])


def _campaigns(d):
    if not d['campaigns']:
        return join([
            section_heading('What the photo campaigns brought in'),
            callout('No files in this walk sit in a Wiki Loves category. That '
                    'is a statement about category naming rather than about the '
                    'campaigns: campaign uploads are often filed only under the '
                    'subject, so this counts the ones that kept the campaign '
                    'category and undercounts the rest.'),
        ])
    rows = [[
        {'text': c['label']},
        {'text': fmt(c['files'])},
        {'text': f'{c["share"]:.2f}%', 'dim': True},
    ] for c in d['campaigns']]
    return join([
        section_heading(
            'What the photo campaigns brought in',
            'Files sitting in a category named for one of the Wiki Loves '
            'competitions.'),
        plain_table(
            [{'label': 'Campaign'}, {'label': 'Files', 'num': True},
             {'label': 'Share of all files', 'num': True}],
            rows),
        note(f'{fmt(d["fromCampaigns"])} files, {d["campaignShare"]:.2f}% of '
             f'the collection, are filed under a campaign category. Campaign '
             f'uploads are frequently recategorised to the subject afterwards '
             f'and lose the campaign category, so treat this as a floor.'),
    ])


def _top(d):
    rows = [[
        {'html': f'<a href="{esc(c["url"])}" target="_blank" '
                 f'rel="noopener">{esc(c["title"])}</a>'},
        {'text': f'Depth {c["depth"]}', 'dim': True},
        {'text': c['theme'], 'dim': True},
        {'text': fmt(c['files'])},
    ] for c in d['top']]
    return join([
        section_heading(
            'The largest categories',
            'Where the files actually are. File counts are the category&rsquo;s '
            'own, so a parent category counts only files filed directly in it, '
            'not those in its children.'),
        plain_table(
            [{'label': 'Category'}, {'label': 'Found at'},
             {'label': 'Theme'}, {'label': 'Files', 'num': True}],
            rows),
    ])


def render(d):
    tiles = [
        {'k': 'Files', 'v': d['nFiles'],
         'd': f'distinct, within depth {d["maxDepth"]} of Category:Uganda'},
        {'k': 'Categories', 'v': d['nCategories'],
         'd': f'reached in {d["maxDepth"]} steps from the root'},
        {'k': 'Photographs', 'raw': True, 'v': f'{d["photoShare"]:.1f}%',
         'd': 'of everything in the walk'},
    ]
    if d['campaigns']:
        tiles.append({
            'k': 'From Wiki Loves', 'raw': True,
            'v': f'{d["campaignShare"]:.2f}%',
            'd': f'{fmt(d["fromCampaigns"])} files still in a campaign category'})

    non_photo = d['nFiles'] - d['photos']
    parts = [
        '<div class="wrap">',
        tab_bar(d['nav']),
        _header(d),
        section_heading('The headline'),
        stat_tiles(tiles),
        callout(
            f'<strong>{d["photoShare"]:.1f}% of Uganda&rsquo;s presence on '
            f'Commons is photographs.</strong> That leaves {fmt(non_photo)} '
            f'files of everything else: the maps, diagrams, charts, audio and '
            f'video that an encyclopedia article needs and a photograph cannot '
            f'supply. A gap in media of that kind is invisible in a file count '
            f'and obvious the moment someone tries to illustrate an article '
            f'about a language, a piece of music or an administrative boundary.'),
        _depth(d),
        _media(d),
        _themes(d),
        _campaigns(d),
        _top(d),
        page_footer([
            '<strong>Where this comes from.</strong> A breadth-first walk of the '
            'Commons category graph starting at <code>Category:Uganda</code>, '
            'using the MediaWiki API on commons.wikimedia.org. Categories are '
            'deduplicated by title and recorded at the shallowest depth they '
            'were reached, because the graph has cycles and multiple parents.',

            '<strong>What a total here is and is not.</strong> It is the set of '
            'files reachable within a fixed number of category steps from one '
            'root. It is not "every file about Uganda": a file about Uganda '
            'filed only under a category the walk never reached is not counted, '
            'and a file with no Ugandan subject sitting in a category the walk '
            'did reach is. Both errors grow with depth, which is why the depth '
            'travels with every number on this page.',

            '<strong>Media type.</strong> Derived from the file extension and '
            'checked against the Commons API on a random sample; the measured '
            'agreement rate is quoted above rather than assumed.',

            '<strong>Rebuild.</strong> <code>python '
            'src_data/commons_audit.py</code>, then <code>python '
            'src_viz/export_data.py</code> and <code>python '
            'src_viz/build_pages.py commons</code>. Full exports are in '
            '<code>data/ug_commons_categories.csv</code>, '
            '<code>data/ug_commons_media.csv</code> and '
            '<code>data/ug_commons_summary.csv</code>.',
        ]),
        '</div>',
    ]
    return join(parts)
