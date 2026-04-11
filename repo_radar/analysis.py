"""Heuristic analysis engine — 100% local, no API cost."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────
# DOCUMENTATION SCORE
# ──────────────────────────────────────────────────────────────────
def measure_doc_score(repo_path: Path) -> dict:
    score = 0
    notes = []
    root = Path(repo_path)

    # README (up to 30 pts)
    readme = next((f for f in root.iterdir() if f.is_file() and f.name.upper().startswith("README")), None)
    if readme:
        score += 10
        notes.append("✓ README present")
        content = readme.read_text(errors="ignore")
        if len(content) > 500:  score += 5;  notes.append("✓ README non-trivial (>500 chars)")
        if len(content) > 2000: score += 5;  notes.append("✓ README substantial (>2k chars)")
        if len(content) > 5000: score += 5;  notes.append("✓ README rich (>5k chars)")
        if re.search(r"(?i)(install|getting started|como usar|usage)", content):
            score += 5
            notes.append("✓ Install/usage instructions")
    else:
        notes.append("✗ No README")

    # CHANGELOG (10 pts)
    changelog = next((f for f in root.rglob("CHANGE*") if f.is_file()), None)
    if changelog: score += 10; notes.append("✓ CHANGELOG present")
    else: notes.append("✗ No CHANGELOG")

    # docs/ folder (10 pts)
    docs_dir = next((d for d in root.iterdir() if d.is_dir() and d.name.lower() in ("docs", "doc", "wiki", "documentation")), None)
    if docs_dir: score += 10; notes.append(f"✓ Docs folder ({docs_dir.name})")
    else: notes.append("✗ No docs/ folder")

    # examples/ folder (10 pts)
    ex_dir = next((d for d in root.iterdir() if d.is_dir() and d.name.lower() in ("examples", "example", "samples", "demo", "demos", "tutorials")), None)
    if ex_dir: score += 10; notes.append(f"✓ Examples ({ex_dir.name})")
    else: notes.append("✗ No examples")

    # LICENSE (10 pts)
    lic = next((f for f in root.iterdir() if f.is_file() and f.name.upper().startswith("LICENSE")), None)
    if lic: score += 10; notes.append("✓ LICENSE present")
    else: notes.append("✗ No LICENSE")

    # CONTRIBUTING / CODE_OF_CONDUCT (10 pts)
    contrib = next((f for f in root.iterdir() if f.is_file() and f.name.upper().startswith(("CONTRIBUTING", "CODE_OF_CONDUCT"))), None)
    if contrib: score += 10; notes.append("✓ CONTRIBUTING/CoC present")

    # .github/ (5 pts)
    if (root / ".github").is_dir(): score += 5; notes.append("✓ .github/ present")

    # API docs (5 pts)
    api_doc = next((f for f in root.rglob("*") if f.is_file() and re.search(r"(swagger|openapi|api[-_]?doc)", f.name, re.I)), None)
    if api_doc: score += 5; notes.append("✓ API docs detected")

    return {"score": min(score, 100), "notes": notes}


# ──────────────────────────────────────────────────────────────────
# CODE / STRUCTURE SCORE
# ──────────────────────────────────────────────────────────────────
def measure_code_score(repo_path: Path) -> dict:
    score = 0
    notes = []
    features = []
    root = Path(repo_path)

    # Tests (20 pts)
    test_dir = next((d for d in root.iterdir() if d.is_dir() and d.name.lower() in ("tests", "test", "spec", "__tests__", "e2e", "integration")), None)
    if test_dir:
        score += 15
        notes.append(f"✓ Test directory ({test_dir.name})")
        test_files = list(test_dir.rglob("*.py")) + list(test_dir.rglob("*.ts")) + list(test_dir.rglob("*.js"))
        test_files = [f for f in test_files if re.search(r"(test_|_test\.|spec\.)", f.name)]
        if len(test_files) > 5:
            score += 5
            notes.append(f"✓ Multiple test files ({len(test_files)})")
    else:
        notes.append("✗ No test directory")

    # CI/CD (15 pts)
    ci_found = False
    if (root / ".github" / "workflows").is_dir(): score += 15; ci_found = True; notes.append("✓ GitHub Actions")
    elif (root / ".circleci").is_dir(): score += 15; ci_found = True; notes.append("✓ CircleCI")
    elif (root / ".travis.yml").exists(): score += 15; ci_found = True; notes.append("✓ Travis CI")
    elif (root / "Jenkinsfile").exists(): score += 15; ci_found = True; notes.append("✓ Jenkins")
    elif list(root.glob("*.gitlab-ci.yml")): score += 15; ci_found = True; notes.append("✓ GitLab CI")
    if not ci_found: notes.append("✗ No CI/CD detected")

    # Docker (10 pts)
    if (root / "Dockerfile").exists(): score += 7; notes.append("✓ Dockerfile"); features.append("Docker")
    if list(root.glob("docker-compose*")): score += 3; notes.append("✓ docker-compose"); features.append("Docker Compose")

    # Package manager (10 pts)
    pkg_map = {
        "package.json": "Node.js/npm",
        "requirements.txt": "Python/pip",
        "pyproject.toml": "Python/pyproject",
        "Cargo.toml": "Rust/Cargo",
        "go.mod": "Go modules",
        "pom.xml": "Java/Maven",
        "build.gradle": "Java/Gradle",
        "Gemfile": "Ruby/Bundler",
        "composer.json": "PHP/Composer",
        "mix.exs": "Elixir/Mix",
    }
    for fname, label in pkg_map.items():
        if (root / fname).exists():
            score += 10
            notes.append(f"✓ {label} ({fname})")
            features.append(label)
            break
    else:
        if list(root.glob("*.csproj")): score += 10; notes.append("✓ .NET (.csproj)")

    # Organized structure (10 pts)
    src_dir = next((d for d in root.iterdir() if d.is_dir() and d.name.lower() in ("src", "lib", "cmd", "app", "pkg", "core")), None)
    if src_dir: score += 10; notes.append(f"✓ Organized structure ({src_dir.name})")

    # Linting config (5 pts)
    lint_patterns = [".eslintrc*", ".prettierrc*", ".editorconfig", ".rubocop.yml", "rustfmt.toml", "ruff.toml", ".flake8"]
    for pat in lint_patterns:
        if list(root.glob(pat)):
            score += 5
            notes.append(f"✓ Lint/format config")
            break

    # Total code files
    code_exts = (".py", ".js", ".ts", ".go", ".rs", ".java", ".cs", ".rb", ".php", ".cpp", ".c", ".ex", ".exs")
    total_code = sum(1 for f in root.rglob("*") if f.is_file() and f.suffix in code_exts)
    notes.append(f"📁 Code files: {total_code}")

    return {"score": min(score, 100), "notes": notes, "features": features, "code_files": total_code}


# ──────────────────────────────────────────────────────────────────
# README ↔ CODE COHERENCE
# ──────────────────────────────────────────────────────────────────
def measure_coherence_score(repo_path: Path) -> dict:
    root = Path(repo_path)
    readme = next((f for f in root.iterdir() if f.is_file() and f.name.upper().startswith("README")), None)
    if not readme:
        return {"score": 30, "notes": ["No README to evaluate coherence"]}

    content = readme.read_text(errors="ignore")
    score = 50
    notes = []

    checks = [
        (r"(?i)(docker|container)",     ["Dockerfile"],                                         10, "Docker mentioned → Dockerfile"),
        (r"(?i)(test|spec)",            ["tests", "test", "spec", "__tests__"],                  10, "Tests mentioned → test dir"),
        (r"(?i)(install|pip install|npm install|cargo build)", ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "pyproject.toml"], 10, "Build instructions → manifest"),
        (r"(?i)(cli|command.line|terminal)", ["cmd", "bin", "cli"],                              5,  "CLI mentioned → cmd/bin"),
        (r"(?i)(api|rest|endpoint|swagger)", ["api", "routes", "swagger", "openapi"],            5,  "API mentioned → api folder"),
        (r"(?i)(configur|config\.yaml|config\.json|\.env)", ["config", ".env.example"],        5,  "Config mentioned → config files"),
        (r"(?i)(database|postgres|mysql|sqlite|mongodb)", ["migrations", "db", "database", "models"], 5, "DB mentioned → models/migrations"),
        (r"(?i)(ci|pipeline|github.actions|travis)", [".github/workflows", ".circleci", ".travis.yml"], 5, "CI/CD mentioned → CI config"),
    ]

    for pattern, paths, pts, label in checks:
        if re.search(pattern, content):
            found = any((root / p).exists() for p in paths)
            if found:
                score += pts
                notes.append(f"✓ {label}")
            else:
                score -= pts // 2
                notes.append(f"⚠ {label} — not found in code")

    return {"score": max(0, min(score, 100)), "notes": notes}


# ──────────────────────────────────────────────────────────────────
# MATURITY SCORE (based on GitHub metadata)
# ──────────────────────────────────────────────────────────────────
def measure_maturity_score(meta: dict) -> dict:
    score = 0
    notes = []
    stars = meta.get("stars", 0)

    if stars >= 5000:  score += 25; notes.append(f"⭐ Stars: {stars} (excellent)")
    elif stars >= 500: score += 18; notes.append(f"⭐ Stars: {stars} (good)")
    elif stars >= 50:  score += 10; notes.append(f"⭐ Stars: {stars} (moderate)")
    elif stars >= 5:   score += 5;  notes.append(f"⭐ Stars: {stars} (low)")
    else:                           notes.append(f"⭐ Stars: {stars} (very low)")

    pushed_at = meta.get("pushed_at", "")
    if pushed_at:
        try:
            dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            days = (datetime.now(tz=timezone.utc) - dt).days
            if days <= 30:   score += 20; notes.append(f"🕐 Active (pushed {days}d ago)")
            elif days <= 90:  score += 15; notes.append(f"🕐 Recent (pushed {days}d ago)")
            elif days <= 365: score += 8;  notes.append(f"🕐 Moderate (pushed {days}d ago)")
            elif days <= 730: score += 3;  notes.append(f"⚠ Slow (pushed {days}d ago)")
            else:                          notes.append(f"🔴 Inactive (pushed {days}d ago)")
        except ValueError:
            pass

    forks = meta.get("forks", 0)
    if forks >= 500: score += 15; notes.append(f"🍴 Forks: {forks} (heavily used)")
    elif forks >= 50: score += 10; notes.append(f"🍴 Forks: {forks}")
    elif forks >= 5:  score += 5;  notes.append(f"🍴 Forks: {forks}")

    releases = meta.get("release_count", 0)
    if releases >= 5:  score += 15; notes.append(f"📦 Releases: {releases} (versioned)")
    elif releases >= 1: score += 8; notes.append(f"📦 Releases: {releases}")
    else:                           notes.append("📦 No releases")

    contribs = meta.get("contributor_count", 0)
    if contribs >= 20: score += 15; notes.append(f"👥 Contributors: {contribs} (community)")
    elif contribs >= 3: score += 8; notes.append(f"👥 Contributors: {contribs}")
    else:                           notes.append(f"👥 Contributors: {contribs} (solo/small)")

    if meta.get("archived"): score = int(score * 0.3); notes.append("🔴 REPO ARCHIVED")
    if meta.get("fork"):     score -= 10;              notes.append("⚠ Fork (not original project)")

    return {"score": max(0, min(score, 100)), "notes": notes}


# ──────────────────────────────────────────────────────────────────
# SCORING HELPERS
# ──────────────────────────────────────────────────────────────────
def get_interest_score(doc: int, code: int, coherence: int, maturity: int) -> int:
    return int(doc * 0.2 + code * 0.3 + coherence * 0.2 + maturity * 0.3)


def get_classification(interest: int, maturity: int, doc: int, meta: dict) -> str:
    if meta.get("archived"):
        return "DISCARD"
    avg = (interest + maturity + doc) / 3
    if avg >= 65 and maturity >= 50:
        return "INTERESTING"
    if avg >= 50 or maturity >= 40:
        return "WATCH"
    if avg < 30 and maturity < 25:
        return "DISCARD"
    return "WATCH"


def get_main_features(repo_path: Path, meta: dict) -> list[dict]:
    root = Path(repo_path)
    features = []

    for lang in (meta.get("all_languages") or "").split(", "):
        if lang and lang != "unknown":
            features.append({"name": f"Language: {lang}", "source": "github_api", "portability_note": ""})

    for topic in (meta.get("topics") or "").split(", "):
        if topic:
            features.append({"name": f"Topic: {topic}", "source": "github_topics", "portability_note": ""})

    feature_map = {
        "Dockerfile":           "Docker containerization",
        "docker-compose.yml":   "Docker Compose orchestration",
        ".github/workflows":    "GitHub Actions CI/CD",
        "migrations":           "DB migration management",
        "Makefile":             "Build via Makefile",
        ".env.example":         "Env-var configuration",
        "helm":                 "Kubernetes (Helm) deployment",
        "terraform":            "Infrastructure as Code (Terraform)",
        "graphql":              "GraphQL API",
        "proto":                "Protocol Buffers / gRPC",
    }
    for path_pattern, label in feature_map.items():
        if (root / path_pattern).exists() or list(root.rglob(path_pattern)):
            features.append({"name": label, "source": "filesystem", "portability_note": "Check stack compatibility"})

    return features
