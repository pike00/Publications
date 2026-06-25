#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml", "reportlab"]
# ///
"""Render a formatted publications CV (publications.pdf) from the metadata --
the same source of truth that builds the website.

Reverse-chronological, grouped into Publications and Abstracts/Posters, with the
self-author (CW Pike / W Pike) bolded. Output defaults to build/publications.pdf.

Usage: build_cv.py [output.pdf]
"""

import html
import sys

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import publib

SELF = {"CW Pike", "W Pike"}
DEFAULT_OUT = publib.REPO_ROOT / "build" / "publications.pdf"


def fmt_authors(authors: list[str]) -> str:
    out = []
    for a in authors:
        esc = html.escape(a)
        out.append(f"<b>{esc}</b>" if a in SELF else esc)
    return ", ".join(out)


def citation(meta: dict) -> str:
    authors = fmt_authors(meta.get("authors", []))
    title = html.escape(meta.get("title", "").rstrip("."))
    journal = html.escape(meta.get("journal", ""))
    year = (meta.get("date_published") or "")[:4]

    vip = ""
    if meta.get("volume"):
        vip += html.escape(str(meta["volume"]))
        if meta.get("issue"):
            vip += f"({html.escape(str(meta['issue']))})"
        if meta.get("pages"):
            vip += f":{html.escape(str(meta['pages']))}"
    elif meta.get("pages"):
        vip = html.escape(str(meta["pages"]))

    tail = f"<i>{journal}</i>. {year}"
    if vip:
        tail += f";{vip}"
    tail += "."
    if meta.get("doi"):
        doi = html.escape(meta["doi"])
        tail += f' doi:<link href="https://doi.org/{doi}" color="blue">{doi}</link>.'
    return f"{authors}. {title}. {tail}"


def date_key(entry: publib.Entry) -> str:
    return entry.metadata.get("date_published", "0000-00-00")


def main() -> None:
    log = publib.get_logger("build_cv")
    out = publib.REPO_ROOT / sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)

    entries = [e for e in publib.iter_entries() if e.metadata.get("title")]
    pubs = sorted((e for e in entries if e.kind == "Publication"), key=date_key, reverse=True)
    absts = sorted((e for e in entries if e.kind == "Abstract"), key=date_key, reverse=True)
    log.info("started", publications=len(pubs), abstracts=len(absts), out=str(out))

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body", parent=styles["Normal"], fontSize=9.5, leading=13,
        spaceAfter=7, alignment=TA_LEFT,
    )
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=15, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6)

    flow = [Paragraph("Publications of C. William Pike, MD", h1), Spacer(1, 0.12 * inch)]

    def section(label: str, items: list[publib.Entry]) -> None:
        flow.append(Paragraph(label, h2))
        for i, e in enumerate(items, 1):
            flow.append(Paragraph(f"{i}. {citation(e.metadata)}", body))

    section(f"Peer-Reviewed Publications ({len(pubs)})", pubs)
    section(f"Abstracts, Posters, and Presentations ({len(absts)})", absts)

    SimpleDocTemplate(
        str(out), pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="Publications of C. William Pike, MD",
    ).build(flow)

    log.info("complete", out=str(out), bytes=out.stat().st_size, elapsed_s=log.elapsed())
    log.flush()


if __name__ == "__main__":
    main()
