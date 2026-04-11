"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

VALID_CLASSES = {"INTERESTING", "INCORPORATE", "WATCH", "REDUNDANT", "DISCARD"}

PROMPT_TEMPLATE = """\
You are an experienced software architect evaluating whether a GitHub repository is worth
incorporating, monitoring, or discarding.

## Repository: {full_name}
Description: {description}
Language: {primary_language} | Others: {all_languages}
Stars: {stars} | Forks: {forks} | Open issues: {open_issues}
Contributors: {contributor_count} | Releases: {release_count}
Topics: {topics}
License: {license}
Archived: {archived} | Fork: {fork}
Last commit: {last_commit_date}

## Heuristic scores (0-100)
Documentation      : {doc_score}  → {doc_notes}
Code/structure     : {code_score}  → {code_notes}
README↔code coherence: {coherence_score} → {coherence_notes}
Maturity           : {maturity_score} → {maturity_notes}

## README snippet
{readme_snippet}

## Available classifications
INTERESTING — High potential, mature, coherent documentation. Worth exploring further.
INCORPORATE — Contains something concrete to port/use in our stack now.
WATCH       — Promising but immature or incomplete. Monitor its evolution.
REDUNDANT   — Duplicates something already catalogued or available internally.
DISCARD     — Abandoned, low quality, misleading docs, or irrelevant.

Respond ONLY with valid JSON, no markdown, in this exact format:
{{"classification":"WATCH","rationale":"Concise explanation in Portuguese (2-3 sentences)."}}
"""


class LLMProvider(ABC):
    @abstractmethod
    def _call(self, prompt: str) -> Optional[str]:
        """Send prompt to LLM and return raw text response."""

    def get_verdict(self, meta: dict, scores: dict, readme_snippet: str) -> Optional[dict]:
        import json, re

        def _notes(lst: list, n: int = 6) -> str:
            return "; ".join(lst[:n]) if lst else ""

        prompt = PROMPT_TEMPLATE.format(
            full_name=meta.get("full_name", ""),
            description=meta.get("description", ""),
            primary_language=meta.get("primary_language", ""),
            all_languages=meta.get("all_languages", ""),
            stars=meta.get("stars", 0),
            forks=meta.get("forks", 0),
            open_issues=meta.get("open_issues", 0),
            contributor_count=meta.get("contributor_count", 0),
            release_count=meta.get("release_count", 0),
            topics=meta.get("topics", ""),
            license=meta.get("license", "none"),
            archived=meta.get("archived", False),
            fork=meta.get("fork", False),
            last_commit_date=meta.get("last_commit_date", ""),
            doc_score=scores.get("doc", {}).get("score", 0),
            doc_notes=_notes(scores.get("doc", {}).get("notes", [])),
            code_score=scores.get("code", {}).get("score", 0),
            code_notes=_notes(scores.get("code", {}).get("notes", [])),
            coherence_score=scores.get("coherence", {}).get("score", 0),
            coherence_notes=_notes(scores.get("coherence", {}).get("notes", []), 4),
            maturity_score=scores.get("maturity", {}).get("score", 0),
            maturity_notes=_notes(scores.get("maturity", {}).get("notes", [])),
            readme_snippet=readme_snippet[:3000] if readme_snippet else "(not available)",
        )

        raw = self._call(prompt)
        if not raw:
            return None

        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw).strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\{.*?"classification".*?\}', raw, re.S)
            if not m:
                return None
            try:
                parsed = json.loads(m.group())
            except json.JSONDecodeError:
                return None

        if parsed.get("classification") not in VALID_CLASSES:
            return None

        return {"classification": parsed["classification"], "rationale": parsed.get("rationale", "")}
