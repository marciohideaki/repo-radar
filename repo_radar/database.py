"""SQLite persistence layer — uses Python stdlib sqlite3, no external binary needed."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    url               TEXT UNIQUE NOT NULL,
    owner             TEXT,
    name              TEXT,
    full_name         TEXT,
    description       TEXT,
    primary_language  TEXT,
    all_languages     TEXT,
    stars             INTEGER DEFAULT 0,
    forks             INTEGER DEFAULT 0,
    open_issues       INTEGER DEFAULT 0,
    license           TEXT,
    topics            TEXT,
    archived          INTEGER DEFAULT 0,
    fork              INTEGER DEFAULT 0,
    release_count     INTEGER DEFAULT 0,
    contributor_count INTEGER DEFAULT 0,
    interest_score    INTEGER DEFAULT 0,
    maturity_score    INTEGER DEFAULT 0,
    doc_score         INTEGER DEFAULT 0,
    code_score        INTEGER DEFAULT 0,
    coherence_score   INTEGER DEFAULT 0,
    classification    TEXT DEFAULT 'WATCH',
    llm_rationale     TEXT,
    llm_provider      TEXT,
    incorporate_target TEXT,
    notes             TEXT,
    last_commit_sha   TEXT,
    last_commit_date  TEXT,
    first_seen_at     TEXT NOT NULL,
    last_checked_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id           INTEGER NOT NULL REFERENCES repositories(id),
    checked_at        TEXT NOT NULL,
    classification    TEXT,
    interest_score    INTEGER,
    maturity_score    INTEGER,
    doc_score         INTEGER,
    code_score        INTEGER,
    coherence_score   INTEGER,
    stars_at_check    INTEGER,
    commit_sha        TEXT,
    stars_delta       INTEGER DEFAULT 0,
    commit_delta      INTEGER DEFAULT 0,
    delta_summary     TEXT,
    new_features      TEXT
);

CREATE TABLE IF NOT EXISTS features (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id          INTEGER NOT NULL REFERENCES repositories(id),
    feature_name     TEXT NOT NULL,
    source           TEXT,
    portability_note TEXT,
    UNIQUE(repo_id, feature_name)
);

CREATE TABLE IF NOT EXISTS tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL REFERENCES repositories(id),
    tag     TEXT NOT NULL,
    UNIQUE(repo_id, tag)
);
"""


@contextmanager
def _conn(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _conn(db_path) as con:
        con.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def upsert_repo(db_path: Path, data: dict) -> int:
    now = _now()
    with _conn(db_path) as con:
        cur = con.execute("SELECT id, stars, last_commit_sha, first_seen_at FROM repositories WHERE url = ?", (data["url"],))
        existing = cur.fetchone()

        if existing:
            stars_delta = data.get("stars", 0) - (existing["stars"] or 0)
            commit_delta = 1 if data.get("last_commit_sha") != existing["last_commit_sha"] else 0
            con.execute("""
                UPDATE repositories SET
                    owner=?, name=?, full_name=?, description=?, primary_language=?,
                    all_languages=?, stars=?, forks=?, open_issues=?, license=?, topics=?,
                    archived=?, fork=?, release_count=?, contributor_count=?,
                    interest_score=?, maturity_score=?, doc_score=?, code_score=?, coherence_score=?,
                    classification=?, llm_rationale=?, llm_provider=?,
                    last_commit_sha=?, last_commit_date=?, last_checked_at=?
                WHERE url=?
            """, (
                data.get("owner"), data.get("name"), data.get("full_name"),
                data.get("description"), data.get("primary_language"), data.get("all_languages"),
                data.get("stars", 0), data.get("forks", 0), data.get("open_issues", 0),
                data.get("license"), data.get("topics"),
                int(data.get("archived", False)), int(data.get("fork", False)),
                data.get("release_count", 0), data.get("contributor_count", 0),
                data.get("interest_score", 0), data.get("maturity_score", 0),
                data.get("doc_score", 0), data.get("code_score", 0), data.get("coherence_score", 0),
                data.get("classification", "WATCH"), data.get("llm_rationale"), data.get("llm_provider"),
                data.get("last_commit_sha"), data.get("last_commit_date"), now,
                data["url"],
            ))
            repo_id = existing["id"]
            _insert_check(con, repo_id, data, now, stars_delta, commit_delta)
        else:
            cur = con.execute("""
                INSERT INTO repositories (
                    url, owner, name, full_name, description, primary_language, all_languages,
                    stars, forks, open_issues, license, topics, archived, fork,
                    release_count, contributor_count,
                    interest_score, maturity_score, doc_score, code_score, coherence_score,
                    classification, llm_rationale, llm_provider,
                    last_commit_sha, last_commit_date, first_seen_at, last_checked_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data["url"], data.get("owner"), data.get("name"), data.get("full_name"),
                data.get("description"), data.get("primary_language"), data.get("all_languages"),
                data.get("stars", 0), data.get("forks", 0), data.get("open_issues", 0),
                data.get("license"), data.get("topics"),
                int(data.get("archived", False)), int(data.get("fork", False)),
                data.get("release_count", 0), data.get("contributor_count", 0),
                data.get("interest_score", 0), data.get("maturity_score", 0),
                data.get("doc_score", 0), data.get("code_score", 0), data.get("coherence_score", 0),
                data.get("classification", "WATCH"), data.get("llm_rationale"), data.get("llm_provider"),
                data.get("last_commit_sha"), data.get("last_commit_date"), now, now,
            ))
            repo_id = cur.lastrowid
            _insert_check(con, repo_id, data, now, 0, 0)

    return repo_id


def _insert_check(con: sqlite3.Connection, repo_id: int, data: dict, now: str, stars_delta: int, commit_delta: int):
    deltas = []
    if stars_delta > 0: deltas.append(f"+{stars_delta} stars")
    if commit_delta:    deltas.append("new commits")
    delta_summary = ", ".join(deltas) if deltas else "no changes"

    con.execute("""
        INSERT INTO checks (repo_id, checked_at, classification, interest_score,
            maturity_score, doc_score, code_score, coherence_score,
            stars_at_check, commit_sha, stars_delta, commit_delta, delta_summary)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        repo_id, now, data.get("classification"), data.get("interest_score", 0),
        data.get("maturity_score", 0), data.get("doc_score", 0),
        data.get("code_score", 0), data.get("coherence_score", 0),
        data.get("stars", 0), data.get("last_commit_sha"),
        stars_delta, commit_delta, delta_summary,
    ))


def upsert_features(db_path: Path, repo_id: int, features: list[dict]) -> None:
    with _conn(db_path) as con:
        for f in features:
            con.execute("""
                INSERT OR IGNORE INTO features (repo_id, feature_name, source, portability_note)
                VALUES (?,?,?,?)
            """, (repo_id, f.get("name", ""), f.get("source", ""), f.get("portability_note", "")))


def add_tags(db_path: Path, repo_id: int, tags: list[str]) -> None:
    with _conn(db_path) as con:
        for tag in tags:
            con.execute("INSERT OR IGNORE INTO tags (repo_id, tag) VALUES (?,?)", (repo_id, tag.strip()))


def get_all_repos(db_path: Path) -> list[dict]:
    with _conn(db_path) as con:
        rows = con.execute("SELECT * FROM repositories ORDER BY interest_score DESC").fetchall()
        return [dict(r) for r in rows]


def get_repo_by_name(db_path: Path, name: str) -> Optional[dict]:
    with _conn(db_path) as con:
        row = con.execute("SELECT * FROM repositories WHERE name=? OR url=?", (name, name)).fetchone()
        return dict(row) if row else None


def get_repo_checks(db_path: Path, repo_id: int) -> list[dict]:
    with _conn(db_path) as con:
        rows = con.execute("SELECT * FROM checks WHERE repo_id=? ORDER BY checked_at DESC", (repo_id,)).fetchall()
        return [dict(r) for r in rows]


def get_repo_features(db_path: Path, repo_id: int) -> list[dict]:
    with _conn(db_path) as con:
        rows = con.execute("SELECT * FROM features WHERE repo_id=?", (repo_id,)).fetchall()
        return [dict(r) for r in rows]


def get_repo_tags(db_path: Path, repo_id: int) -> list[str]:
    with _conn(db_path) as con:
        rows = con.execute("SELECT tag FROM tags WHERE repo_id=?", (repo_id,)).fetchall()
        return [r["tag"] for r in rows]


def update_repo_notes(db_path: Path, url: str, classification: Optional[str] = None,
                      incorporate_target: Optional[str] = None, notes: Optional[str] = None) -> bool:
    with _conn(db_path) as con:
        row = con.execute("SELECT id FROM repositories WHERE url=? OR name=?", (url, url)).fetchone()
        if not row:
            return False
        if classification:
            con.execute("UPDATE repositories SET classification=? WHERE id=?", (classification, row["id"]))
        if incorporate_target:
            con.execute("UPDATE repositories SET incorporate_target=? WHERE id=?", (incorporate_target, row["id"]))
        if notes:
            con.execute("UPDATE repositories SET notes=? WHERE id=?", (notes, row["id"]))
        return True


def remove_repo(db_path: Path, url: str) -> bool:
    with _conn(db_path) as con:
        row = con.execute("SELECT id FROM repositories WHERE url=? OR name=?", (url, url)).fetchone()
        if not row:
            return False
        con.execute("UPDATE repositories SET archived=2 WHERE id=?", (row["id"],))
        return True
