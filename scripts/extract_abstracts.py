#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml", "httpx", "pypdf"]
# ///
"""Populate each entry's ``abstract`` field so the site is searchable and can
show summaries without re-fetching.

Sources, in priority order:
  * PubMed efetch (when ``pmid`` is present) -- authoritative, labeled sections.
  * the entry PDF (only with --pdf) -- best-effort, isolates the text between an
    "Abstract" heading and the next section heading; conservative, skips when it
    cannot isolate a block.

Idempotent: entries that already carry an ``abstract`` are skipped (use --force
to refetch). The field is appended as a single JSON-encoded line, which is a
valid YAML double-quoted scalar, so the rest of each metadata.yml is preserved
byte-for-byte (no dumper round-trip).
"""

import json
import re
import sys
import time
import xml.etree.ElementTree as ET

import httpx

import publib

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SECTION_HEADINGS = re.compile(
    r"\b(introduction|background|methods|materials and methods|keywords|"
    r"objectives?|1\.\s*introduction)\b",
    re.I,
)


def fetch_pubmed_abstract(pmid: int) -> str | None:
    resp = httpx.get(
        EFETCH,
        params={"db": "pubmed", "id": str(pmid), "retmode": "xml"},
        timeout=20,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    segs = root.findall(".//Abstract/AbstractText")
    if not segs:
        return None
    parts = []
    for seg in segs:
        text = "".join(seg.itertext()).strip()
        if not text:
            continue
        label = seg.get("Label")
        parts.append(f"{label}: {text}" if label else text)
    return "\n\n".join(parts) or None


def extract_pdf_abstract(pdf_path) -> str | None:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    text = "\n".join((reader.pages[i].extract_text() or "") for i in range(min(2, len(reader.pages))))
    lower = text.lower()
    start = lower.find("abstract")
    if start == -1:
        return None
    body = text[start + len("abstract"):].lstrip(" :\n\t")
    m = SECTION_HEADINGS.search(body)
    block = body[: m.start()] if m else body[:2500]
    block = re.sub(r"\s+", " ", block).strip()
    # require a plausible abstract length to avoid writing junk
    return block if 200 <= len(block) <= 4000 else None


def append_abstract(meta_path, abstract: str) -> None:
    text = meta_path.read_text()
    if not text.endswith("\n"):
        text += "\n"
    text += f'"abstract": {json.dumps(abstract, ensure_ascii=False)}\n'
    meta_path.write_text(text)


def main() -> None:
    log = publib.get_logger("extract_abstracts")
    use_pdf = "--pdf" in sys.argv[1:]
    force = "--force" in sys.argv[1:]
    entries = list(publib.iter_entries())
    log.info("started", total=len(entries), pdf=use_pdf, force=force)

    written = skipped = 0
    for e in entries:
        meta_path = e.folder / "metadata.yml"
        if not meta_path.exists():
            continue
        if e.metadata.get("abstract") and not force:
            skipped += 1
            continue

        abstract = None
        source = None
        pmid = e.metadata.get("pmid")
        if pmid:
            try:
                abstract = fetch_pubmed_abstract(int(pmid))
                source = "pubmed"
            except Exception as exc:  # noqa: BLE001
                log.warn("pubmed_error", entry=e.rel_folder, detail=str(exc))
            time.sleep(0.4)  # NCBI rate limit
        if not abstract and use_pdf and e.pdf:
            try:
                abstract = extract_pdf_abstract(e.pdf)
                source = "pdf"
            except Exception as exc:  # noqa: BLE001
                log.warn("pdf_error", entry=e.rel_folder, detail=str(exc))

        if abstract:
            append_abstract(meta_path, abstract)
            written += 1
            log.info("wrote_abstract", entry=e.rel_folder, source=source, chars=len(abstract))
        else:
            log.warn("no_abstract", entry=e.rel_folder)

    log.info("complete", written=written, skipped=skipped, elapsed_s=log.elapsed())
    log.flush()


if __name__ == "__main__":
    main()
