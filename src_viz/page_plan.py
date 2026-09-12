# -*- coding: utf-8 -*-
"""The action plan.

Unlike the other pages this one has no view model beyond its nav block: its
numbers are a deliberately frozen baseline, so they live in the prose. A plan
needs a fixed starting line to measure against; the living figures are on the
dashboard, which re-runs monthly.
"""

from render import tab_bar, stat_tiles, esc, join

WDO_LINK = ('<a href="https://meta.wikimedia.org/wiki/'
            'Wikipedia_Diversity_Observatory" target="_blank" '
            'rel="noopener">Wikipedia Diversity Observatory</a>')


def _finding(heading, paras, so_what):
    body = ''.join(f'<p>{p}</p>' for p in paras)
    swat = ''.join(f'<p>{p}</p>' for p in so_what)
    return (f'<div class="finding"><div><h3>{heading}</h3>{body}</div>'
            f'<div class="so-what"><p class="k">So what</p>{swat}</div></div>')


def _rec(priority, label, heading, paras, meta=None, dont=False):
    body = ''.join(f'<p>{p}</p>' for p in paras)
    out = [f'<div class="{"rec dont" if dont else "rec"}">',
           f'<div class="rec-head"><span class="pri {priority}">{esc(label)}'
           f'</span><h3>{heading}</h3></div>', body]
    if meta:
        items = ''.join(f'<div><span class="k">{esc(k)}</span>'
                        f'<span class="v">{v}</span></div>' for k, v in meta)
        out.append(f'<div class="meta">{items}</div>')
    out.append('</div>')
    return ''.join(out)


def _bar(label, width, value):
    return (f'<div class="bar-row"><div class="bar-label">{label}</div>'
            f'<div class="bar-track">'
            f'<div class="bar-fill" style="width:{width}"></div></div>'
            f'<div class="bar-val">{esc(value)}</div></div>')


def _step(when, heading, para):
    return (f'<li><p class="when">{esc(when)}</p><h3>{esc(heading)}</h3>'
            f'<p>{para}</p></li>')


BACKLOG_BARS = [
    ('Other sport', '100%', '711'),
    ('Other / unspecified', '68.6%', '488'),
    ('Politics &amp; government', '36.1%', '257'),
    ('Football', '24.1%', '171'),
    ('Academia &amp; education', '23.3%', '166'),
    ('Media &amp; writing', '20.4%', '145'),
    ('Arts &amp; entertainment', '12.0%', '85'),
    ('Activism &amp; social work', '11.7%', '83'),
    ('Business &amp; finance', '4.4%', '31'),
    ('Law', '2.7%', '19'),
    ('Health', '1.7%', '12'),
]

BASELINE = [
    ('Uganda topics in Luganda', '3,592', 'ug_coverage_by_language.csv'),
    ('Luganda articles about places', '404', 'ug_edition_composition.csv'),
    ("Uganda's four Regions in Luganda", '0 of 4', 'ug_admin_units_coverage.csv'),
    ('Luganda Uganda-article stub rate', '24%', 'ug_incomplete_lg.csv'),
    ('Women to translate into Luganda', '65', 'ug_women_by_field.csv'),
    ('Women with no article anywhere', '2,168', 'ug_women_by_field.csv'),
    ("Women's biographies in Luganda", '1,066', 'ug_women_by_field.csv'),
    ('Topics missing from Luganda', '8,225', 'ug_missing_lg.csv'),
    ('Runyankore starter list ready', '255', 'ug_starter_nyn.csv'),
    ('Acholi starter list ready', '223', 'ug_starter_ach.csv'),
    ('Ugandan languages with no test project', '8', 'ug_incubator_targets.csv'),
]

LIMITS = [
    '<strong>Recall is a floor, not a true count.</strong> The Wikipedia '
    'Diversity Observatory uses a machine-learning classifier trained on '
    'hand-labelled data to catch culturally Ugandan topics with no formal '
    'Wikidata link to Uganda. This pipeline uses seven explicit rules '
    'instead, so the real corpus is somewhat larger than 14,149.',

    '<strong>It measures content, not people.</strong> Nothing here explains '
    '<em>why</em> gaps exist, who is editing, or whether new editors stay. '
    "Luganda's 73 active editors are the binding constraint on every "
    'recommendation, and this analysis has nothing to say about growing that '
    'number.',

    '<strong>Data quality is inherited.</strong> Wrong citizenship records '
    'and odd classifications flow straight through from Wikidata into the '
    'worklists. Expect to discard some rows by hand.',

    '<strong>The bot/human distinction is a judgement per edition</strong>, '
    'inferred from composition and stub rates: strong evidence, not a '
    'per-article test.',

    '<strong>Reader demand is English-shaped.</strong> Priority ranking uses '
    "English Wikipedia pageviews because Luganda's traffic is too small to "
    'rank on. What English readers want is a proxy for what Luganda readers '
    'want, and an imperfect one.',

    "<strong>The campaign attribution is inferred.</strong> Luganda's parity "
    'on women\'s biographies looks like organised effort, but this '
    'measures the outcome and not the cause. Confirm with the people who ran '
    'it.',

    '<strong>Incubator content is invisible to this analysis.</strong> Test '
    'wikis live at <code>incubator.wikimedia.org/wiki/Wp/&lt;code&gt;</code> '
    'and are not Wikidata sitelinks, so whatever Runyankore and Acholi have '
    'already written cannot be measured here. Their starter lists are '
    '<em>proposals</em>, not gap measurements: check them against the test '
    'wikis before assigning work, or some of it will already be done.',
]


def _findings():
    return join([
        _finding(
            '1. Counting articles gives the wrong answer',
            ['The edition with the most Uganda articles is not English. It is '
             '<strong>Cebuano</strong>, a Philippine language, with 6,765 and '
             '<strong>two</strong> of them are biographies of Ugandans. A bot '
             'generated thousands of articles about Ugandan streams, hills '
             'and sub-counties.',
             'Luganda has 3,592 Uganda articles, of which <strong>2,634 are '
             'about Ugandan people</strong>. Similar magnitude, completely '
             'different encyclopedia.'],
            ['Article counts cannot distinguish a written encyclopedia from a '
             'generated one. Any target, report or funding case built on raw '
             'counts can be satisfied by a bot without serving a single '
             'reader.',
             'Report <strong>composition</strong> (people, places, '
             'institutions), not volume.']),

        _finding(
            "2. The women's translation backlog is nearly gone",
            ['Of 3,340 Ugandan women in Wikidata, 1,112 have an English '
             'article and <strong>1,066 have a Luganda one</strong>. The '
             'English-to-Luganda backlog is <strong>65 people</strong>.',
             'In football and academia there is <strong>nothing left to '
             "translate</strong>; Luganda carries 44 women footballers to "
             "English's 38. Nineteen Ugandan women have a Luganda article and "
             'no English one. These are not stubs: median length 4,410 bytes, '
             'only 12% under 2&nbsp;KB.'],
            ['Another "translate women\'s biographies into '
             'Luganda" campaign would spend volunteer goodwill on a '
             'solved problem.',
             'The gap moved: <strong>2,168 Ugandan women have no article in '
             'any language</strong>. The work is now writing from sources, '
             'not translating.']),

        _finding(
            '3. Luganda has people but not places',
            ["Luganda's Uganda content splits <strong>2,634 people</strong> "
             'against <strong>404 places</strong>. English splits 3,188 to '
             '791; Swahili runs the other way at 638 to 3,039.',
             "All four of Uganda's Regions (Central, Eastern, Northern, "
             'Western) have no Luganda article. Neither do the Rwenzori '
             'Mountains, Mount Elgon, Lake Kyoga or the Nile, the last of '
             'which draws over 400,000 English readings every six months.'],
            ['The gap in Luganda is not a general shortage. It is a specific, '
             'nameable shortage of <strong>geography and institutions</strong>, '
             'in the language spoken where that geography is.',
             'This is a well-defined campaign with a finishable target list.']),

        _finding(
            '4. Uganda is over-described as data, under-described as '
            'encyclopedia',
            ['Wikidata holds <strong>68,587</strong> items whose country is '
             'Uganda. <strong>58,240 of them (85%) have no article in any '
             'language.</strong> They are bulk-imported registries: roughly '
             '15,000 primary schools, 24,000 settlements, 4,800 parishes.',
             "Meanwhile Luganda is still Uganda's only live Wikipedia, though "
             'not for much longer. <strong>Runyankore is approved and '
             'awaiting creation</strong>; <strong>Acholi is in Incubator with '
             'a request pending</strong>; eight further languages have no '
             'project at all.'],
            ["Part of Uganda's deepest gap is not fixable by editing: "
             '<strong>data without prose</strong>, and <strong>languages '
             'without a project</strong>.',
             'But the language work is no longer purely advocacy. Two '
             'projects are already in flight and need <strong>content, '
             'now</strong>. That is work this analysis can supply directly.']),
    ])


def _recommendations():
    return join([
        _rec('p1', 'P1', "Clear the women's translation backlog in one session",
             ['It is 65 people. That is finishable in a single editathon, and '
              'it converts a long-running programme into a completed one you '
              'can report as closed.',
              'Start with the most-read: <strong>Sheila Atim</strong> (95,196 '
              'readings in six months), <strong>Salma Lakhani</strong> '
              '(20,463), <strong>Judith Ayaa</strong>, <strong>Neema '
              'Iyer</strong>. Law is the one field where English is '
              "meaningfully ahead: 25 articles to Luganda's 17."],
             [('List', '<code>ug_women_translate_to_lg.csv</code>'),
              ('Effort', 'One editathon, ~10 editors'),
              ('Done when', '65 &rarr; 0')]),

        _rec('p1', 'P1', "Move women's programming from translating to writing",
             ['2,168 Ugandan women have no article in any language. Rank by '
              'how much Wikidata already records about each one: the better '
              'documented she is, the easier she is to source. Suggested '
              'first cohorts, chosen because they are both well-documented '
              'and concentrated:'
              '<ul>'
              '<li><strong>Politics &amp; government</strong> (257): '
              'Katushabe Ruth, Ntale Nsereko Madina, Priscilla Nyadoi</li>'
              '<li><strong>Academia &amp; education</strong> (166): Sylvia '
              'Angubua Baluka (microbiologist), Harriet Mpairwe, Annabella '
              'Habinka Basaza Ejiri</li>'
              '<li><strong>Football</strong> (171): Margret Kunihira, Phiona '
              'Nabbumba, Majidah Nantanda</li>'
              '<li><strong>Other sport</strong> (711): a large, sourceable '
              'cluster of badminton and basketball players</li>'
              '</ul>',
              'Note this is harder work than translation: it needs sources, '
              'not just language skills. Plan for librarian or journalist '
              'partnerships accordingly.'],
             [('Lists', '<code>ug_women_create_from_scratch.csv</code>, plus '
                        'one per field'),
              ('Effort', 'Recurring; sourcing-led'),
              ('Done when', 'Monthly fall in the no-article count')]),

        _rec('p2', 'P2', 'Run a "Places of Uganda" campaign in '
                         'Luganda',
             ['Luganda has 2,634 articles about people and 404 about places. '
              'The country itself is missing from its own language.',
              'High-demand targets already ranked: <strong>the Nile</strong> '
              '(401,934 readings), <strong>African Great Lakes</strong> '
              '(73,527), <strong>White Nile</strong> (49,323), '
              '<strong>Rwenzori Mountains</strong> (28,596), <strong>Mount '
              'Elgon</strong>, <strong>Lake Kyoga</strong>, <strong>Kibale '
              'National Park</strong>. Then the four Regions, none of which '
              'has a Luganda article.'],
             [('List', '<code>ug_missing_lg.csv</code>, filter on place types'),
              ('Effort', 'One quarter, geography-themed'),
              ('Done when', 'Luganda place count 404 to 600+')]),

        _rec('p2', 'P2', 'Report composition, and make it the metric everyone '
                         'quotes',
             ['Replace "how many Uganda articles does X have" '
              'with "how many are about people, places, '
              'institutions". Publish the dashboard each month so the '
              'User Group, the Foundation and partners are all reading the '
              'same number.',
              'This is the cheapest recommendation here and it protects every '
              'other one: it makes bot-inflated progress visible instead of '
              'flattering.'],
             [('Source', '<code>ug_edition_composition.csv</code>'),
              ('Effort', '20 min/month to re-run'),
              ('Done when', 'Used in the next grant report')]),

        _rec('p1', 'P1', 'Get Runyankore Wikipedia a day-one content plan '
                         'before it launches',
             ['<a href="https://incubator.wikimedia.org/wiki/Wp/nyn" '
              'target="_blank" rel="noopener">Runyankore</a> is '
              '<strong>already approved by the Language Committee and waiting '
              'on developers to create it</strong> (task T429189). It does '
              'not need advocacy. It needs content, and it needs it ready for '
              'the day the wiki appears.',
              "A new Wikipedia's first few hundred articles decide whether it "
              'reads as a real encyclopedia or an empty shell. A 255-topic '
              'starter list is already generated: 150 Uganda-wide essentials '
              'plus 105 topics from the Ankole sub-region where the language '
              'is actually spoken (Mbarara City, Mbarara University of '
              'Science and Technology, Ntungamo, Ntare School, Lake Mburo, '
              'Bushenyi).',
              'That Ankole half matters most. It is the content <em>no other '
              'edition has any reason to write</em>, and it is what makes a '
              'Runyankore Wikipedia worth reading rather than a thinner copy '
              'of English.'],
             [('List', '<code>ug_starter_nyn.csv</code>'),
              ('Effort', 'Pre-launch sprint; time-boxed by the developer queue'),
              ('Done when', 'Wiki launches with 250+ articles, not 5')]),

        _rec('p2', 'P2', "Build Acholi's case for approval with measured "
                         'content',
             ['<a href="https://incubator.wikimedia.org/wiki/Wp/ach" '
              'target="_blank" rel="noopener">Acholi</a> is an eligible test '
              'wiki with a request pending on Meta-Wiki. Approval turns on '
              'demonstrable content and an active community, so the useful '
              'contribution is volume in the right places.',
              'A 223-topic starter list is ready: 150 essentials plus 73 from '
              'the Acholi sub-region (Gulu City, Gulu University, Kitgum, St. '
              "Mary's Hospital Lacor, Atiak, the Pager River)."],
             [('List', '<code>ug_starter_ach.csv</code>'),
              ('Effort', 'Sustained; approval-driven'),
              ('Done when', 'Request approved by the Language Committee')]),

        _rec('p3', 'P3', 'Open an advocacy track for the eight languages with '
                         'no project',
             ['Rukiga, Lusoga, Lango, Ateso, Masaaba, Runyoro-Rutooro, Lugbara '
              'and Alur have no test project at all. No editing campaign can '
              'reach them; this needs Incubator test wikis, Language '
              'Committee engagement and university or cultural-institution '
              'partners.',
              'Runyankore and Acholi are the proof that the path works, and '
              'the template for how to walk it again.'],
             [('Scope', '8 languages with no test project'),
              ('Effort', 'Multi-year, partnership-led'),
              ('Done when', 'A third Ugandan language enters Incubator')]),

        _rec('p3', 'P3', 'Run a Wikidata quality drive alongside the writing',
             ["The analysis inherits Wikidata's errors: it surfaced an "
              'American actress recorded as a Ugandan citizen, and a Harry '
              'Potter school filed as a Ugandan administrative unit. Cleanup '
              'improves the encyclopedia and sharpens every future '
              'measurement at the same time.',
              'The 58,240 article-less school and village records are not '
              'waste: they are a foundation for later articles and for reuse '
              'outside Wikipedia. They just should never be counted as '
              'coverage.'],
             [('Source', '<code>ug_wikidata_only_by_type.csv</code>'),
              ('Effort', 'Ongoing, pairs with editathons'),
              ('Done when', 'Fewer false positives each cycle')]),

        _rec('p1', "DON'T", 'Do not bulk-generate stub articles to raise the '
                            'count',
             ['It is tempting: Uganda has 58,240 ready-made Wikidata records, '
              'and a bot could turn them into Luganda articles overnight. '
              'Article counts would jump and Luganda would leap up every '
              'ranking.',
              '<strong>Cebuano is the proof of what that produces.</strong> '
              'The largest Uganda encyclopedia in the world, and a reader '
              'looking for a Ugandan person finds two. It would also wreck '
              'the one thing Luganda currently does better than English: a '
              'genuinely written, human encyclopedia with a 12% stub rate on '
              "its women's biographies."],
             dont=True),
    ])


def _ninety_days():
    steps = [
        ('Weeks 1-2', 'Publish the baseline and agree the metric',
         'Circulate the dashboard. Get the User Group to adopt composition '
         'rather than article count as the reported measure, before any '
         'campaign starts and can be judged by the old one.'),
        ('Weeks 3-4', 'Translation sprint: clear all 65',
         'One editathon, one finishable list. Fast visible win, and it '
         'retires the translation programme cleanly rather than letting it '
         'drift.'),
        ('Weeks 5-8', 'First creation cohort: women in politics and academia',
         '423 candidates between the two fields, the best-documented first. '
         'Pair with a library or newsroom for sourcing, since this is the '
         'step where translation skills alone are not enough.'),
        ('Weeks 9-12', 'Places of Uganda, then re-measure',
         'Geography sprint on the ranked list, starting with the Nile and the '
         'four Regions. Then re-run the pipeline and publish the delta '
         'against this baseline: that comparison is the grant report.'),
        ('In parallel, throughout', 'Runyankore pre-launch sprint',
         'This one is not sequenced by us: it is sequenced by the developer '
         'queue, and the wiki could be created at any point. Run the '
         '255-topic starter list as a standing workstream with Ankole-region '
         'contributors so that whenever creation lands, the wiki opens with '
         'an encyclopedia rather than a main page.'),
    ]
    return ('<ol class="plan">'
            + ''.join(_step(*s) for s in steps) + '</ol>')


def _baseline_table():
    body = ''.join(
        f'<tr><td>{esc(name)}</td><td class="num">{esc(value)}</td>'
        f'<td><code>{esc(source)}</code></td></tr>'
        for name, value, source in BASELINE)
    return ('<div class="card scroller"><table><thead><tr><th>Indicator</th>'
            '<th class="num">Sep 2026</th><th>Where it comes from</th></tr>'
            f'</thead><tbody>{body}</tbody></table></div>')


def render(d):
    return join([
        '<div class="wrap">',
        tab_bar(d['nav']),

        '<header>',
        '<p class="eyebrow">Content Gap Analysis Wikimedia Community User '
        'Group Uganda</p>',
        "<h1>What Uganda's content gaps actually are, and how to close "
        'them</h1>',
        "<p class=\"lede\">A measured baseline of Uganda's presence across "
        "Wikipedia's 343 language editions, and eight recommendations that "
        'follow from it. Two of them redirect work the community is most '
        'likely doing already; two more supply content to Wikipedia projects '
        'that are already in flight.</p>',
        '<p class="stamp"><strong>Baseline: cycle 2026-09.</strong> The '
        'numbers on this page are deliberately frozen: a plan needs a fixed '
        'starting line to measure against. Living figures are in the '
        '<a href="uganda_content_gap.html">companion dashboard</a>, which '
        're-runs monthly.</p>',
        '</header>',

        '<h2>What was measured</h2>',
        '<p class="h2sub">Built from public Wikidata and Wikipedia interfaces '
        'only: no Wikimedia Cloud account, no database replicas. It runs on a '
        'laptop in about 20 minutes and refreshes on a monthly cycle.</p>',

        stat_tiles([
            {'k': 'Uganda topics', 'raw': True, 'v': '14,149',
             'd': 'with an article in at least one language'},
            {'k': 'In Luganda', 'raw': True, 'v': '3,592',
             'd': '25% of the corpus; 62% of all of lgwiki'},
            {'k': 'Missing from Luganda', 'raw': True, 'v': '8,225',
             'd': 'topics with a structural link to Uganda', 'alarm': True},
            {'k': 'Ugandan women tracked', 'raw': True, 'v': '3,340',
             'd': '2,168 have no article anywhere'},
        ]),

        '<h2>Four findings that change the plan</h2>',
        '<p class="h2sub">Each of these contradicts an assumption that would '
        'otherwise shape programming. They are the reason the recommendations '
        'below look different from a standard "translate more '
        'articles" plan.</p>',
        _findings(),

        '<h2>Where the writing work is</h2>',
        '<p class="h2sub">Ugandan women with no article in any language, by '
        'field. This is the single largest actionable backlog the analysis '
        'found, and it is what campaign targeting should follow.</p>',
        '<div class="card"><div class="bars">'
        + ''.join(_bar(*b) for b in BACKLOG_BARS) + '</div></div>',

        '<h2>Recommendations</h2>',
        '<p class="h2sub">Ordered by priority. Each names the file that '
        'contains the actual list, so none of this requires re-deriving the '
        'analysis.</p>',
        _recommendations(),

        '<h2>First 90 days</h2>',
        '<p class="h2sub">A sequence that produces a measurable delta by the '
        'end of the quarter, and one completed programme to report.</p>',
        _ninety_days(),

        '<h2>Baseline to measure against</h2>',
        '<p class="h2sub">Re-running the pipeline next month regenerates '
        'every one of these. Progress is the difference.</p>',
        _baseline_table(),

        '<h2>What this analysis cannot tell you</h2>',
        '<p class="h2sub">Stating the limits is part of the job. Every one of '
        'these is a real constraint on how far the recommendations above can '
        'be pushed.</p>',
        '<div class="card"><ul class="limits">'
        + ''.join(f'<li>{item}</li>' for item in LIMITS) + '</ul></div>',

        '<footer>',
        "<p><strong>Method.</strong> Uganda's content corpus is Wikidata "
        'items about Uganda holding at least one Wikipedia sitelink, gathered '
        'by seven retrieval strategies over the Wikidata Query Service, with '
        'article sizes from the MediaWiki API and pageviews from the '
        'Wikimedia REST API. Worklists are gated on a structural link to '
        f'Uganda rather than a keyword match. Modelled on the {WDO_LINK} by '
        'Marc Miquel and David Laniado, rebuilt to run without Wikimedia '
        'Cloud access.</p>',
        '<p><strong>Everything is reproducible.</strong> <code>python '
        'src_data/run_all.py</code> rebuilds all 24 datasets; <code>python '
        'src_viz/export_data.py</code> and <code>python '
        'src_viz/build_pages.py</code> rebuild every page. Stages checkpoint '
        'per calendar month. Source data from Wikidata (CC0) and Wikipedia '
        '(CC BY-SA).</p>',
        '</footer>',
        '</div>',
    ])
