# -*- coding: utf-8 -*-
"""Build every page to static HTML in the project root.

The pages are opened from disk and shared as files, so they are rendered whole
here rather than mounted in the browser: a blank page without JavaScript would
be a real regression, and the largest page is a 6,765-row table that has no
business being built client-side.

Reads the view models written by export_data.py. Run that first when the
database has changed; this step only turns those into markup.

    python src_viz/export_data.py     # database  -> data/ui/*.json
    python src_viz/build_pages.py     # data/ui/* -> *.html

Pass page keys to rebuild only some of them, which is worth doing while
iterating: `python src_viz/build_pages.py dashboard` skips the 2 MB edition
table.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src_data'))

import config                     # noqa: E402
import page_dashboard             # noqa: E402
import page_plan                  # noqa: E402
import page_edition               # noqa: E402
import page_topics                # noqa: E402
import page_osm                   # noqa: E402
import page_registers             # noqa: E402
import page_offices               # noqa: E402
import page_undocumented          # noqa: E402

RENDERERS = {
    'dashboard': page_dashboard.render,
    'plan': page_plan.render,
    'edition': page_edition.render,
    'topics': page_topics.render,
    'osm': page_osm.render,
    'registers': page_registers.render,
    'offices': page_offices.render,
    'undocumented': page_undocumented.render,
    'undocumented_men': page_undocumented.render,
}

UI_DIR = os.path.join(config.PROJECT_PATH, 'data', 'ui')


def output_for(data, page_key):
    """page key -> output file, taken from the nav block every model carries."""
    for page in data['nav']['pages']:
        if page['key'] == page_key:
            return page['href']
    raise KeyError(f'page {page_key} is not in config.PAGES')


def sheets(data):
    """tokens and shell on every page, components for the pages that use the
    shared list furniture, then the page's own sheet last so it can override."""
    names = ['tokens.css', 'shell.css']
    if data.get('components') is not False:
        names.append('components.css')
    names.append(data['sheet'])
    return '\n'.join(f'<link rel="stylesheet" href="assets/css/{n}">'
                     for n in names)


def document(data, body):
    """The page skeleton.

    The charset declaration is not optional: the markup carries real UTF-8
    characters rather than ASCII entities, and opened from disk with no
    charset declared, Chrome guesses the encoding and renders them as
    mojibake. The viewport tag goes with it: the stylesheets have carried
    mobile breakpoints all along, and without this they never fire on a phone.
    """
    return f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{data['title']}</title>
{sheets(data)}
<script>document.documentElement.classList.add('js')</script>

{body}

<script src="assets/js/app.js" defer></script>
'''


def build(page_key):
    data_path = os.path.join(UI_DIR, page_key + '.json')
    if not os.path.exists(data_path):
        print(f'skipping {page_key}: no {data_path}', file=sys.stderr)
        print('  run: python src_viz/export_data.py', file=sys.stderr)
        return False

    with open(data_path, encoding='utf-8') as handle:
        data = json.load(handle)

    doc = document(data, RENDERERS[page_key](data))
    href = output_for(data, page_key)
    out = os.path.join(config.PROJECT_PATH, href)
    with open(out, 'w', encoding='utf-8') as handle:
        handle.write(doc)
    print(f'wrote {href} ({len(doc.encode("utf-8")) // 1024} KB)')
    return True


def main():
    keys = sys.argv[1:] or list(RENDERERS)
    unknown = [k for k in keys if k not in RENDERERS]
    if unknown:
        print(f'unknown page(s): {", ".join(unknown)}', file=sys.stderr)
        print(f'known: {", ".join(RENDERERS)}', file=sys.stderr)
        return 2
    return 0 if all([build(k) for k in keys]) else 1


if __name__ == '__main__':
    sys.exit(main())
