#!/usr/bin/env python3
"""Add new AI news records to docs/latest.json for AI Hacker News.

This is THE way to update the site's data. Never hand-edit latest.json's
structure and never edit docs/index.html to add news.

Rules (see AGENTS.md for the full spec):
  * Records are newest-first in { "records": [...], "link": <archive|null> }.
  * Freshness: only stories published within --max-age-days (default 7)
    are accepted; future-dated stories (> 1 day ahead) are rejected.
  * No duplicates: a story is dropped if its normalized URL *or* its
    normalized title already exists in latest.json or earlier in the batch.
    Normalization: lowercase, strip scheme/www/trailing slash and tracking
    query params (utm_*, ref, fbclid, gclid) for URLs; lowercase, collapse
    punctuation/whitespace for titles.
  * Rotation: latest.json keeps at most 1000 records. Overflow (the oldest
    records) is written to docs/archive_{YYYYMMDD}_{random4}.json with the
    same {records, link} shape; the new archive inherits latest.json's old
    `link`, and latest.json's `link` is updated to the new archive's name.

Usage:
  python3 tools/update_latest.py --input new_records.json [--docs-dir docs]
                                 [--max-age-days 7] [--dry-run]

Input: a JSON list of records, or {"records": [...]}. Each record:
  {"title": str, "url": str, "source": str, "summary": str (optional),
   "published_at": "YYYY-MM-DDTHH:MM:SSZ", "tags": [str, ...] (optional)}
`added_at` is stamped automatically. `id` is derived from the URL if absent.
"""
import argparse, json, random, re, string, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

MAX_RECORDS = 1000
TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "spm"}

def norm_url(u: str) -> str:
    try:
        p = urlparse(u.strip())
    except Exception:
        return u.strip().lower()
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    q = [(k, v) for k, v in parse_qsl(p.query)
         if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS]
    path = p.path.rstrip("/") or "/"
    return urlunparse(("", host, path, "", urlencode(q), "")).lower()

def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()

def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--docs-dir", default="docs")
    ap.add_argument("--max-age-days", type=float, default=7)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    docs = Path(args.docs_dir)
    latest_path = docs / "latest.json"
    now = datetime.now(timezone.utc)

    raw = json.loads(Path(args.input).read_text())
    batch = raw["records"] if isinstance(raw, dict) else raw
    if not isinstance(batch, list):
        sys.exit("input must be a JSON list or {\"records\": [...]}")

    current = json.loads(latest_path.read_text()) if latest_path.exists() else {"records": [], "link": None}
    existing_urls = {norm_url(r["url"]) for r in current["records"] if r.get("url")}
    existing_titles = {norm_title(r["title"]) for r in current["records"] if r.get("title")}

    accepted, rejected = [], []
    for r in batch:
        if not r.get("title") or not r.get("url"):
            rejected.append((r.get("title", "?"), "missing title/url")); continue
        pub = parse_dt(r.get("published_at"))
        if pub is None:
            rejected.append((r["title"], "missing/unparseable published_at")); continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age = now - pub
        if age > timedelta(days=args.max_age_days):
            rejected.append((r["title"], f"too old ({age.days}d > {args.max_age_days}d)")); continue
        if age < timedelta(days=-1):
            rejected.append((r["title"], "future-dated")); continue
        nu, nt = norm_url(r["url"]), norm_title(r["title"])
        if nu in existing_urls:
            rejected.append((r["title"], "duplicate URL")); continue
        if nt in existing_titles:
            rejected.append((r["title"], "duplicate title")); continue
        existing_urls.add(nu); existing_titles.add(nt)
        r = dict(r)
        r.setdefault("id", re.sub(r"[^a-z0-9]+", "-", nt)[:80].strip("-"))
        r.setdefault("summary", "")
        r.setdefault("source", urlparse(r["url"]).hostname or "")
        r.setdefault("tags", [])
        r["added_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        accepted.append(r)

    # Newest first: new batch (sorted newest-first) ahead of existing records.
    accepted.sort(key=lambda r: r.get("published_at", ""), reverse=True)
    merged = accepted + current["records"]

    archive_name = None
    if len(merged) > MAX_RECORDS:
        overflow = merged[MAX_RECORDS:]
        merged = merged[:MAX_RECORDS]
        rand4 = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        archive_name = f"archive_{now.strftime('%Y%m%d')}_{rand4}.json"
        archive_data = {"records": overflow, "link": current.get("link")}
        if not args.dry_run:
            (docs / archive_name).write_text(json.dumps(archive_data, indent=2, ensure_ascii=False) + "\n")
        new_link = archive_name
    else:
        new_link = current.get("link")

    out = {"records": merged, "link": new_link}
    if not args.dry_run:
        latest_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print(f"accepted: {len(accepted)}  rejected: {len(rejected)}  total in latest.json: {len(merged)}")
    for title, why in rejected:
        print(f"  rejected ({why}): {title}")
    if archive_name:
        print(f"rotated: created {archive_name} with {len(overflow)} records; latest.json link -> {archive_name}")
    if args.dry_run:
        print("(dry run — nothing written)")

if __name__ == "__main__":
    main()
