# intsys.guru

Website for IntSysGuru LLC, Workday integration consulting. Served by GitHub Pages at https://intsys.guru.

| File | What it is |
|---|---|
| `index.html` | The published page. Built by `build.py`; don't edit it by hand. |
| `index.src.html` | The source to edit. Logo, photo and fonts appear as `{{LOGO}}`, `{{LOGO_WHITE}}`, `{{PHOTO}}`, `{{FONTS}}`. |
| `build.py` | Builds `index.html` from the source: `python3 build.py` (needs Pillow: `pip3 install pillow`). |
| `logo*.webp/png`, `photo.jpg` | Images embedded by `build.py`. |
| `fonts/` | IBM Plex Sans and Michroma (SIL Open Font License 1.1), embedded so visitors never load anything from Google. |
| `CNAME`, `.nojekyll` | GitHub Pages: custom domain, and serve files as they are. |

To preview locally: `python3 -m http.server 8765`, then open http://127.0.0.1:8765/index.html.
Analytics (Umami) only count on intsys.guru, so local previews don't affect the numbers.

To publish a change: edit `index.src.html`, run `python3 build.py`, commit, push. Pages redeploys in about a minute.
