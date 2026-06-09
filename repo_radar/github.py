"""GitHub API client — fetches repository metadata."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

BASE_URL = "https://api.github.com"
TIMEOUT = 15
MAX_RETRIES = 3


def _headers(token: Optional[str] = None) -> dict:
    h = {"User-Agent": "repo-radar/1.0", "Accept": "application/vnd.github.v3+json"}
    tok = token or os.getenv("GITHUB_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _get(url: str, token: Optional[str] = None) -> Optional[dict | list]:
    headers = _headers(token)
    for attempt in range(MAX_RETRIES):
        try:
            r = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 403):
                wait = 2 ** attempt * 5
                time.sleep(wait)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
        except httpx.RequestError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def _parse_slug(url: str) -> Optional[str]:
    url = url.rstrip("/")
    import re
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def get_repo_metadata(url: str, token: Optional[str] = None, local_path: Optional[str] = None) -> Optional[dict]:
    """Fetch repo metadata using a single GitHub API call.
    Languages, last commit, and contributor count are enriched from the local clone when available.
    """
    slug = _parse_slug(url)
    if not slug:
        return None

    api_url = f"{BASE_URL}/repos/{slug}"
    repo = _get(api_url, token)  # 1 API call only
    if not repo:
        return None

    # Enrich from local clone when available — zero extra API calls
    languages = "unknown"
    last_commit_sha = ""
    last_commit_date = ""
    contributor_count = 0
    release_count = 0

    if local_path:
        import subprocess
        from pathlib import Path
        lp = Path(local_path)
        if lp.is_dir():
            # Languages: count files by extension
            ext_map: dict[str, int] = {}
            for f in lp.rglob("*"):
                if f.is_file() and f.suffix and ".git" not in f.parts:
                    ext_map[f.suffix] = ext_map.get(f.suffix, 0) + 1
            lang_exts = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".go": "Go", ".rs": "Rust", ".java": "Java", ".cs": "C#",
                ".rb": "Ruby", ".php": "PHP", ".cpp": "C++", ".c": "C",
                ".ex": "Elixir", ".exs": "Elixir", ".kt": "Kotlin",
                ".swift": "Swift", ".sh": "Shell", ".ps1": "PowerShell",
            }
            found_langs = sorted(
                {lang_exts[ext] for ext, cnt in ext_map.items() if ext in lang_exts},
                key=lambda l: -ext_map.get({v: k for k, v in lang_exts.items()}.get(l, ""), 0)
            )
            if found_langs:
                languages = ", ".join(found_langs)

            # Last commit from git log
            r = subprocess.run(
                ["git", "-C", str(lp), "log", "-1", "--format=%H %aI"],
                capture_output=True, text=True
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(" ", 1)
                last_commit_sha = parts[0]
                last_commit_date = parts[1] if len(parts) > 1 else ""

            # Contributor count from git shortlog
            r2 = subprocess.run(
                ["git", "-C", str(lp), "shortlog", "-s", "HEAD"],
                capture_output=True, text=True
            )
            if r2.returncode == 0:
                contributor_count = len([l for l in r2.stdout.strip().splitlines() if l.strip()])

            # Release count from tags
            r3 = subprocess.run(
                ["git", "-C", str(lp), "tag", "-l"],
                capture_output=True, text=True
            )
            if r3.returncode == 0:
                release_count = len([t for t in r3.stdout.strip().splitlines() if t.strip()])
    else:
        # Fallback: use what the main API endpoint provides (no extra calls)
        languages = repo.get("language") or "unknown"

    return {
        "owner": repo["owner"]["login"],
        "name": repo["name"],
        "full_name": repo["full_name"],
        "description": repo.get("description") or "",
        "homepage": repo.get("homepage") or "",
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "primary_language": repo.get("language") or "unknown",
        "all_languages": languages,
        "license": (repo.get("license") or {}).get("spdx_id") or "none",
        "default_branch": repo.get("default_branch", "main"),
        "created_at": repo.get("created_at", ""),
        "updated_at": repo.get("updated_at", ""),
        "pushed_at": repo.get("pushed_at", ""),
        "last_commit_sha": last_commit_sha,
        "last_commit_date": last_commit_date,
        "release_count": release_count,
        "contributor_count": contributor_count,
        "has_wiki": repo.get("has_wiki", False),
        "has_pages": repo.get("has_pages", False),
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
        "size": repo.get("size", 0),
        "topics": ", ".join(repo.get("topics") or []),
        "api_url": api_url,
        "html_url": repo.get("html_url", ""),
        "clone_url": repo.get("clone_url", ""),
    }


def get_rate_limit_status(token: Optional[str] = None) -> Optional[dict]:
    data = _get(f"{BASE_URL}/rate_limit", token)
    if not data:
        return None
    rate = data.get("rate", {})
    reset_ts = rate.get("reset", 0)
    reset_dt = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
    return {
        "limit": rate.get("limit", 0),
        "remaining": rate.get("remaining", 0),
        "reset_at": reset_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
