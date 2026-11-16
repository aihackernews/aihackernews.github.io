# AI Hacker News

Hacker News, but only AI. Live at https://aihackernews.github.io/

A single static page (`docs/index.html`) renders news from a JSON data file
(`docs/latest.json`). News updates never touch the HTML — a scheduled job
gathers fresh AI stories every few hours, de-duplicates them, and appends
them to the JSON. When `latest.json` grows past 1,000 records, the oldest
ones rotate into `docs/archive_{YYYYMMDD}_{random4}.json` files, chained
together by each file's `link` field so readers can scroll back forever.

**Agents: read [AGENTS.md](AGENTS.md) before changing anything** — it has the
data format, the freshness / no-duplicate rules, the rotation spec, and the
mandatory analytics snippet that every HTML page must carry.

Local preview:

```bash
cd docs && python3 -m http.server 8000   # then open http://localhost:8000
```

Add news manually:

```bash
python3 tools/update_latest.py --input my_batch.json --docs-dir docs
```
