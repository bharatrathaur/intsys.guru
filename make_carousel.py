"""Render a field note's LinkedIn carousel: notes-src/<slug>.carousel.html (slides of 1080x1350, stacked)
-> <out>/<slug>/slide-N.png, <slug>.pdf (upload this as a LinkedIn document post) and preview.jpg.

    python3 make_carousel.py <slug> [out_dir]      (out_dir defaults to ../carousels, outside the site)
"""
from PIL import Image
import os, re, subprocess, sys

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
W, H = 1080, 1350

os.chdir(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
out = os.path.join(sys.argv[2] if len(sys.argv) > 2 else '../carousels', slug)
os.makedirs(out, exist_ok=True)
src = os.path.abspath(f'notes-src/{slug}.carousel.html')
n = len(re.findall(r'<div class="s[ "]', open(src).read()))

full = os.path.join(out, '_full.png')
subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                f'--window-size={W},{H * n}', '--virtual-time-budget=4000', '--screenshot=' + full, 'file://' + src],
               capture_output=True, check=True)
sheet = Image.open(full).convert('RGB')
slides = [sheet.crop((0, i * H, W, (i + 1) * H)) for i in range(n)]
for i, s in enumerate(slides, 1):
    s.save(os.path.join(out, f'slide-{i}.png'))
slides[0].save(os.path.join(out, f'{slug}.pdf'), save_all=True, append_images=slides[1:], resolution=144)
# a small contact sheet to review all slides at once
t = [s.resize((W // 3, H // 3), Image.LANCZOS) for s in slides]
cols = 3; rows = (n + cols - 1) // cols; gap = 16
prev = Image.new('RGB', (cols * t[0].width + (cols + 1) * gap, rows * t[0].height + (rows + 1) * gap), (240, 241, 248))
for i, im in enumerate(t):
    prev.paste(im, (gap + (i % cols) * (im.width + gap), gap + (i // cols) * (im.height + gap)))
prev.save(os.path.join(out, 'preview.jpg'), quality=90)
os.remove(full)
print(n, 'slides ->', os.path.abspath(out))
