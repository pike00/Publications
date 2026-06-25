"""Shared helpers for the publications repo tooling.

Importable by any sibling script invoked via ``uv run scripts/<name>.py`` --
uv puts ``scripts/`` on ``sys.path`` so ``import publib`` resolves. Depends only
on the standard library plus PyYAML (every importing script declares ``pyyaml``
in its own ``# /// script`` header).

Provides:
  * ``get_logger`` -- structured JSON logging to stderr (one object per event).
  * ``iter_entries`` / ``Entry`` -- walk ``Publications/`` and ``Abstracts/``,
    yielding parsed metadata + the resolved PDF for each folder.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY_DIRS = ("Publications", "Abstracts")


# --------------------------------------------------------------------------- #
# Structured logging
# --------------------------------------------------------------------------- #
@dataclass
class Logger:
    """Minimal structured logger: one JSON object per event, written to stderr
    immediately. ``flush()`` is a no-op kept for call-site stability (there is
    no buffered sink)."""

    script: str
    _t0: float = field(default_factory=time.monotonic)

    def _emit(self, level: str, msg: str, ctx: dict) -> None:
        rec = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": level,
            "script": self.script,
            "msg": msg,
            **ctx,
        }
        print(json.dumps(rec, ensure_ascii=False), file=sys.stderr, flush=True)

    def info(self, msg: str, **ctx) -> None:
        self._emit("info", msg, ctx)

    def warn(self, msg: str, **ctx) -> None:
        self._emit("warn", msg, ctx)

    def error(self, msg: str, **ctx) -> None:
        self._emit("error", msg, ctx)

    def elapsed(self) -> float:
        return round(time.monotonic() - self._t0, 3)

    def flush(self) -> None:  # stderr is line-flushed already
        return None


def get_logger(script: str) -> Logger:
    return Logger(script=script)


# --------------------------------------------------------------------------- #
# Entry iteration
# --------------------------------------------------------------------------- #
@dataclass
class Entry:
    kind: str  # "Publication" | "Abstract"
    number: str  # zero-padded folder number, e.g. "001" ("" if unparseable)
    title_slug: str  # folder name minus the leading number
    folder: Path
    metadata: dict
    pdf: Path | None

    @property
    def rel_folder(self) -> str:
        return self.folder.relative_to(REPO_ROOT).as_posix()

    @property
    def rel_pdf(self) -> str | None:
        return self.pdf.relative_to(REPO_ROOT).as_posix() if self.pdf else None


def _split_folder(name: str) -> tuple[str, str]:
    head, _, tail = name.partition(" ")
    if head.isdigit():
        return head, tail
    return "", name


def _is_aux_pdf(stem: str) -> bool:
    """Auxiliary PDFs that sit alongside the paper (raw PubMed printout, a
    commentary). Never the canonical entry PDF."""
    s = stem.lower()
    return s in {"pubmed", "info", "esummary"} or "commentary" in s


def find_pdf(folder: Path) -> Path | None:
    """The canonical PDF for an entry: the largest non-auxiliary PDF in the
    folder (folders often also contain a small Pubmed.pdf or a commentary)."""
    pdfs = list(folder.glob("*.pdf"))
    if not pdfs:
        return None
    candidates = [p for p in pdfs if not _is_aux_pdf(p.stem)] or pdfs
    return max(candidates, key=lambda p: (p.stat().st_size, p.name))


def load_metadata(folder: Path) -> dict:
    path = folder / "metadata.yml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def iter_entries(kinds: tuple[str, ...] = ENTRY_DIRS):
    """Yield an ``Entry`` per folder under the given top-level directories,
    ordered by directory then numeric folder prefix."""
    for d in kinds:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        kind = "Publication" if d == "Publications" else "Abstract"
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            number, title_slug = _split_folder(folder.name)
            yield Entry(
                kind=kind,
                number=number,
                title_slug=title_slug,
                folder=folder,
                metadata=load_metadata(folder),
                pdf=find_pdf(folder),
            )
