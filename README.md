# 🔭 Repo Radar

**GitHub repository intelligence system** — cross-platform (Windows, Linux, macOS), multi-LLM, no infrastructure required.

> Analyse, classify and track GitHub repos with heuristic scoring + LLM verdict.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/marciohideaki/repo-radar
cd repo-radar
pip install -e .

# 2. Configure your LLM (choose one)
cp .env.example .env
# Edit .env: set LLM_PROVIDER and the matching API key

# 3. Start analysing
repo-radar add https://github.com/crewaiinc/crewai
repo-radar list
repo-radar report
# Open data/radar-report.html 🎉
```

## Supported LLMs

| Provider | Set in `.env` | Key needed |
|----------|---------------|------------|
| **Claude** (Anthropic) | `LLM_PROVIDER=claude` | `ANTHROPIC_API_KEY` |
| **Gemini** (Google) | `LLM_PROVIDER=gemini` | `GEMINI_API_KEY` |
| **OpenAI / Codex** | `LLM_PROVIDER=openai` | `OPENAI_API_KEY` |
| **Ollama** (local) | `LLM_PROVIDER=ollama` | none (free) |

If no LLM is configured, heuristic classification is used automatically as fallback.

## How It Works

```
Input: GitHub URL
  ↓
[github.py]    → Fetch: stars, forks, commits, language, license
  ↓
[analysis.py]  → Local heuristics: doc, code, coherence, maturity scores
  ↓
[llm/]         → LLM verdict: “Worth it?” + rationale (Claude/Gemini/OpenAI/Ollama)
  ↓
[database.py]  → Save to SQLite (append-only history)
  ↓
[report.py]    → HTML dashboard + Markdown report
```

## Commands

```bash
repo-radar add <url>                        # Add and analyse
repo-radar check <url|all>                  # Re-check, detect changes
repo-radar list                             # Table of all repos
repo-radar list -c INTERESTING              # Filter by classification
repo-radar show <name>                      # Full detail
repo-radar report                           # Generate HTML + MD
repo-radar note <url> -c INCORPORATE \      # Add notes
  -t "my-project" -n "evaluate in Q3"
repo-radar tag <url> security,cli,rust      # Add tags
repo-radar status                           # DB stats + API rate limit
```

## Classifications

| | Class | Meaning |
|--|-------|---------|
| 🟢 | **INTERESTING** | High potential, active, coherent docs |
| 🟡 | **INCORPORATE** | Contains something portable to your stack |
| 🔵 | **WATCH** | Promising but immature — monitor |
| ⚪ | **REDUNDANT** | Duplicates existing functionality |
| 🔴 | **DISCARD** | Abandoned, low quality, misleading |

## Scores

Each repo gets 5 scores (0–100) computed locally:

| Score | Weight | What it measures |
|-------|--------|------------------|
| Documentation | 20% | README quality, CHANGELOG, docs/, examples/ |
| Code/Structure | 30% | Tests, CI/CD, Docker, package manager |
| Coherence | 20% | README ↔ actual code consistency |
| Maturity | 30% | Stars, activity, forks, releases, contributors |

The **LLM** receives all scores + metadata + README excerpt and returns the final verdict.

## CI/CD Automation

The included GitHub Actions workflow (`.github/workflows/check-repos.yml`) runs every Monday at 9am UTC, re-checks all repos, and commits updated reports automatically.

Set the following secrets in your repo:
- `ANTHROPIC_API_KEY` (or `GEMINI_API_KEY` / `OPENAI_API_KEY`)
- `LLM_PROVIDER` (optional, defaults to `claude`)

## License

MIT — free to use, modify and distribute.
