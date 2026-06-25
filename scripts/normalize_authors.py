#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "pydantic-settings"]
# ///
"""Normalize author names in every metadata.yml to the repo's house style:
initials-first surname, e.g. "CW Pike", "ML Jackson" (CLAUDE.md / new-publication).

Replaces the retired enrich_author_names.py, which did the opposite (expanded to
full forenames like "C William Pike") and fought the personal-site self-author
bolding (exact match on "CW Pike" / "W Pike").

Handles three input shapes and is idempotent on its own output:
  * Vancouver "Surname INITIALS"  -> "INITIALS Surname"   ("Hui G" -> "G Hui")
  * full "Given [Given...] Surname" -> "INITIALS Surname"  ("Derek Liu" -> "D Liu")
  * already initials-first          -> unchanged           ("S Gombar")

Will Pike is always canonicalized to "CW Pike", regardless of the input spelling
(even when only the W initial appears in the source, e.g. "Pike W" -> "CW Pike").
The placeholder author "A UA" (abstracts 001-003, real authors unknown) is left
untouched.

Edits are line-targeted on the quoted author strings only; the rest of each
file is preserved byte-for-byte (no YAML dumper round-trip).
"""

import re
import sys

import publib

PLACEHOLDERS = {"A UA"}

AUTHORS_KEY = re.compile(r'^"?authors"?\s*:\s*$')
LIST_ITEM = re.compile(r'^(\s*-\s*")(?P<name>.+)("\s*)$')
INITIALS = re.compile(r"[A-Z]{1,3}")


def is_initials(token: str) -> bool:
    return bool(INITIALS.fullmatch(token))


def given_initials(tokens: list[str]) -> str:
    """First letter of each given-name token, splitting hyphenated names."""
    out = []
    for tok in tokens:
        for seg in tok.split("-"):
            if seg:
                out.append(seg[0].upper())
    return "".join(out)


def as_will(tokens: list[str]) -> str | None:
    """Return Will Pike's canonical form if these tokens name him, else None."""
    lowered = [t.lower().strip(".") for t in tokens]
    if "pike" not in lowered:
        return None
    letters: set[str] = set()
    for tok in lowered:
        if tok == "pike":
            continue
        if tok == "william":
            letters.add("w")
        elif re.fullmatch(r"[cw]+", tok):
            letters.update(tok)
        else:
            return None  # some other Pike
    # Will Pike is always "CW Pike", even when the source gives only one initial
    # (e.g. "Pike W" / "W Pike" -> "CW Pike").
    if letters and letters <= {"c", "w"}:
        return "CW Pike"
    return None


def normalize(name: str) -> str:
    name = name.strip()
    if name in PLACEHOLDERS:
        return name

    tokens = name.split()
    if len(tokens) < 2:
        return name

    will = as_will(tokens)
    if will:
        return will

    first, last = tokens[0], tokens[-1]
    if is_initials(last) and not is_initials(first):  # Vancouver
        return f"{last} {' '.join(tokens[:-1])}"
    if is_initials(first) and not is_initials(last):  # already normalized
        return name
    # full name: surname is the last token, initials from everything before it
    return f"{given_initials(tokens[:-1])} {last}"


def process_file(entry, log) -> bool:
    meta_path = entry.folder / "metadata.yml"
    if not meta_path.exists():
        return False
    lines = meta_path.read_text().splitlines(keepends=True)

    in_authors = False
    changed = False
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if AUTHORS_KEY.match(stripped):
            in_authors = True
            out.append(line)
            continue
        if in_authors:
            m = LIST_ITEM.match(stripped)
            if m:
                old = m.group("name")
                new = normalize(old)
                if new != old:
                    nl = "\n" if line.endswith("\n") else ""
                    line = f"{m.group(1)}{new}{m.group(3)}{nl}"
                    changed = True
                    log.info("renamed", path=entry.rel_folder, old=old, new=new)
                out.append(line)
                continue
            in_authors = False  # left the authors block
        out.append(line)

    if changed:
        meta_path.write_text("".join(out))
    return changed


def main() -> None:
    log = publib.get_logger("normalize_authors")
    entries = list(publib.iter_entries())
    log.info("started", total=len(entries))
    updated = sum(1 for e in entries if process_file(e, log))
    log.info("complete", updated=updated, elapsed_s=log.elapsed())
    log.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
