#!/usr/bin/env python3
"""Prerender the top stories of docs/latest.json into docs/index.html.

Why: the front page renders stories with JavaScript from latest.json.
Crawlers (and no-JS readers) should still see real content. This script
bakes a static snapshot of the newest stories into marked blocks of
index.html:

  <!-- STATIC:START --> ... <!-- STATIC:END -->   inside <ol id="stories">
  <!-- JSONLD:START --> ... <!-- JSONLD:END -->   JSON-LD ItemList in <head>

and refreshes docs/sitemap.xml lastmod values. It is run by the
"Render static snapshot" GitHub Actions workflow after every data push,
and can be run by hand:

  python3 tools/render_static.py [--docs-dir docs] [--count 15]

latest.json remains the single source of truth; this script is a pure,
idempotent view generator. It never modifies any JSON file. The page's
JavaScript clears the <ol> and re-renders live data on load, so the
snapshot only serves crawlers / first paint.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

SITE = "https://aihackernews.github.io"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parse_dt(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None


def fmt_date(iso):
    dt = parse_dt(iso)
    if not dt:
        return ""
    return f"{MONTHS[dt.month - 1]} {dt.day}, {dt.year}"


def domain_of(url):
    try:
        host = urlparse(url).hostname or ""
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def story_li(i, r):
    esc = html.escape
    dom = domain_of(r.get("url", ""))
    meta = []
    if r.get("published_at"):
        meta.append(f'<time datetime="{esc(r["published_at"], quote=True)}">'
                    f'{esc(fmt_date(r["published_at"]))}</time>')
    if r.get("source"):
        meta.append(esc(r["source"]))
    if r.get("submitted_by"):
        h = esc(r["submitted_by"], quote=True)
        meta.append(f'by <a href="https://github.com/{h}">@{esc(r["submitted_by"])}</a>')
    pills = " ".join(f'<span class="pill">{esc(t)}</span>' for t in r.get("tags") or [])
    parts = [
        "<li>",
        f'<div class="rank">{i}.</div>',
        '<div class="story">',
        f'<span class="titleline"><a href="{esc(r.get("url", ""), quote=True)}">'
        f'{esc(r.get("title", ""))}</a>',
    ]
    if dom:
        parts.append(f' <span class="domain">{esc(dom)}</span>')
    parts.append("</span>")
    if r.get("summary"):
        parts.append(f'<div class="summary">{esc(r["summary"])}</div>')
    sub = " · ".join(meta)
    if pills:
        sub = (sub + " " + pills) if sub else pills
    parts.append(f'<div class="subtext">{sub}</div>')
    parts.append("</div></li>")
    return "".join(parts)


def jsonld(records):
    items = []
    for i, r in enumerate(records, 1):
        art = {
            "@type": "Article",
            "headline": r.get("title", ""),
            "url": r.get("url", ""),
        }
        if r.get("published_at"):
            art["datePublished"] = r["published_at"]
        if r.get("summary"):
            art["description"] = r["summary"]
        if r.get("source"):
            art["publisher"] = {"@type": "Organization", "name": r["source"]}
        items.append({"@type": "ListItem", "position": i, "item": art})
    doc = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "AI Hacker News — latest stories",
        "itemListElement": items,
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{payload}\n</script>'


def replace_block(text, start_marker, end_marker, new_inner, label):
    pat = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.S)
    if not pat.search(text):
        raise SystemExit(f"error: markers for {label} not found in index.html")
    return pat.sub(lambda m: start_marker + new_inner + end_marker, text, count=1)


def sitemap(newest_iso):
    lastmod = ""
    dt = parse_dt(newest_iso) if newest_iso else None
    if dt:
        lastmod = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    def entry(loc, priority):
        lm = f"\n    <lastmod>{lastmod}</lastmod>" if lastmod else ""
        return (f"  <url>\n    <loc>{loc}</loc>{lm}\n"
                f"    <changefreq>hourly</changefreq>\n"
                f"    <priority>{priority}</priority>\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + entry(f"{SITE}/", "1.0") + "\n"
            + entry(f"{SITE}/submit.html", "0.5") + "\n"
            "</urlset>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-dir", default="docs")
    ap.add_argument("--count", type=int, default=15)
    args = ap.parse_args()

    docs = args.docs_dir.rstrip("/")
    with open(f"{docs}/latest.json", encoding="utf-8") as f:
        data = json.load(f)
    records = list(data.get("records", []))
    records.sort(key=lambda r: r.get("published_at") or "", reverse=True)
    top = records[: args.count]

    index_path = f"{docs}/index.html"
    with open(index_path, encoding="utf-8") as f:
        page = f.read()

    static_inner = "\n" + "\n".join(story_li(i, r) for i, r in enumerate(top, 1)) + "\n"
    page = replace_block(page, "<!-- STATIC:START -->", "<!-- STATIC:END -->",
                         static_inner, "static stories")
    page = replace_block(page, "<!-- JSONLD:START -->", "<!-- JSONLD:END -->",
                         "\n" + jsonld(top) + "\n", "JSON-LD")

    changed = []
    with open(index_path, encoding="utf-8") as f:
        if f.read() != page:
            changed.append("index.html")
    if changed:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(page)

    sm = sitemap(top[0].get("published_at") if top else "")
    sm_path = f"{docs}/sitemap.xml"
    try:
        with open(sm_path, encoding="utf-8") as f:
            old = f.read()
    except FileNotFoundError:
        old = ""
    if old != sm:
        with open(sm_path, "w", encoding="utf-8") as f:
            f.write(sm)
        changed.append("sitemap.xml")

    print(f"rendered {len(top)} stories; changed: {', '.join(changed) or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
