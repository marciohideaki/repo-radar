"""CLI entry point — all commands."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console

console = Console()


def _setup() -> tuple[Path, Path, Path]:
    # Load .env from RADAR_HOME, the package root, or cwd — whichever exists first
    pkg_root = Path(__file__).parent.parent
    for candidate in [pkg_root / ".env", Path.cwd() / ".env"]:
        if candidate.exists():
            load_dotenv(candidate)
            break
    else:
        load_dotenv()
    radar_home = Path(os.getenv("RADAR_HOME") or pkg_root)
    data_dir = radar_home / "data"
    repos_dir = radar_home / "repos"
    data_dir.mkdir(parents=True, exist_ok=True)
    repos_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, repos_dir, data_dir / "radar.db"


def _clone_or_pull(clone_url: str, repo_name: str, repos_dir: Path, force: bool = False) -> Optional[Path]:
    dest = repos_dir / repo_name
    if dest.exists() and not force:
        console.print(f"  🔄 Updating {repo_name}...")
        subprocess.run(["git", "-C", str(dest), "pull", "--quiet"], check=False)
    else:
        if dest.exists():
            import shutil
            shutil.rmtree(dest)
        console.print(f"  📥 Cloning {repo_name}...")
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", clone_url, str(dest)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]  ✗ Clone failed: {result.stderr.strip()}[/red]")
            return None
    return dest


def _find_existing_local(repo_name: str, repos_dir: Path) -> Optional[Path]:
    """Check if repo is already cloned locally — in repos_dir or in parent (e.g. /opt/references)."""
    candidate = repos_dir / repo_name
    if candidate.is_dir() and (candidate / ".git").is_dir():
        return candidate
    # Check one level up (e.g. /opt/references/<name>)
    parent = repos_dir.parent
    candidate2 = parent / repo_name
    if candidate2.is_dir() and (candidate2 / ".git").is_dir():
        return candidate2
    return None


def _run_analysis(url: str, repos_dir: Path, force: bool = False) -> Optional[dict]:
    from . import github, analysis, llm as llm_mod

    console.print(f"\n[cyan]🔍 Analysing[/cyan] {url}")

    # Check for existing local clone before API call (to pass as local_path)
    import re
    slug_match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    repo_name_hint = slug_match.group(1).split("/")[1] if slug_match else None
    existing_path = _find_existing_local(repo_name_hint, repos_dir) if repo_name_hint else None

    # 1 API call only — enrich from local clone when available
    meta = github.get_repo_metadata(url, local_path=str(existing_path) if existing_path else None)
    if not meta:
        console.print("[red]  ✗ Could not fetch metadata from GitHub.[/red]")
        return None

    # Clone or pull — reuse existing local clone if already found
    if existing_path and not force:
        console.print(f"  🔄 Updating {meta['name']} (existing clone)...")
        subprocess.run(["git", "-C", str(existing_path), "pull", "--quiet"], check=False)
        repo_path = existing_path
    else:
        repo_path = _clone_or_pull(meta["clone_url"], meta["name"], repos_dir, force)
    if not repo_path:
        return None

    console.print("  📊 Running heuristic analysis...")
    doc     = analysis.measure_doc_score(repo_path)
    code    = analysis.measure_code_score(repo_path)
    coh     = analysis.measure_coherence_score(repo_path)
    mat     = analysis.measure_maturity_score(meta)
    interest = analysis.get_interest_score(doc["score"], code["score"], coh["score"], mat["score"])
    classification = analysis.get_classification(interest, mat["score"], doc["score"], meta)
    features = analysis.get_main_features(repo_path, meta)

    llm_rationale = None
    llm_provider_name = None
    provider = llm_mod.get_provider()
    if provider:
        console.print(f"  🤖 Asking LLM for verdict ({os.getenv('LLM_PROVIDER', 'claude')})...")
        readme_file = next((f for f in repo_path.iterdir() if f.is_file() and f.name.upper().startswith("README")), None)
        readme_snippet = readme_file.read_text(errors="ignore")[:3000] if readme_file else ""
        scores = {"doc": doc, "code": code, "coherence": coh, "maturity": mat}
        verdict = provider.get_verdict(meta, scores, readme_snippet)
        if verdict:
            classification = verdict["classification"]
            llm_rationale = verdict["rationale"]
            llm_provider_name = os.getenv("LLM_PROVIDER", "claude")
        else:
            console.print("  [dim]⚠ LLM unavailable, using heuristic classification.[/dim]")
    else:
        console.print("  [dim]⚠ No LLM configured (LLM_PROVIDER not set), using heuristic.[/dim]")

    return {
        "url": url,
        **meta,
        "doc_score": doc["score"],
        "code_score": code["score"],
        "coherence_score": coh["score"],
        "maturity_score": mat["score"],
        "interest_score": interest,
        "classification": classification,
        "llm_rationale": llm_rationale,
        "llm_provider": llm_provider_name,
        "_features": features,
    }


@click.group()
def main():
    """\U0001f52d Repo Radar — GitHub repository intelligence system."""


@main.command()
@click.argument("url")
@click.option("--force", is_flag=True, help="Re-analyse even if already in radar")
def add(url: str, force: bool):
    """Clone and analyse a new repository."""
    from . import database
    data_dir, repos_dir, db_path = _setup()
    database.init_db(db_path)

    data = _run_analysis(url, repos_dir, force)
    if not data:
        sys.exit(1)

    features = data.pop("_features", [])
    repo_id = database.upsert_repo(db_path, data)
    database.upsert_features(db_path, repo_id, features)

    from . import report as rpt
    cls = data["classification"]
    color = rpt.CLASS_COLOR.get(cls, "white")
    console.print(f"\n[{color}]{rpt.CLASS_EMOJI.get(cls,'')} {cls}[/{color}]  "
                  f"interest={data['interest_score']}  "
                  f"doc={data['doc_score']}  code={data['code_score']}  "
                  f"maturity={data['maturity_score']}")
    if data.get("llm_rationale"):
        console.print(f"[dim]{data['llm_rationale']}[/dim]")
    console.print(f"[green]✓[/green] Saved to radar.db")


@main.command()
@click.argument("target")
def check(target: str):
    """Re-check one repo (URL or name) or all."""
    from . import database
    data_dir, repos_dir, db_path = _setup()
    database.init_db(db_path)

    if target.lower() == "all":
        repos = database.get_all_repos(db_path)
        if not repos:
            console.print("[dim]No repos in radar.[/dim]")
            return
        console.print(f"Checking {len(repos)} repos...")
        for r in repos:
            _do_check(r["url"], repos_dir, db_path)
    else:
        _do_check(target, repos_dir, db_path)


def _do_check(url: str, repos_dir: Path, db_path: Path):
    from . import database
    data = _run_analysis(url, repos_dir)
    if not data:
        return
    features = data.pop("_features", [])
    repo_id = database.upsert_repo(db_path, data)
    database.upsert_features(db_path, repo_id, features)
    console.print(f"  [green]✓[/green] {data.get('name',url)} → {data['classification']} (score {data['interest_score']})")


@main.command(name="list")
@click.option("--classification", "-c", default=None, help="Filter by classification")
def list_repos(classification: Optional[str]):
    """List all monitored repositories."""
    from . import database, report as rpt
    _, _, db_path = _setup()
    database.init_db(db_path)
    repos = database.get_all_repos(db_path)
    if classification:
        repos = [r for r in repos if r.get("classification", "").upper() == classification.upper()]
    rpt.print_list(repos)


@main.command()
@click.argument("name")
def show(name: str):
    """Show full details of a repository."""
    from . import database, report as rpt
    _, _, db_path = _setup()
    database.init_db(db_path)
    repo = database.get_repo_by_name(db_path, name)
    if not repo:
        console.print(f"[red]Repo '{name}' not found in radar.[/red]")
        sys.exit(1)
    checks = database.get_repo_checks(db_path, repo["id"])
    features = database.get_repo_features(db_path, repo["id"])
    tags = database.get_repo_tags(db_path, repo["id"])
    rpt.print_repo_detail(repo, checks, features, tags)


@main.command()
@click.option("--format", "fmt", type=click.Choice(["html", "md", "both"]), default="both")
def report(fmt: str):
    """Generate HTML and/or Markdown reports."""
    from . import database, report as rpt
    data_dir, _, db_path = _setup()
    database.init_db(db_path)
    repos = database.get_all_repos(db_path)
    if fmt in ("md", "both"):
        md = rpt.generate_markdown(repos)
        (data_dir / "radar-report.md").write_text(md, encoding="utf-8")
        console.print(f"[green]✓[/green] {data_dir / 'radar-report.md'}")
    if fmt in ("html", "both"):
        html = rpt.generate_html(repos)
        (data_dir / "radar-report.html").write_text(html, encoding="utf-8")
        console.print(f"[green]✓[/green] {data_dir / 'radar-report.html'}")


@main.command()
@click.argument("url")
@click.option("--classification", "-c", default=None)
@click.option("--target", "-t", default=None, help="Incorporate target project")
@click.option("--notes", "-n", default=None)
def note(url: str, classification: Optional[str], target: Optional[str], notes: Optional[str]):
    """Add/edit notes, classification or incorporate target for a repo."""
    from . import database
    _, _, db_path = _setup()
    if not database.update_repo_notes(db_path, url, classification, target, notes):
        console.print(f"[red]Repo '{url}' not found.[/red]")
        sys.exit(1)
    console.print("[green]✓[/green] Updated.")


@main.command()
@click.argument("url")
@click.argument("tags")
def tag(url: str, tags: str):
    """Add tags to a repository (comma-separated)."""
    from . import database
    _, _, db_path = _setup()
    repo = database.get_repo_by_name(db_path, url)
    if not repo:
        console.print(f"[red]Repo '{url}' not found.[/red]")
        sys.exit(1)
    database.add_tags(db_path, repo["id"], tags.split(","))
    console.print("[green]✓[/green] Tags added.")


@main.command()
@click.argument("url")
def remove(url: str):
    """Remove a repository from radar (preserves history)."""
    from . import database
    _, _, db_path = _setup()
    if not database.remove_repo(db_path, url):
        console.print(f"[red]Repo '{url}' not found.[/red]")
        sys.exit(1)
    console.print("[green]✓[/green] Removed (history preserved).")


@main.command()
def status():
    """Show radar database status and GitHub API rate limit."""
    from . import database, github as gh
    _, _, db_path = _setup()
    database.init_db(db_path)
    repos = database.get_all_repos(db_path)
    console.print(f"[bold]Repos in radar:[/bold] {len(repos)}")
    from collections import Counter
    counts = Counter(r.get("classification") for r in repos)
    for cls, n in counts.items():
        console.print(f"  {rpt_badge(cls)}: {n}")
    rl = gh.get_rate_limit_status()
    if rl:
        console.print(f"\n[bold]GitHub API rate limit:[/bold] {rl['remaining']}/{rl['limit']} (resets {rl['reset_at']})")


def rpt_badge(cls):
    from . import report as rpt
    return f"{rpt.CLASS_EMOJI.get(cls,'')} {cls}"
