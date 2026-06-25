#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml", "httpx"]
# ///
"""Validate that the repo's links resolve before they ship to the public site.

Checks, in one pass:
  * every Markdown link target in README.md exists on disk (catches broken PDF
    paths / renamed folders);
  * every metadata ``doi`` is a registered DOI, via the doi.org handles API
    (https://doi.org/api/handles/<doi>) -- this confirms registration without
    fetching the publisher page (which often 403s bots);
  * warns (does not fail) on entries with no PDF or no tags.

Exit 1 on any broken link or unregistered/unreachable DOI; 0 otherwise.
Pass --offline to skip the DOI network checks.
"""

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import httpx

import publib

REPO_ROOT = publib.REPO_ROOT
README = REPO_ROOT / "README.md"
LINK_RE = re.compile(r"\[[^\]]*\]\((<[^>]+>|[^)]+)\)")
HANDLES_API = "https://doi.org/api/handles/"


def readme_targets() -> list[str]:
    if not README.exists():
        return []
    out = []
    for m in LINK_RE.finditer(README.read_text()):
        dest = m.group(1).strip("<>")
        if not dest.startswith(("http://", "https://", "#", "mailto:")):
            out.append(dest)
    return out


def doi_registered(doi: str) -> tuple[str, bool, str]:
    """Return (doi, ok, detail). responseCode 1 == handle exists."""
    try:
        resp = httpx.get(
            HANDLES_API + quote(doi, safe="/"),
            headers={"Accept": "application/json"},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        code = resp.json().get("responseCode")
        return doi, code == 1, f"responseCode={code}"
    except Exception as e:  # noqa: BLE001
        return doi, False, str(e)


def main() -> None:
    log = publib.get_logger("check_links")
    offline = "--offline" in sys.argv[1:]
    entries = list(publib.iter_entries())
    log.info("started", entries=len(entries), offline=offline)

    failures = 0

    # 1. README link targets exist on disk
    targets = readme_targets()
    for dest in targets:
        if not (REPO_ROOT / dest).exists():
            log.error("broken_link", target=dest)
            failures += 1
    log.info("links_checked", total=len(targets))

    # 2. warnings: missing PDF / missing tags
    for e in entries:
        if e.pdf is None:
            log.warn("no_pdf", entry=e.rel_folder)
        if not e.metadata.get("tags"):
            log.warn("no_tags", entry=e.rel_folder)

    # 3. DOI registration
    if not offline:
        dois = sorted({e.metadata["doi"] for e in entries if e.metadata.get("doi")})
        with ThreadPoolExecutor(max_workers=8) as pool:
            for doi, ok, detail in pool.map(doi_registered, dois):
                if ok:
                    log.info("doi_ok", doi=doi)
                else:
                    log.error("doi_unregistered", doi=doi, detail=detail)
                    failures += 1
        log.info("dois_checked", total=len(dois))

    log.info("complete", failures=failures, elapsed_s=log.elapsed())
    log.flush()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
