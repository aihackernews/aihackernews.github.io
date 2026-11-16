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

## Where news comes from (sourcing order)

`sources.json` in the repo root is the FIXED source list. Work in this order:

1. **Fixed list first.** Check every source in `sources.json` for new
   stories (lab blogs first — OpenAI, Anthropic, DeepMind, Meta AI, Mistral,
   xAI, Cohere, NVIDIA, Microsoft Research, AWS ML, Apple ML — then Hugging
   Face, arXiv cs.AI, Hacker News, then trade press). A `403`/`429` from a
   plain fetch usually means bot protection, not a dead source — fall back
   to browser/search for that source instead of dropping it.
2. **Keep the list current.** Every run: quick health check — a source that
   is genuinely gone (domain dead / section discontinued, confirmed via
   search, not just a bot block) gets removed. Once a week (the Sunday
   run): a full review — verify every URL still lands on the right section,
   fix moved URLs, and consider adding sources that have become important
   (a new major lab, a publication that keeps breaking AI stories). Keep the
   list focused (~15–25 sources); update the `updated` date and commit
   `sources.json` changes together with the news commit, noting list changes
   in the commit message.
3. **Open internet last.** After the fixed list, search the open web for
   anything the list missed (breaking news, smaller outlets, primary
   documents).

## News quality rules

- **Specific stories only — NEVER aggregator/roundup entries.** Every record
  must be ONE specific topic: a single announcement, release, deal, incident
  or finding, with a headline that names that topic. Do NOT add entries that
  are themselves summaries of many stories — daily briefings, "AI news
  today", week-in-review posts, roundups, digests, "every major release"
  listicles, or an aggregator's front page. Those pages are *sources to
  mine*, not entries: open them, find the individual stories inside, and add
  each worthwhile one as its own record, linking the specific story (prefer
  the original article the aggregator links to; a discussion link such as a
  Hacker News item page is acceptable when that is the link provided).
  Example: do NOT add "AI Frontier Daily Briefing: 2026-11-15
  (thecontext.dev)". DO add the specific story inside it: "Nvidia allegedly
  funded startups to buy its own GPUs" →
  https://news.ycombinator.com/item?id=50493251
  (The update script also rejects titles that look like briefings/roundups.)
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

## Community submissions

- `docs/submit.html` tells readers how to submit: open a GitHub issue at
  https://github.com/aihackernews/aihackernews.github.io/issues with a title
  starting `[NEW_POST] ` and a body in one of two formats — `LINK:` + URL, or
  `CONTENT:` + hand-written text.
- The hourly cron `aihackernews-submissions` processes open `[NEW_POST]`
  issues: validates (real AI news, not ads/promo, specific story, fresh,
  not a duplicate of latest.json), adds accepted ones via
  `tools/update_latest.py` (LINK → entry links the article; CONTENT → entry
  links the issue itself, source "Community submission"). Accepted records
  also carry `submitted_by` = the submitter's GitHub login, and the front
  page renders a "by @handle" credit in the story's meta line, before the
  tag pills. Cron-gathered
  stories never carry `submitted_by` (no credit line). Reopened appeals
  it cannot decide are escalated to the owner in chat, never auto-rejected
  twice.
- Issue bookkeeping (comments/closes) NEVER uses API tokens or the GitHub
  connector's write tools (those demand per-call human approval). Instead
  the processor commits a queue file `issue-actions/issue-<N>.json`
  ({"issue": N, "comment": string|null, "close":
  "completed"|"not_planned"|null}) and the `Issue bookkeeping` workflow
  (`.github/workflows/issue-bookkeeping.yml`) performs the action with its
  built-in GITHUB_TOKEN and deletes the queue file. This requires repo
  Settings → Actions → Workflow permissions = "Read and write permissions"
  (set Nov 15, 2026; end-to-end verified on test issue #2).

## Publishing notes

- Commit identity: author and committer are always `Muse
  <muse@aihackernews.local>`. NEVER put the repo owner's name in a commit
  author, committer, or message.

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
