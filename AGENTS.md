# AGENTS.md — Instructions for every LLM agent working on AI Hacker News

Read this whole file before changing anything in this repository.

## What this is

**AI Hacker News** — a Hacker News–style site focused only on AI, served by
GitHub Pages from the `docs/` folder of this repo
(`git@github.com:aihackernews/aihackernews.github.io.git`, branch `main`).
Live at https://aihackernews.github.io/

## ⚠️ MANDATORY: analytics snippet on every HTML page

Every HTML page in this site MUST carry the following snippet in its `<head>`,
verbatim and unmodified. Never remove it, never "fix" or reformat it, and add
it to any new HTML page you create:

```html
<script async src="https://www.googletagmanager.com/gtm.js?id=GTM-TJZ293FB"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
</script>
```

## Architecture (keep it simple)

- `docs/index.html` — the ONLY page. It is static and should almost never
  change. It contains no news data.
- `docs/latest.json` — the current news data. The page always loads this
  file first.
- `docs/archive_{YYYYMMDD}_{random 4 chars}.json` — older news, created
  automatically by rotation (see below). Immutable once created: never edit
  an archive's records.
- `tools/update_latest.py` — the only supported way to add news and rotate
  archives. Use it; do not hand-roll the rotation logic.

## Data format

Every data file (`latest.json` and every archive) has exactly this shape:

```json
{ "records": [ {record}, {record}, ... ], "link": "archive_20261115_a1b2.json" }
```

- `records` — newest first.
- `link` — the filename of the next-older archive, or `null` if there is none.
  The page follows this chain: when a reader scrolls past the end of one
  file, the page fetches the file named in `link`, then that file's `link`,
  and so on.
- Record fields:
  - `id` — short slug, unique, derived from the title
  - `title` — headline, as published by the source
  - `url` — the original article URL (the source, not an aggregator copy)
  - `source` — publisher name (e.g. "TechCrunch")
  - `summary` — one or two plain sentences, your own words
  - `published_at` — ISO 8601 UTC, e.g. `2026-11-15T12:00:00Z`
  - `added_at` — ISO 8601 UTC, stamped by the update script
  - `tags` — a few short lowercase tags

## News quality rules

- **Fresh only:** only add stories published within the last 7 days
  (the update script rejects anything older, and anything future-dated).
- **No duplicates:** never add a story whose URL or title already exists in
  `latest.json` — including the same story under a different URL from a
  different outlet covering the same announcement. When in doubt, skip it.
  (The update script enforces URL/title de-duplication; the cross-outlet
  same-story check is on you.)
- **AI only:** models, research, AI products/tools, AI startups and funding,
  AI policy/regulation, AI infrastructure. No general tech news.
- Prefer primary sources and reputable outlets; link the original article.

## Rotation rule (archive creation)

Implemented by `tools/update_latest.py` — the spec it follows:

1. `latest.json` holds at most **1000** records, newest first.
2. When it would exceed 1000, the overflow (oldest records) moves into a new
   file named `archive_{YYYYMMDD}_{random 4 chars}.json` (date = rotation
   date, UTC), with the same `{records, link}` shape.
3. The new archive **inherits** the `link` that `latest.json` had, and
   `latest.json`'s `link` is updated to point to the new archive.
4. Archives are never modified afterwards.

## Updating the news (the normal workflow)

1. Gather fresh AI news from the web (last 7 days, no duplicates — see above).
2. Write the batch to a temp JSON file: a list of records with `title`,
   `url`, `source`, `summary`, `published_at`, `tags`.
3. Run: `python3 tools/update_latest.py --input <batch.json> --docs-dir docs`
   (add `--dry-run` first if you want to preview accept/reject decisions).
4. Commit **only** the changed JSON files under `docs/` and push to `main`:
   `git add docs/*.json && git commit -m "news: <summary>" && git push`
5. Verify the live site loads and shows the new stories:
   https://aihackernews.github.io/ (GitHub Pages can take a few minutes;
   also check https://aihackernews.github.io/latest.json directly).

A scheduled agent job ("AI Hacker News — gather AI news every 3 hours")
normally does this automatically.

## Publishing notes

- Push access uses a DEDICATED SSH deploy key for this repo only:
  `~/.ssh/id_ed25519_aihackernews` (fingerprint
  `SHA256:pwjiVYfHj7UNuVhLilfmP3S9m2Wfw8teKsqs/Fo5C6c`), via the SSH host alias
  `github-aihackernews` defined in `~/.ssh/config`. Clone/push with the
  remote `git@github-aihackernews:aihackernews/aihackernews.github.io.git`
  and `core.sshCommand "ssh -F /home/hatch/.ssh/config"`. Do NOT use the
  default `~/.ssh/id_ed25519` key for this repo — that one belongs to
  Plain Earnings.
- GitHub Pages must be set to serve branch `main`, folder `/docs`
  (repo Settings → Pages). If the live URL 404s, that setting is the cause.
- Commit directly to `main`; no branches or PRs for routine news updates.
- Do NOT edit `docs/index.html` for news. Only edit it for genuine site
  changes — and if you do, the analytics snippet rule above still applies.
