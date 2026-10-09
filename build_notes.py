"""Field notes: turn notes-src/*.md into notes/<slug>/index.html, the notes/ list page (with its search index),
sitemap.xml, the home-page cards and the What's breaking? links. Only notes with `status: published` are built.

Front matter: title, date, summary, topic, status, and optionally
  short:     the "In short" answer shown first on the note
  featured:  yes  -> listed under "Start here" once there are enough notes
  breaking:  a What's breaking? pattern or symptom name (comma-separated for several); its result then links here

The list page grows its tools as the collection grows (thresholds below), so a small collection stays simple."""
from PIL import Image
import datetime, html, json, math, os, re, subprocess, urllib.parse

SITE = 'https://intsys.guru'
BOOK = 'https://fantastical.app/bharatrathaur'
UMAMI = ('<script defer src="https://cloud.umami.is/script.js" data-website-id="7283e81e-7919-433a-a250-63175c9607ab" '
         'data-domains="intsys.guru,www.intsys.guru"></script>')
# same owner switch as the home page: ?notrack / ?track
CHIPS_AT, SEARCH_AT, START_AT, YEARS_AT, PAGE = 6, 15, 10, 40, 20   # list-page tools switch on at these note counts
NOTRACK = """<script>(() => { try { const q = new URLSearchParams(location.search);
  if (!q.has('notrack') && !q.has('track')) return;
  q.has('notrack') ? localStorage.setItem('umami.disabled', '1') : localStorage.removeItem('umami.disabled');
  history.replaceState(null, '', location.pathname + location.hash); } catch (e) {} })();</script>"""


def read_note(path):
    text = open(path).read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    meta = dict(line.split(': ', 1) for line in m.group(1).splitlines() if ': ' in line)
    meta['slug'] = os.path.splitext(os.path.basename(path))[0]
    meta['path'] = path
    meta['body_md'] = m.group(2).strip()
    meta['date'] = datetime.date.fromisoformat(meta['date'])
    meta['minutes'] = max(1, math.ceil(len(meta['body_md'].split()) / 220))
    return meta


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    return s


def timeline(lines):
    """`date | label | note` lines are points; plain lines are the span between two points; `= text` is the caption.
    The second and later spans and points are drawn in the accent colour (that's where the clock is running)."""
    parts, caption, hot = [], '', False
    for l in lines:
        if l.startswith('= '):
            caption = l[2:]
        elif '|' in l:
            date, label, *note = [x.strip() for x in l.split('|')]
            hot = hot or bool(note)
            parts.append(f'<div class="pt{" hot" if note else ""}"><b>{inline(date)}</b><span>{inline(label)}</span>'
                         + (f'<em>{inline(note[0])}</em>' if note else '') + '</div>')
        else:
            parts.append(f'<div class="seg{" hot" if hot else ""}"><span>{inline(l)}</span></div>')
    return ('<figure class="tl"><div class="tl-row">' + ''.join(parts) + '</div>'
            + (f'<figcaption>{inline(caption)}</figcaption>' if caption else '') + '</figure>')


def md_to_html(md):
    out = []
    for block in re.split(r'\n\s*\n', md):
        lines = block.strip().splitlines()
        if lines[0] == ':::timeline':
            out.append(timeline([l for l in lines[1:] if l != ':::']))
        elif lines[0].startswith('## '):
            title = lines[0][3:]
            out.append(f'<h2 id="{re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")}">{inline(title)}</h2>')
        elif all(l.startswith('- ') for l in lines):
            out.append('<ul>\n' + '\n'.join(f'  <li>{inline(l[2:])}</li>' for l in lines) + '\n</ul>')
        elif lines[0].startswith('> '):
            out.append('<blockquote><p>' + inline(' '.join(l[2:] for l in lines)) + '</p></blockquote>')
        else:
            out.append('<p>' + inline(' '.join(lines)) + '</p>')
    return '\n'.join(out)


def nice(d):
    return d.strftime('%B ') + str(d.day) + d.strftime(', %Y')


def head(title, desc, url, og_type, extra='', image=f'{SITE}/og-image.png'):
    t, d = html.escape(title), html.escape(desc)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="IntSys Guru">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="627">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/notes/assets/mark.png">
<link rel="stylesheet" href="/header.css">
<link rel="stylesheet" href="/notes/notes.css">
{NOTRACK}
{UMAMI}
{extra}</head>
<body>
{shared_header()}
"""


def shared_header():
    """The home page's own header (between the shared-header markers in index.src.html), with its links pointed back at
    the home page, so every page has exactly the same top section."""
    s = open('index.src.html').read()
    s = s[s.index('<!-- shared-header:start'):s.index('<!-- shared-header:end -->')]
    s = s[s.index('<header'):].rstrip()
    s = s.replace('href="#"', 'href="/"').replace('href="#notes"', 'href="/notes/"').replace('href="#', 'href="/#')
    s = s.replace('{{LOGO}}', '/notes/assets/logo-home.webp')
    s = s.replace('rel="noopener">Book a call', 'rel="noopener" data-umami-event="note_book_call">Book a call')
    assert '{{' not in s
    return s


FOOT = """<footer>
  <div class="wrap">
    <span><img src="/notes/assets/logo-white.webp" alt="IntSys Guru" width="500" height="102">© 2026 IntSysGuru LLC · <a href="/">intsys.guru</a></span>
    <span class="legal">Independent consultant. Not affiliated with Workday, Inc. Workday is a trademark of Workday, Inc.<br>
      All other product names and trademarks belong to their owners. Examples are generalised; no client data is shown.</span>
  </div>
</footer>
</body>
</html>
"""


def plain(md):
    """Note body as plain words, for the search index."""
    t = re.sub(r'^:::.*$|^[#>=\-]+ ?', ' ', md, flags=re.M)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    return re.sub(r'\s+', ' ', re.sub(r'[*|`_]', ' ', t)).strip()


def related(n, notes):
    """Up to three other notes on the same topic, newest first."""
    rel = [m for m in notes if m is not n and m['topic'] == n['topic']][:3]
    if not rel:
        return ''
    items = ''.join(f'<li><a href="/notes/{m["slug"]}/" data-umami-event="note_related">{inline(m["title"])}</a>'
                    f'<span>{nice(m["date"])} · {m["minutes"]} min</span></li>' for m in rel)
    return f'<aside class="more-on"><h2>More on {html.escape(n["topic"])}</h2><ul>{items}</ul></aside>\n'


def note_page(n, notes=()):
    url = f'{SITE}/notes/{n["slug"]}/'
    image = url + 'og.jpg'
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': n['title'], 'description': n['summary'],
          'datePublished': n['date'].isoformat(), 'mainEntityOfPage': url, 'image': image,
          'author': {'@type': 'Person', 'name': 'Bharat Rathaur', 'url': SITE},
          'publisher': {'@type': 'Organization', 'name': 'IntSysGuru LLC', 'url': SITE}}
    extra = f'<script type="application/ld+json">{json.dumps(ld)}</script>\n'
    share = 'https://www.linkedin.com/sharing/share-offsite/?url=' + urllib.parse.quote(url, safe='')
    # the first screen carries the whole message: the "In short" answer, plus a timeline if the note opens with one
    body = n['body_md']
    top = ''
    if body.startswith(':::timeline'):
        tl, body = body.split('\n:::', 1)
        top = md_to_html(tl + '\n:::')
    if n.get('short'):  # one box: the answer, with the timeline (if any) as a slim strip underneath
        top = f'<aside class="short"><p><b>In short:</b> {inline(n["short"])}</p>{top}</aside>\n'
    mail = 'mailto:bharat@intsys.guru?subject=' + urllib.parse.quote('About: ' + n['title'])
    return head(n['title'] + ' · IntSys Guru', n['summary'], url, 'article', extra, image) + f"""<main>
<div class="note-hero">
  <div class="col">
    <p class="crumb wide">Field notes · <a href="/notes/?topic={urllib.parse.quote(n['topic'])}" title="More notes on {html.escape(n['topic'])}">{html.escape(n['topic'])}</a></p>
    <script>/* came from the notes list? go back to it as you left it: same filter, search and scroll */
    (() => {{ try {{ const r = new URL(document.referrer); if (r.origin === location.origin && r.pathname === '/notes/')
      addEventListener('click', e => {{ if (e.target.closest('a.to-list')) {{ e.preventDefault(); history.back(); }} }}); }} catch (e) {{}} }})();</script>
    <h1>{inline(n['title'])}</h1>
    <div class="byline-row">
      <p class="byline"><img src="/notes/assets/bharat.webp" alt="" width="88" height="88"><span><b>Bharat Rathaur</b> · {nice(n['date'])} · {n['minutes']} min read</span></p>
      <a class="to-list to-notes" href="/notes/" data-umami-event="note_back">← All field notes</a>
    </div>
    {top}
  </div>
</div>
<div class="col">
<article class="body">
{md_to_html(body.strip())}
</article>
{related(n, notes)}<div class="next">
  <div class="note-ask">
    <h2>Something like this on your integrations?</h2>
    <p>Paste the error into What's breaking? for the likely cause and what to check first. Or talk it through with me.</p>
    <div class="btns">
      <a class="btn btn-primary" href="{BOOK}" target="_blank" rel="noopener" data-umami-event="note_book_call">Book a 30-minute call</a>
      <a class="btn btn-ghost" href="/#breaking" data-umami-event="note_whats_breaking">What's breaking?</a>
      <a class="btn btn-ghost" href="{mail}" data-umami-event="note_email">Email me</a>
    </div>
  </div>
  <p class="note-foot"><a class="to-list" href="/notes/">← All field notes</a><a href="{share}" target="_blank" rel="noopener" data-umami-event="note_share">Share on LinkedIn</a></p>
</div>
</div>
</main>
""" + FOOT


def card(n, href, cls, h='h3'):
    return (f'<a class="{cls}" href="{href}" data-umami-event="note_open" data-umami-event-note="{n["slug"]}" '
            f'data-slug="{n["slug"]}" data-topic="{html.escape(n["topic"])}">'
            f'<p class="n-meta"><b>{html.escape(n["topic"])}</b> · {nice(n["date"])} · {n["minutes"]} min read</p>'
            f'<{h}>{inline(n["title"])}</{h}><p>{inline(n["summary"])}</p><span class="more">Read the note →</span></a>')


LIST_JS = """<script>
/* Field notes list: topic chips, search (full text, loaded on first use), "Show more". Without JavaScript every note is listed. */
(() => {
  const list = document.querySelector('.n-list'); if (!list) return;
  const cards = [...list.querySelectorAll('.n-card')], years = [...list.querySelectorAll('.n-year')];
  const q = document.querySelector('.n-q'), chips = [...document.querySelectorAll('.n-chip')], more = document.querySelector('.n-more');
  const count = document.querySelector('.n-count'), empty = document.querySelector('.n-empty'), PAGE = %d;
  const track = (n, d) => { try { window.umami && umami.track(n, d); } catch (e) {} };
  let limit = more ? PAGE : Infinity, topic = 'all', words = [], idx = null, searched = false;
  async function load() {
    if (idx) return;
    try { idx = {}; (await (await fetch('/notes/index.json')).json()).forEach(n => idx[n.s] = (n.t + ' ' + n.d + ' ' + n.p + ' ' + n.x).toLowerCase()); }
    catch (e) { idx = {}; }
  }
  function apply() {
    let shown = 0, total = 0;
    cards.forEach(c => {
      const hay = (idx && idx[c.dataset.slug]) || c.textContent.toLowerCase();
      const ok = (topic === 'all' || c.dataset.topic === topic) && words.every(w => hay.includes(w));
      if (ok) total++;
      c.hidden = !(ok && shown < limit); if (!c.hidden) shown++;
    });
    years.forEach(y => { let el = y.nextElementSibling, any = false;
      while (el && !el.classList.contains('n-year')) { if (!el.hidden) any = true; el = el.nextElementSibling; } y.hidden = !any; });
    if (count) count.textContent = topic === 'all' && !words.length ? `${cards.length} notes` : `${total} of ${cards.length} notes`;
    if (empty) empty.hidden = total > 0;
    if (more) { more.hidden = shown >= total; more.textContent = `Show more (${total - shown} more)`; }
  }
  // the address keeps the current view (?topic=…&q=…&n=…), so Back from a note, a reload or a shared link shows the same list
  function sync() {
    const p = new URLSearchParams();
    if (topic !== 'all') p.set('topic', topic);
    if (q && q.value.trim()) p.set('q', q.value.trim());
    if (more && limit > PAGE) p.set('n', limit);
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }
  const pressChip = t => chips.forEach(x => x.setAttribute('aria-pressed', x.dataset.topic === t));
  if (q) {
    let t; q.addEventListener('focus', load, { once: true });
    q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(async () => {
      await load(); words = q.value.toLowerCase().split(/\\s+/).filter(Boolean); limit = more ? PAGE : Infinity; apply(); sync();
      if (words.length && !searched) { searched = true; track('notes_search'); }   // that someone searched, never what
    }, 150); });
  }
  chips.forEach(ch => ch.onclick = () => {
    topic = ch.dataset.topic; pressChip(topic); limit = more ? PAGE : Infinity; apply(); sync();
    track('notes_topic', { topic });
  });
  if (more) more.onclick = () => { limit += PAGE; apply(); sync(); };
  (async () => {
    const p = new URLSearchParams(location.search);
    if (p.get('topic') && cards.some(c => c.dataset.topic === p.get('topic'))) { topic = p.get('topic'); pressChip(topic); }
    if (more && +p.get('n') > PAGE) limit = +p.get('n');
    if (q && p.get('q')) { q.value = p.get('q'); await load(); words = q.value.toLowerCase().split(/\\s+/).filter(Boolean); }
    apply();
  })();
})();
</script>
""" % PAGE


def list_page(notes):
    desc = 'Short, practical notes from real Workday integration work: what broke, why, and what to check. Examples generalised, no client data.'
    n_all, years = len(notes), len(notes) >= YEARS_AT
    h = 'h3' if years else 'h2'
    tools = ''
    feat = [n for n in notes if n.get('featured', '').lower() == 'yes'][:4]
    if feat and n_all >= START_AT:
        tools += ('<section class="n-start"><h2 class="wide">Start here</h2><div class="n-start-grid">'
                  + ''.join(f'<a class="n-feat" href="/notes/{n["slug"]}/" data-umami-event="note_open" data-umami-event-note="{n["slug"]}">'
                            f'<b>{html.escape(n["topic"])}</b><span>{inline(n["title"])}</span></a>' for n in feat) + '</div></section>\n')
    bar = ''
    if n_all >= SEARCH_AT:
        bar += ('<label class="n-search"><span class="sr">Search field notes</span>'
                '<input class="n-q" type="search" placeholder="Search, e.g. rehire or 834" autocomplete="off"></label>')
    if n_all >= CHIPS_AT:
        topics = {}
        for n in notes:
            topics[n['topic']] = topics.get(n['topic'], 0) + 1
        bar += ('<div class="n-chips" role="group" aria-label="Filter by topic">'
                f'<button type="button" class="n-chip" data-topic="all" aria-pressed="true">All <i>{n_all}</i></button>'
                + ''.join(f'<button type="button" class="n-chip" data-topic="{html.escape(t)}" aria-pressed="false">{html.escape(t)} <i>{c}</i></button>'
                          for t, c in sorted(topics.items(), key=lambda kv: (-kv[1], kv[0]))) + '</div>')
    if bar:
        tools += f'<div class="n-tools">{bar}<p class="n-count" aria-live="polite"></p></div>\n'
    rows, last = [], None
    for n in notes:
        if years and n['date'].year != last:
            last = n['date'].year
            rows.append(f'<h2 class="n-year wide">{last}</h2>')
        rows.append(card(n, f'/notes/{n["slug"]}/', 'n-card', h))
    more = '<button type="button" class="n-more" hidden>Show more</button>' if n_all > PAGE else ''
    empty = ('<p class="n-empty" hidden>No notes match. Try fewer words, or '
             '<a href="mailto:bharat@intsys.guru?subject=Field%20note%20request">ask me about it</a>.</p>')
    return head('Field notes · IntSys Guru', desc, f'{SITE}/notes/', 'website') + f"""<main>
<div class="note-hero">
  <div class="col">
    <p class="crumb wide">Field notes</p>
    <h1>Notes from the field</h1>
    <p class="dek">{desc}</p>
  </div>
</div>
<div class="col list">
{tools}<div class="n-list">
{chr(10).join(rows)}
</div>
{empty}
{more}
</div>
</main>
{LIST_JS if (bar or more) else ''}""" + FOOT


def assets():
    os.makedirs('notes/assets', exist_ok=True)
    def save(src, dst, width, fmt='WEBP'):
        im = Image.open(src)
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst, fmt, quality=88)
    save('logo.webp', 'notes/assets/logo-home.webp', 900)   # same logo and size as the home page header
    save('logo-white.png', 'notes/assets/logo-white.webp', 500)
    im = Image.open('photo.jpg'); s = min(im.size)
    im.crop(((im.width - s) // 2, 0, (im.width + s) // 2, s)).resize((88, 88), Image.LANCZOS).save('notes/assets/bharat.webp', 'WEBP', quality=88)
    # favicon: the coloured mark from the middle of the logo
    logo = Image.open('logo.webp').convert('RGBA'); px = logo.load()
    xs, ys = [], []
    for y in range(0, min(300, logo.height)):
        for x in range(logo.width // 2 - 200, logo.width // 2 + 200):
            r, g, b, a = px[x, y]
            if a > 40 and max(r, g, b) - min(r, g, b) > 60: xs.append(x); ys.append(y)
    logo.crop((min(xs), min(ys), max(xs) + 1, max(ys) + 1)).resize((64, 64), Image.LANCZOS).save('notes/assets/mark.png')


CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def og_card(n):
    """Render the note's own 1200x627 link-preview card to notes/<slug>/og.jpg with headless Chrome."""
    here = os.getcwd()
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: 'IBM Plex Sans'; font-weight: 100 700; src: url(file://{here}/fonts/IBMPlexSans-var.woff2) format('woff2'); }}
@font-face {{ font-family: 'Michroma'; src: url(file://{here}/fonts/Michroma-400.woff2) format('woff2'); }}
html, body {{ margin: 0; }}
.c {{ width: 1200px; height: 627px; position: relative; overflow: hidden; color: #fff; font-family: 'IBM Plex Sans', sans-serif;
  background: radial-gradient(circle at 92% 8%, rgba(188,31,45,.6), transparent 40%), radial-gradient(circle at 4% 100%, rgba(47,49,146,.95), transparent 48%),
  radial-gradient(circle at 66% 118%, rgba(248,173,64,.32), transparent 42%), #10123a; }}
.in {{ position: absolute; left: 72px; right: 72px; top: 60px; }}
.k {{ font-family: 'Michroma', sans-serif; font-size: 19px; letter-spacing: .16em; text-transform: uppercase; color: #ffc15e; margin: 0 0 26px; }}
h1 {{ font-size: 62px; line-height: 1.1; letter-spacing: -.02em; margin: 0; max-width: 1000px; }}
.d {{ font-size: 28px; line-height: 1.4; color: #c9cbe6; margin: 26px 0 0; max-width: 940px; }}
.foot {{ position: absolute; left: 72px; right: 72px; bottom: 50px; display: flex; align-items: center; justify-content: space-between; }}
.by {{ display: flex; align-items: center; gap: 16px; font-size: 24px; color: #d3d5f0; }}
.by img {{ width: 64px; height: 64px; border-radius: 50%; border: 3px solid rgba(255,255,255,.25); }}
.by b {{ color: #fff; }}
.logo {{ height: 64px; }}
.bar {{ position: absolute; left: 0; right: 0; bottom: 0; height: 10px; background: linear-gradient(90deg, #f8ad40, #e8572f 35%, #bc1f2d 60%, #2f3192); }}
</style></head><body><div class="c">
<div class="in"><p class="k">Field note · {html.escape(n['topic'])}</p><h1>{inline(n['title'])}</h1><p class="d">{inline(n['summary'])}</p></div>
<div class="foot"><span class="by"><img src="file://{here}/photo.jpg" style="object-fit: cover; object-position: top"><span><b>Bharat Rathaur</b> · intsys.guru</span></span>
<img class="logo" src="file://{here}/logo-white.png"></div><div class="bar"></div></div></body></html>"""
    tmp_html, tmp_png = os.path.join(here, '.og-card.tmp.html'), os.path.join(here, '.og-card.tmp.png')
    open(tmp_html, 'w').write(page)
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                    '--window-size=1200,627', '--virtual-time-budget=3000', '--screenshot=' + tmp_png, 'file://' + tmp_html],
                   capture_output=True, check=True)
    Image.open(tmp_png).convert('RGB').crop((0, 0, 1200, 627)).save(f'notes/{n["slug"]}/og.jpg', 'JPEG', quality=88)
    os.remove(tmp_html); os.remove(tmp_png)


def build():
    """Write every note page, the list page, its search index and sitemap.xml. Returns what the home page needs:
    {'cards': latest three, 'count': n, 'links': What's breaking? name -> newest note about it}."""
    os.makedirs('notes', exist_ok=True)
    src = sorted(os.listdir('notes-src')) if os.path.isdir('notes-src') else []
    notes = [read_note(os.path.join('notes-src', f)) for f in src if f.endswith('.md')]
    notes = sorted((n for n in notes if n.get('status') == 'published'), key=lambda n: n['date'], reverse=True)
    if not notes:   # nothing published: no notes pages, and the sitemap lists only the home page
        open('sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       f'  <url><loc>{SITE}/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n')
        open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
        print('notes built: 0 (none published)')
        return {'cards': '', 'count': 0, 'links': {}, 'more': '', 'topics': ''}
    assets()
    for n in notes:
        os.makedirs(f'notes/{n["slug"]}', exist_ok=True)
        open(f'notes/{n["slug"]}/index.html', 'w').write(note_page(n, notes))
        og = f'notes/{n["slug"]}/og.jpg'   # re-render the link card only when the note changed
        if not os.environ.get('NOTES_SKIP_OG') and (not os.path.exists(og) or os.path.getmtime(og) < os.path.getmtime(n['path'])):
            og_card(n)
    open('notes/index.html', 'w').write(list_page(notes))
    json.dump([{'s': n['slug'], 't': n['title'], 'd': n['summary'], 'p': n['topic'], 'y': n['date'].isoformat(), 'x': plain(n['body_md'])}
               for n in notes], open('notes/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    links = {}
    for n in reversed(notes):   # oldest first, so the newest note on a name wins
        for name in filter(None, (x.strip() for x in n.get('breaking', '').split(','))):
            links[name] = {'t': n['title'], 'u': f'/notes/{n["slug"]}/'}
    urls = [(f'{SITE}/', datetime.date.today()), (f'{SITE}/notes/', notes[0]['date'] if notes else datetime.date.today())]
    urls += [(f'{SITE}/notes/{n["slug"]}/', n['date']) for n in notes]
    open('sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                   + ''.join(f'  <url><loc>{u}</loc><lastmod>{d.isoformat()}</lastmod></url>\n' for u, d in urls) + '</urlset>\n')
    open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    print('notes built:', len(notes))
    return {'cards': '\n'.join(card(n, f'/notes/{n["slug"]}/', 'n-card') for n in notes[:3]), 'count': len(notes), 'links': links,
            'more': home_more(notes), 'topics': home_topics(notes)}


HOME_MORE_AT, HOME_TOPICS_AT = 4, 10   # home page: compact list from 4 notes, topic links from 10


def home_more(notes):
    """Notes 4-8 as a compact list under the three newest cards."""
    if len(notes) < HOME_MORE_AT:
        return ''
    return ('    <ul class="n-list-more">' + ''.join(
        f'<li><a href="/notes/{n["slug"]}/" data-umami-event="note_open" data-umami-event-note="{n["slug"]}">'
        f'<b>{inline(n["title"])}</b><span><em>{html.escape(n["topic"])}</em> · {nice(n["date"])}</span></a></li>'
        for n in notes[3:8]) + '</ul>')


def home_topics(notes):
    """Topic links, busiest first, each opening the notes page filtered to it."""
    if len(notes) < HOME_TOPICS_AT:
        return ''
    topics = {}
    for n in notes:
        topics[n['topic']] = topics.get(n['topic'], 0) + 1
    return ('    <div class="n-topics"><span>Browse by topic</span>' + ''.join(
        f'<a href="/notes/?topic={urllib.parse.quote(t)}" data-umami-event="notes_topic_home">{html.escape(t)} <i>{c}</i></a>'
        for t, c in sorted(topics.items(), key=lambda kv: (-kv[1], kv[0]))) + '</div>')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()
