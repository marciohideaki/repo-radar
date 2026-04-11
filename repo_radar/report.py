"""Report generation — terminal (rich), Markdown, and HTML."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

console = Console()

CLASS_COLOR = {
    "INTERESTING": "green",
    "INCORPORATE": "yellow",
    "WATCH":       "blue",
    "REDUNDANT":   "white",
    "DISCARD":     "red",
}
CLASS_EMOJI = {
    "INTERESTING": "🟢",
    "INCORPORATE": "🟡",
    "WATCH":       "🔵",
    "REDUNDANT":   "⚪",
    "DISCARD":     "🔴",
}


def _badge(cls: Optional[str]) -> str:
    c = cls or "WATCH"
    return f"{CLASS_EMOJI.get(c, '')} {c}"


def print_list(repos: list[dict]) -> None:
    if not repos:
        console.print("[dim]No repositories in radar.[/dim]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Repo", style="bold", min_width=25)
    table.add_column("Class", min_width=14)
    table.add_column("Score", justify="right")
    table.add_column("Stars", justify="right")
    table.add_column("Language", min_width=12)
    table.add_column("Last checked", min_width=16)

    for r in repos:
        cls = r.get("classification", "WATCH")
        color = CLASS_COLOR.get(cls, "white")
        table.add_row(
            r.get("name", ""),
            Text(_badge(cls), style=color),
            str(r.get("interest_score", 0)),
            str(r.get("stars", 0)),
            r.get("primary_language") or "-",
            (r.get("last_checked_at") or "")[:16],
        )

    console.print(table)
    console.print(f"[dim]Total: {len(repos)} repos[/dim]")


def print_repo_detail(repo: dict, checks: list[dict], features: list[dict], tags: list[str]) -> None:
    cls = repo.get("classification", "WATCH")
    color = CLASS_COLOR.get(cls, "white")

    lines = [
        f"[bold]URL:[/bold]         {repo.get('html_url') or repo.get('url', '')}",
        f"[bold]Description:[/bold] {repo.get('description') or '-'}",
        f"[bold]Language:[/bold]    {repo.get('all_languages') or '-'}",
        f"[bold]Stars:[/bold]       {repo.get('stars', 0)}  |  [bold]Forks:[/bold] {repo.get('forks', 0)}  |  [bold]Issues:[/bold] {repo.get('open_issues', 0)}",
        f"[bold]License:[/bold]     {repo.get('license') or '-'}  |  [bold]Topics:[/bold] {repo.get('topics') or '-'}",
        f"[bold]Archived:[/bold]    {bool(repo.get('archived'))}  |  [bold]Fork:[/bold] {bool(repo.get('fork'))}",
        "",
        f"[bold]Scores[/bold]  interest={repo.get('interest_score',0)}  doc={repo.get('doc_score',0)}  code={repo.get('code_score',0)}  coherence={repo.get('coherence_score',0)}  maturity={repo.get('maturity_score',0)}",
    ]

    if repo.get("llm_rationale"):
        lines += ["", f"[bold]LLM rationale ({repo.get('llm_provider','?')}):[/bold] {repo['llm_rationale']}"]
    if repo.get("incorporate_target"):
        lines.append(f"[bold]Incorporate target:[/bold] {repo['incorporate_target']}")
    if repo.get("notes"):
        lines.append(f"[bold]Notes:[/bold] {repo['notes']}")
    if tags:
        lines.append(f"[bold]Tags:[/bold] {', '.join(tags)}")

    if checks:
        lines.append("")
        lines.append("[bold]Recent checks:[/bold]")
        for c in checks[:5]:
            lines.append(f"  {c.get('checked_at','')[:16]}  score={c.get('interest_score',0)}  Δstars={c.get('stars_delta',0)}  {c.get('delta_summary','')}")

    if features:
        lines.append("")
        lines.append(f"[bold]Features detected:[/bold] {', '.join(f['feature_name'] for f in features[:10])}")

    console.print(Panel(
        "\n".join(lines),
        title=f"[{color}]{_badge(cls)}  {repo.get('full_name') or repo.get('name', '')}[/{color}]",
        border_style=color,
    ))


def generate_markdown(repos: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    groups: dict[str, list] = {c: [] for c in ["INTERESTING", "INCORPORATE", "WATCH", "REDUNDANT", "DISCARD"]}
    for r in repos:
        cls = r.get("classification", "WATCH")
        groups.setdefault(cls, []).append(r)

    lines = [f"# Repo Radar Report\n\n> Generated: {now}\n"]
    for cls, items in groups.items():
        if not items:
            continue
        lines.append(f"\n## {CLASS_EMOJI.get(cls, '')} {cls} ({len(items)})\n")
        lines.append("| Repo | Score | Stars | Language | Last checked |")
        lines.append("|---|---|---|---|---|")
        for r in items:
            lines.append(
                f"| [{r.get('name','')}]({r.get('html_url','')}) "
                f"| {r.get('interest_score',0)} "
                f"| {r.get('stars',0)} "
                f"| {r.get('primary_language') or '-'} "
                f"| {(r.get('last_checked_at') or '')[:10]} |"
            )
    return "\n".join(lines) + "\n"


def generate_html(repos: list[dict]) -> str:
    import json
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows_html = ""
    for r in repos:
        cls = r.get("classification", "WATCH")
        color_map = {"INTERESTING": "#2d9a46", "INCORPORATE": "#b8860b", "WATCH": "#1a6fb5", "REDUNDANT": "#888", "DISCARD": "#c0392b"}
        color = color_map.get(cls, "#888")
        rows_html += f"""
        <tr data-class="{cls}">
          <td><a href="{r.get('html_url','')}" target="_blank">{r.get('name','')}</a></td>
          <td><span style="color:{color};font-weight:bold">{CLASS_EMOJI.get(cls,'')} {cls}</span></td>
          <td>{r.get('interest_score',0)}</td>
          <td>{r.get('stars',0)}</td>
          <td>{r.get('primary_language') or '-'}</td>
          <td>{r.get('description') or '-'}</td>
          <td>{(r.get('last_checked_at') or '')[:10]}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Repo Radar Report</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:20px}}
  h1{{color:#58a6ff}} .meta{{color:#8b949e;font-size:.85rem;margin-bottom:16px}}
  .filters{{margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap}}
  .filter-btn{{padding:5px 14px;border-radius:20px;border:1px solid #30363d;background:#161b22;color:#e6edf3;cursor:pointer}}
  .filter-btn.active{{border-color:#58a6ff;color:#58a6ff}}
  input[type=search]{{padding:6px 12px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#e6edf3;width:240px}}
  table{{width:100%;border-collapse:collapse;font-size:.9rem}}
  th{{background:#161b22;padding:8px 12px;text-align:left;border-bottom:1px solid #30363d;color:#8b949e}}
  td{{padding:8px 12px;border-bottom:1px solid #21262d}} tr:hover td{{background:#161b22}}
  a{{color:#58a6ff;text-decoration:none}} a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>🔭 Repo Radar</h1>
<div class="meta">Generated: {now} &nbsp;|&nbsp; {len(repos)} repositories</div>
<div class="filters">
  <input type="search" id="search" placeholder="Search repos..." oninput="applyFilters()">
  <button class="filter-btn active" onclick="setClass('ALL',this)">All</button>
  <button class="filter-btn" onclick="setClass('INTERESTING',this)">🟢 Interesting</button>
  <button class="filter-btn" onclick="setClass('INCORPORATE',this)">🟡 Incorporate</button>
  <button class="filter-btn" onclick="setClass('WATCH',this)">🔵 Watch</button>
  <button class="filter-btn" onclick="setClass('REDUNDANT',this)">⚪ Redundant</button>
  <button class="filter-btn" onclick="setClass('DISCARD',this)">🔴 Discard</button>
</div>
<table id="tbl">
<thead><tr><th>Repo</th><th>Class</th><th>Score</th><th>Stars</th><th>Language</th><th>Description</th><th>Checked</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
<script>
  let activeClass='ALL';
  function setClass(c,btn){{activeClass=c;document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');applyFilters();}}
  function applyFilters(){{const q=document.getElementById('search').value.toLowerCase();document.querySelectorAll('#tbl tbody tr').forEach(r=>{{const cls=r.dataset.class;const txt=r.textContent.toLowerCase();r.style.display=((activeClass==='ALL'||cls===activeClass)&&txt.includes(q))?'':'none';}});}}
</script>
</body></html>
"""


def write_reports(data_dir: Path, repos: list[dict]) -> None:
    md = generate_markdown(repos)
    html = generate_html(repos)
    (data_dir / "radar-report.md").write_text(md, encoding="utf-8")
    (data_dir / "radar-report.html").write_text(html, encoding="utf-8")
    console.print(f"[green]✓[/green] Reports written to [bold]{data_dir}[/bold]")
