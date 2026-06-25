#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "pydantic-settings", "pydantic-ai-slim[openai]"]
# ///
"""Propose topic tags for untagged entries via the LLM proxy (pydantic-ai),
constrained to the controlled vocabulary already used across the repo.

Structured output: the agent returns a validated TagSet whose tags are a Literal
of the vocabulary, so the model cannot invent a tag off-list.

Dry-run by default (prints proposals); pass --apply to append the tags line.
Use --all to (re)propose for entries that already have tags. Constructs the LLM
client only when there is work to do, so an all-tagged repo needs no API key.
"""

import json
import sys
from typing import Literal

from pydantic import BaseModel, Field

import publib

VOCAB = (
    "Cardiology", "Endocrinology", "Neurology", "Urology", "Substance Use",
    "Health Informatics", "Hepatology", "Gastroenterology", "Psychiatry",
    "Orthopedics", "Gynecology", "Critical Care", "Infectious Disease",
    "Dermatology", "Telemedicine", "Perioperative Medicine", "Pain Management",
    "Health Equity", "Ethics", "Artificial Intelligence",
)

INSTRUCTIONS = (
    "You are a biomedical librarian. Assign 1-3 topic tags to a paper from the "
    "controlled vocabulary, choosing the most specific applicable topics."
)


class TagSet(BaseModel):
    tags: list[Literal[VOCAB]] = Field(min_length=1, max_length=3)  # type: ignore[valid-type]


def main() -> None:
    log = publib.get_logger("autotag")
    apply = "--apply" in sys.argv[1:]
    do_all = "--all" in sys.argv[1:]

    targets = [
        e for e in publib.iter_entries()
        if (e.folder / "metadata.yml").exists() and (do_all or not e.metadata.get("tags"))
    ]
    log.info("started", targets=len(targets), apply=apply)
    if not targets:
        log.info("complete", note="nothing untagged", elapsed_s=log.elapsed())
        log.flush()
        return

    import llm

    agent = llm.build_agent(llm.LLMSettings(), instructions=INSTRUCTIONS, output_type=TagSet)
    written = 0
    for e in targets:
        prompt = f"Title: {e.metadata.get('title','')}\nJournal: {e.metadata.get('journal','')}"
        try:
            tags = list(dict.fromkeys(agent.run_sync(prompt).output.tags))[:3]
        except Exception as exc:  # noqa: BLE001
            log.error("llm_error", entry=e.rel_folder, detail=str(exc))
            continue
        log.info("proposed", entry=e.rel_folder, tags=tags)
        if apply:
            meta_path = e.folder / "metadata.yml"
            text = meta_path.read_text()
            if not text.endswith("\n"):
                text += "\n"
            meta_path.write_text(text + f'"tags": {json.dumps(tags)}\n')
            written += 1

    log.info("complete", proposed=len(targets), written=written, elapsed_s=log.elapsed())
    log.flush()


if __name__ == "__main__":
    main()
