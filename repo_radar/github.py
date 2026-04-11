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


def get_repo_metadata(url: str, token: Optional[str] = None) -> Optional[dict]:
    slug = _parse_slug(url)
    if not slug:
        return None

    api_url = f"{BASE_URL}/repos/{slug}"
    repo = _get(api_url, token)
    if not repo:
        return None

    langs_raw = _get(f"{api_url}/languages", token) or {}
    languages = ", ".join(langs_raw.keys()) if langs_raw else "unknown"

    commits = _get(f"{api_url}/commits?per_page=1", token) or []
    last_commit_sha = commits[0]["sha"] if commits else ""
    last_commit_date = commits[0]["commit"]["author"]["date"] if commits else ""

    releases = _get(f"{api_url}/releases?per_page=5", token) or []
    contribs = _get(f"{api_url}/contributors?per_page=30&anon=false", token) or []

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
        "release_count": len(releases),
        "contributor_count": len(contribs),
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
