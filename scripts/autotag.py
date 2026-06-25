#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "pydantic-settings", "httpx"]
# ///
"""Propose topic tags for untagged entries via the LiteLLM proxy, constrained to
the controlled vocabulary already used across the repo.

Dry-run by default (prints proposals); pass --apply to append the tags line.
Use --all to (re)propose for entries that already have tags. Constructs the LLM
client only when there is work to do, so an all-tagged repo needs no API key.
"""

import json
import re
import sys

import publib

VOCAB = [
    "Cardiology", "Endocrinology", "Neurology", "Urology", "Substance Use",
    "Health Informatics", "Hepatology", "Gastroenterology", "Psychiatry",
    "Orthopedics", "Gynecology", "Critical Care", "Infectious Disease",
    "Dermatology", "Telemedicine", "Perioperative Medicine", "Pain Management",
    "Health Equity", "Ethics", "Artificial Intelligence",
]

SYSTEM = (
    "You are a biomedical librarian. Assign 1-3 topic tags to a paper, chosen "
    "ONLY from this controlled vocabulary: " + ", ".join(VOCAB) + ". "
    "Reply with a JSON array of the chosen tag strings and nothing else."
)


def parse_tags(text: str) -> list[str]:
    m = re.search(r"\[.*?\]", text, re.S)
    raw = json.loads(m.group(0)) if m else []
    return [t for t in raw if t in VOCAB][:3]


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

    settings = llm.LLMSettings()
    written = 0
    for e in targets:
        user = f"Title: {e.metadata.get('title','')}\nJournal: {e.metadata.get('journal','')}"
        try:
            tags = parse_tags(llm.chat(settings, SYSTEM, user, max_tokens=120, temperature=0.0))
        except Exception as exc:  # noqa: BLE001
            log.error("llm_error", entry=e.rel_folder, detail=str(exc))
            continue
        if not tags:
            log.warn("no_tags_proposed", entry=e.rel_folder)
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
