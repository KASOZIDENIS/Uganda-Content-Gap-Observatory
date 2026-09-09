# -*- coding: utf-8 -*-
"""Presentation helpers shared by the page builders.

Kept free of pandas and requests so a page can be rebuilt from the database
alone, with no pipeline dependencies loaded.
"""

import html


def esc(text):
    return html.escape(str(text) if text is not None else '')


def fmt(number):
    try:
        return f'{int(round(float(number))):,}'
    except (TypeError, ValueError):
        return '-'


def head(title, page_sheet):
    """The <title> and stylesheet links every page opens with.

    tokens.css carries the palette, shell.css the chrome both pages share,
    and page_sheet whatever is specific to this one.
    """
    return (f'<title>{esc(title)}</title>\n'
            '<link rel="stylesheet" href="assets/css/tokens.css">\n'
            '<link rel="stylesheet" href="assets/css/shell.css">\n'
            f'<link rel="stylesheet" href="assets/css/{page_sheet}">')
