---
name: repo-radar
description: >
  Analyse and classify a GitHub repository using the repo-radar CLI (SQLite +
  LLM), recording the verdict in PROJECT_EVALUATIONS.md. Use when asked to
  evaluate, audit, or decide whether to incorporate a GitHub repo.
---

# Repo Radar

Analyse the GitHub repository passed as argument using the `repo-radar` CLI,
persisting results in SQLite and recording the evaluation in
`/opt/references/PROJECT_EVALUATIONS.md`.

## Inputs

- Repository URL (e.g. `https://github.com/owner/repo`)

## Steps

### 1. Ensure repo-radar is installed

```bash
which repo-radar || pip install -e /opt/references/repo-radar
```

If `/opt/references/repo-radar` does not exist:
```bash
git clone https://github.com/marciohideaki/repo-radar /opt/references/repo-radar
pip install -e /opt/references/repo-radar
```

### 2. Ensure `.env` is configured

Check for `/opt/references/repo-radar/.env`. If missing, copy from `.env.example`
and set `LLM_PROVIDER` + matching API key for the running agent:

- Codex → `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
- Claude → `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY`
- Gemini → `LLM_PROVIDER=gemini` + `GEMINI_API_KEY`
- Ollama → `LLM_PROVIDER=ollama`

### 3. Run the analysis

```bash
cd /opt/references/repo-radar
repo-radar add "<url>"
```

The CLI will:
- Fetch metadata via GitHub API
- Clone the repository into `repos/`
- Compute heuristic scores (doc, code, coherence, maturity)
- Ask the LLM for the final verdict (classification + rationale)
- Persist everything in SQLite (`data/radar.db`) with append-only history

### 4. Display result

```bash
repo-radar show <repo-name>
```

### 5. Export to PROJECT_EVALUATIONS.md

Using the data returned by the CLI, append or update the entry in
`/opt/references/PROJECT_EVALUATIONS.md`:

```markdown
## owner/repo

- Local path: `/opt/references/<name>`
- Status: `adopt` | `partial` | `reject`
- Priority: `high` | `medium` | `low`
- Recommended action: <one objective sentence>

#### What To Reuse

- Concrete item with context (based on LLM rationale and evidence)

#### What To Avoid

- Concrete item with context

#### Risks

- Specific risk

#### Evidence

- `path/to/file`: objective note

#### Notes

- Scores: interest=X doc=X code=X coherence=X maturity=X
- Stars: X | Forks: X | Contributors: X | Releases: X
- Language: X | License: X | LLM: <provider>
- Last push: YYYY-MM-DD
- radar.db: `/opt/references/repo-radar/data/radar.db`
```

**Classification mapping:**
- `INTERESTING` → `adopt`
- `INCORPORATE` → `partial`
- `WATCH` → `partial` (with monitoring note)
- `REDUNDANT` → `reject`
- `DISCARD` → `reject`

If the repo already exists in the file, **update** the existing entry
instead of duplicating it.

## Rules

- SQLite is the primary source of truth — PROJECT_EVALUATIONS.md is a derived report.
- Use the LLM rationale as the basis for What To Reuse / What To Avoid.
- Cite actual file paths found in the clone for the Evidence section.
- Always include numeric scores in Notes for traceability.
