---
name: repo-radar
description: >
  Analyse and classify a GitHub repository, recording the verdict in
  PROJECT_EVALUATIONS.md. Use when asked to evaluate, audit, or decide whether
  to incorporate a GitHub repo.
---

# Repo Radar

Analyse the GitHub repository passed as argument and record the evaluation in
`/opt/references/PROJECT_EVALUATIONS.md`.

## Inputs

- Repository URL (e.g. `https://github.com/owner/repo`)
- `PROJECT_EVALUATIONS.md` — existing evaluations file to append or update

## Steps

### 1. Fetch metadata via GitHub API

Use `curl` or the GitHub MCP to retrieve:
- Stars, forks, open issues, contributors, releases
- Primary language and all languages
- Last push date (to compute activity)
- Topics, license, archived flag, fork flag
- Description and clone URL

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>" \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

### 2. Clone the repository

```bash
git clone --depth=1 <clone_url> /tmp/radar-<repo-name>
```

If the directory already exists, run `git pull` instead.

### 3. Local heuristic scoring (no API cost)

Inspect the cloned content and score each dimension 0–100:

#### Documentation score (weight 20%)
| Signal | Points |
|--------|--------|
| README present | +10 |
| README >500 chars | +5 |
| README >2k chars | +5 |
| README >5k chars | +5 |
| Install/usage instructions | +5 |
| CHANGELOG present | +10 |
| docs/ or wiki/ folder | +10 |
| examples/ or demo/ folder | +10 |
| LICENSE present | +10 |
| CONTRIBUTING or CODE_OF_CONDUCT | +10 |
| .github/ present | +5 |
| API docs / swagger / openapi | +5 |

#### Code/structure score (weight 30%)
| Signal | Points |
|--------|--------|
| Test directory (tests/, spec/, __tests__/) | +15 |
| >5 test files | +5 |
| CI/CD (GitHub Actions, CircleCI, Travis, GitLab CI) | +15 |
| Dockerfile | +7 |
| docker-compose | +3 |
| Package manifest (package.json, requirements.txt, go.mod…) | +10 |
| Organised structure (src/, lib/, cmd/) | +10 |
| Lint/format config | +5 |

#### Coherence score — README ↔ code (weight 20%)
Base score: 50. For each item mentioned in the README:
- exists in code: +pts
- mentioned but missing: −pts/2

Checks: Docker→Dockerfile, tests→test dir, install→manifest,
CLI→cmd/bin, API→api/routes, config→config files, CI→CI config.

#### Maturity score (weight 30%)
| Signal | Points |
|--------|--------|
| Stars ≥50k | +25 |
| Stars ≥500 | +18 |
| Stars ≥50 | +10 |
| Stars ≥5 | +5 |
| Last push ≤30d | +20 |
| Last push ≤90d | +15 |
| Last push ≤365d | +8 |
| Last push ≤730d | +3 |
| Forks ≥500 | +15 |
| Forks ≥50 | +10 |
| Forks ≥5 | +5 |
| Releases ≥5 | +15 |
| Releases ≥1 | +8 |
| Contributors ≥20 | +15 |
| Contributors ≥3 | +8 |
| Archived | score × 0.3 |
| Fork | −10 |

**Interest score** = doc×0.2 + code×0.3 + coherence×0.2 + maturity×0.3

### 4. Verdict

Based on scores and direct inspection of the code and README:

| Status | Criterion |
|--------|----------|
| `adopt` | High potential, mature, coherent docs. Worth adopting now. |
| `partial` | Contains something concrete to port, but not the whole thing. |
| `reject` | Abandoned, low quality, misleading docs, or irrelevant. |

Identify:
- **What To Reuse**: concrete items worth porting with context
- **What To Avoid**: risks, tight coupling, bad practices
- **Risks**: adoption risks
- **Evidence**: specific files/snippets supporting the verdict

### 5. Record in PROJECT_EVALUATIONS.md

Append or update the entry in `/opt/references/PROJECT_EVALUATIONS.md`
using this exact template:

```markdown
## owner/repo

- Local path: `/opt/references/<name>`
- Status: `adopt` | `partial` | `reject`
- Priority: `high` | `medium` | `low`
- Recommended action: <one objective sentence>

#### What To Reuse

- Concrete item with context

#### What To Avoid

- Concrete item with context

#### Risks

- Specific risk

#### Evidence

- `path/to/file`: objective note

#### Notes

- Scores: interest=X doc=X code=X coherence=X maturity=X
- Stars: X | Forks: X | Contributors: X | Releases: X
- Language: X | License: X
- Last push: YYYY-MM-DD
```

If the repo already exists in the file, **update** the existing entry
instead of duplicating it.

## Rules

- Be specific. Cite actual file paths found in the clone.
- If the repo cannot be cloned (private, removed), use API metadata only.
- Always include numeric scores in Notes for traceability.
- Clean up after recording: `rm -rf /tmp/radar-<repo-name>`
