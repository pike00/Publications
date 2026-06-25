#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "pydantic-settings", "httpx"]
# ///
"""Generate a one-paragraph plain-language summary per entry via the LiteLLM
proxy (default deepseek-v4-pro-cloud) and store it in the metadata ``summary``
field, so the publications page is readable to non-specialists.

These are LLM-drafted and MUST be reviewed: run this on a dedicated branch and
open a PR. Idempotent (skips entries that already have a summary; --force to
regenerate). The summary is appended as a JSON-encoded YAML scalar so the rest
of each metadata.yml is preserved.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import publib


def clean(text: str) -> str:
    """Normalize LLM punctuation to the house style: no em/en dashes, no smart
    quotes. En dashes in numeric ranges become hyphens; other dashes become a
    comma."""
    text = text.strip()
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"'))
    text = re.sub(r"(?<=\d)\s*–\s*(?=\d)", "-", text)  # ranges: 50–90 -> 50-90
    text = re.sub(r"\s*[—–]\s*", ", ", text)       # other dashes -> comma
    text = re.sub(r",\s*,", ",", text)
    return re.sub(r"\s{2,}", " ", text)


SYSTEM = (
    "You write plain-language summaries of medical research for an educated "
    "general audience (no clinical training). In 3-5 sentences, one paragraph, "
    "explain what the study looked at, what it found, and why it matters. Avoid "
    "jargon and abbreviations; spell out drug classes in lay terms. Do not start "
    "with 'This study' every time. Output only the paragraph, no preamble."
)


def build_prompt(meta: dict) -> str:
    parts = [f"Title: {meta.get('title','')}", f"Journal: {meta.get('journal','')}"]
    if meta.get("abstract"):
        parts.append(f"Abstract: {meta['abstract']}")
    return "\n\n".join(parts)


def summarize_one(settings, entry):
    import llm

    text = llm.chat(settings, SYSTEM, build_prompt(entry.metadata), max_tokens=400, temperature=0.4)
    return entry, clean(text)


def main() -> None:
    log = publib.get_logger("summarize")
    force = "--force" in sys.argv[1:]
    targets = [
        e for e in publib.iter_entries()
        if e.metadata.get("title") and (force or not e.metadata.get("summary"))
    ]
    log.info("started", targets=len(targets), force=force)
    if not targets:
        log.info("complete", note="nothing to summarize", elapsed_s=log.elapsed())
        log.flush()
        return

    import llm

    settings = llm.LLMSettings()
    written = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(summarize_one, settings, e) for e in targets]
        for fut in as_completed(futures):
            try:
                entry, text = fut.result()
            except Exception as exc:  # noqa: BLE001
                log.error("llm_error", detail=str(exc))
                continue
            if not text or len(text) < 40:
                log.warn("weak_summary", entry=entry.rel_folder, chars=len(text or ""))
                continue
            meta_path = entry.folder / "metadata.yml"
            body = meta_path.read_text()
            if not body.endswith("\n"):
                body += "\n"
            meta_path.write_text(body + f'"summary": {json.dumps(text, ensure_ascii=False)}\n')
            written += 1
            log.info("wrote_summary", entry=entry.rel_folder, chars=len(text))

    log.info("complete", written=written, elapsed_s=log.elapsed())
    log.flush()


if __name__ == "__main__":
    main()
