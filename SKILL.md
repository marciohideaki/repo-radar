---
name: repo-radar
description: >
  Monitors, analyses and classifies GitHub repositories as a radar/intelligence system.
  Activate when the user mentions: repo analysis, open-source monitoring, library maturity
  evaluation, deciding whether to incorporate a GitHub project, checking repo evolution,
  classifying repos as interesting/watch/discard, querying radar.db, or any task related
  to the pipeline: add → analyse → classify → monitor → port.
  Also activate when the user asks “is X worth using?”, “is this project still active?”,
  “what can I port from this repo?”, or “I need to check my repos”.
---

# Repo Radar Skill

Local GitHub repository intelligence system.
Analyses, classifies and tracks repo evolution using heuristics + LLM verdict.

## System Structure

```
repo-radar/
├── repo_radar/
│   ├── cli.py          ← entry point (click)
│   ├── github.py       ← GitHub API (httpx + auth)
│   ├── analysis.py     ← local heuristics (pathlib)
│   ├── database.py     ← SQLite (stdlib, no binary needed)
│   ├── report.py       ← HTML, Markdown, terminal (rich)
│   └── llm/
│       ├── anthropic.py  ← Claude
│       ├── gemini.py     ← Gemini
│       ├── openai.py     ← OpenAI / Codex
│       └── ollama.py     ← Ollama (local, no cost)
├── data/               ← radar.db + reports (auto-created)
└── repos/              ← cloned repos (auto-created)
```

## Available Commands

| Command | Usage | What it does |
|---------|-------|--------------|
| `add`    | `repo-radar add <url>` | Clone, analyse, save to radar |
| `check`  | `repo-radar check <url\|all>` | Re-check, detect evolution |
| `list`   | `repo-radar list` | List all repos in coloured table |
| `show`   | `repo-radar show <name>` | Full detail of one repo |
| `report` | `repo-radar report` | Generate HTML + Markdown |
| `note`   | `repo-radar note <url> -c CLASS -t target -n "notes"` | Edit notes/classification |
| `tag`    | `repo-radar tag <url> tag1,tag2` | Add tags |
| `remove` | `repo-radar remove <url>` | Remove from radar (keeps history) |
| `status` | `repo-radar status` | DB stats + GitHub rate limit |

## Classifications

| Class | Emoji | Criterion |
|-------|-------|-----------|
| `INTERESTING` | 🟢 | High potential, active, coherent docs |
| `INCORPORATE` | 🟡 | Contains something portable to our stack |
| `WATCH` | 🔵 | Promising but immature — monitor |
| `REDUNDANT` | ⚪ | Duplicates already-catalogued functionality |
| `DISCARD` | 🔴 | Abandoned, low quality, misleading docs |

## LLM Configuration

Set `LLM_PROVIDER` in `.env` to choose the verdict engine:

```env
LLM_PROVIDER=claude    # Claude (Anthropic) — default
LLM_PROVIDER=gemini    # Gemini (Google)
LLM_PROVIDER=openai    # GPT-4o (OpenAI / Codex)
LLM_PROVIDER=ollama    # Local model (no cost, no internet)
```

Fallback: if LLM is unavailable or misconfigured, heuristic classification is used automatically.

## How Claude should use this skill

### When the user wants to add a repo:
1. Run: `repo-radar add <url>`
2. Explain the returned classification and why
3. Suggest next steps (e.g. `note`, `tag`, mark as INCORPORATE)

### When the user wants to know what’s worth using:
1. Run: `repo-radar list`
2. Focus on INTERESTING and INCORPORATE
3. Explain which have the highest `interest_score` and why

### When the user asks about a project’s evolution:
1. Run: `repo-radar check <url>`
2. Interpret the `delta_summary` returned
3. Compare current score with history in `data/radar.db`

### Direct database queries:
```bash
# SQLite via Python one-liner
python3 -c "
import sqlite3, json
con = sqlite3.connect('data/radar.db')
con.row_factory = sqlite3.Row
rows = con.execute(\"SELECT name, classification, interest_score, stars FROM repositories ORDER BY interest_score DESC\").fetchall()
for r in rows: print(dict(r))
"
```

### Find what to incorporate:
```bash
python3 -c "
import sqlite3
con = sqlite3.connect('data/radar.db')
rows = con.execute(\"SELECT r.name, r.incorporate_target, f.feature_name FROM repositories r JOIN features f ON f.repo_id=r.id WHERE r.classification IN ('INTERESTING','INCORPORATE') ORDER BY r.interest_score DESC\").fetchall()
for r in rows: print(r)
"
```

## Suggested Workflow (Periodic Monitoring)

```
1. Add repos of interest:
   repo-radar add https://github.com/user/repo

2. Annotate intentions:
   repo-radar note https://github.com/user/repo -c INCORPORATE -t "my-project"

3. Weekly review:
   repo-radar check all

4. Generate updated report:
   repo-radar report
   # Open data/radar-report.html in browser
```

## Prerequisites

- Python 3.9+
- Git
- `pip install -e .` (installs all dependencies)

## Notes

- Heuristic analysis is 100% local — no API cost
- GitHub API: 60 req/hour unauthenticated, 5000/hour with `GITHUB_TOKEN`
- `radar.db` checks are append-only — full history preserved
- Cross-platform: Windows, Linux, macOS
