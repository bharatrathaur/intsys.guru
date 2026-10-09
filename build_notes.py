"""Field notes: turn notes-src/*.md into notes/<slug>/index.html, the notes/ list page, sitemap.xml and the
home-page cards. Only notes with `status: published` in their front matter are built."""
from PIL import Image
import datetime, html, json, math, os, re, subprocess, urllib.parse

SITE = 'https://intsys.guru'
BOOK = 'https://fantastical.app/bharatrathaur'
UMAMI = ('<script defer src="https://cloud.umami.is/script.js" data-website-id="7283e81e-7919-433a-a250-63175c9607ab" '
         'data-domains="intsys.guru,www.intsys.guru"></script>')
# same owner switch as the home page: ?notrack / ?track
NOTRACK = """<script>(() => { try { const q = new URLSearchParams(location.search);
  if (!q.has('notrack') && !q.has('track')) return;
  q.has('notrack') ? localStorage.setItem('umami.disabled', '1') : localStorage.removeItem('umami.disabled');
  history.replaceState(null, '', location.pathname + location.hash); } catch (e) {} })();</script>"""


def read_note(path):
    text = open(path).read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    meta = dict(line.split(': ', 1) for line in m.group(1).splitlines() if ': ' in line)
    meta['slug'] = os.path.splitext(os.path.basename(path))[0]
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


def note_page(n):
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
    <p class="crumb wide"><a href="/notes/">Field notes</a> · {html.escape(n['topic'])}</p>
    <h1>{inline(n['title'])}</h1>
    <p class="byline"><img src="/notes/assets/bharat.webp" alt="" width="88" height="88"><span><b>Bharat Rathaur</b> · {nice(n['date'])} · {n['minutes']} min read</span></p>
    {top}
  </div>
</div>
<div class="col">
<article class="body">
{md_to_html(body.strip())}
</article>
<div class="next">
  <div class="cta">
    <h2>Something like this on your integrations?</h2>
    <p>Paste the error into What's breaking? for the likely cause and what to check first. Or talk it through with me.</p>
    <div class="btns">
      <a class="btn btn-primary" href="{BOOK}" target="_blank" rel="noopener" data-umami-event="note_book_call">Book a 30-minute call</a>
      <a class="btn btn-ghost" href="/#breaking" data-umami-event="note_whats_breaking">What's breaking?</a>
      <a class="btn btn-ghost" href="{mail}" data-umami-event="note_email">Email me</a>
    </div>
  </div>
  <p class="share"><a href="/notes/">← All field notes</a><a href="{share}" target="_blank" rel="noopener" data-umami-event="note_share">Share on LinkedIn</a></p>
</div>
</div>
</main>
""" + FOOT


def card(n, href, cls):
    return (f'<a class="{cls}" href="{href}" data-umami-event="note_open" data-umami-event-note="{n["slug"]}">'
            f'<p class="n-meta"><b>{html.escape(n["topic"])}</b> · {nice(n["date"])} · {n["minutes"]} min read</p>'
            f'<h3>{inline(n["title"])}</h3><p>{inline(n["summary"])}</p><span class="more">Read the note →</span></a>')


def list_page(notes):
    desc = 'Short, practical notes from real Workday integration work: what broke, why, and what to check. Examples generalised, no client data.'
    cards = '\n'.join(card(n, f'/notes/{n["slug"]}/', 'n-card').replace('<h3>', '<h2>').replace('</h3>', '</h2>') for n in notes)
    return head('Field notes · IntSys Guru', desc, f'{SITE}/notes/', 'website') + f"""<main>
<div class="note-hero">
  <div class="col">
    <p class="crumb wide">Field notes</p>
    <h1>Notes from the field</h1>
    <p class="dek">{desc}</p>
  </div>
</div>
<div class="col list">
{cards}
</div>
</main>
""" + FOOT


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
    """Write every note page, the list page and sitemap.xml; return the home-page cards (latest three)."""
    os.makedirs('notes', exist_ok=True)
    src = sorted(os.listdir('notes-src')) if os.path.isdir('notes-src') else []
    notes = [read_note(os.path.join('notes-src', f)) for f in src if f.endswith('.md')]
    notes = sorted((n for n in notes if n.get('status') == 'published'), key=lambda n: n['date'], reverse=True)
    if not notes:   # nothing published: no notes pages, and the sitemap lists only the home page
        open('sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       f'  <url><loc>{SITE}/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n')
        open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
        print('notes built: 0 (none published)')
        return ''
    assets()
    for n in notes:
        os.makedirs(f'notes/{n["slug"]}', exist_ok=True)
        open(f'notes/{n["slug"]}/index.html', 'w').write(note_page(n))
        og_card(n)
    open('notes/index.html', 'w').write(list_page(notes))
    urls = [(f'{SITE}/', datetime.date.today()), (f'{SITE}/notes/', notes[0]['date'] if notes else datetime.date.today())]
    urls += [(f'{SITE}/notes/{n["slug"]}/', n['date']) for n in notes]
    open('sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                   + ''.join(f'  <url><loc>{u}</loc><lastmod>{d.isoformat()}</lastmod></url>\n' for u, d in urls) + '</urlset>\n')
    open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    print('notes built:', len(notes))
    return '\n'.join(card(n, f'/notes/{n["slug"]}/', 'n-card') for n in notes[:3])


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()
