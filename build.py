"""Inline the logo, photo and fonts into index.html so the page is one self-contained file."""
from PIL import Image
import base64, io, json, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def webp_uri(path, width):
    im = Image.open(path)
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'WEBP', quality=92)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

def jpeg_uri(path):
    return 'data:image/jpeg;base64,' + base64.b64encode(open(path, 'rb').read()).decode()

def font_uri(path):
    return 'data:font/woff2;base64,' + base64.b64encode(open(path, 'rb').read()).decode()

# Latin subsets only. IBM Plex Sans is one variable file covering every weight we use.
LATIN = ('U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, '
         'U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD')
FONTS = (f"  @font-face {{ font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 100 700; font-display: swap; "
         f"src: url({font_uri('fonts/IBMPlexSans-var.woff2')}) format('woff2'); unicode-range: {LATIN}; }}\n"
         f"  @font-face {{ font-family: 'Michroma'; font-style: normal; font-weight: 400; font-display: swap; "
         f"src: url({font_uri('fonts/Michroma-400.woff2')}) format('woff2'); unicode-range: {LATIN}; }}")

import build_notes

s = open('index.src.html').read()
notes = build_notes.build()
s = s.replace('{{NOTE_LINKS}}', json.dumps(notes['links'], ensure_ascii=False))
if notes['cards']:
    s = s.replace('{{NOTES}}', notes['cards']).replace('{{NOTES_MORE}}\n', notes['more'] + '\n' if notes['more'] else '')
    s = s.replace('{{NOTES_TOPICS}}\n', notes['topics'] + '\n' if notes['topics'] else '')
    s = s.replace('{{NOTES_ALL}}', f'All {notes["count"]} field notes →' if notes['count'] > 3 else 'All field notes →')
else:   # no published field notes yet: leave the section and its header link out of the page
    s = re.sub(r'<section id="notes">.*?</section>\n\n', '', s, flags=re.S)
    s = s.replace('      <a href="#notes" class="nav-notes">Field notes</a>\n', '')
    assert '{{NOTES}}' not in s and 'nav-notes">' not in s
s = s.replace('{{HEADER_CSS}}', open('header.css').read())
s = s.replace('{{FONTS}}', FONTS)
s = s.replace('{{LOGO}}', webp_uri('logo.webp', 900))
s = s.replace('{{LOGO_WHITE}}', webp_uri('logo-white.png', 800))
s = s.replace('{{PHOTO}}', jpeg_uri('photo.jpg'))
assert '{{' not in s
open('index.html', 'w').write(s)
print('built', len(s) // 1024, 'KB')
