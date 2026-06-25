"""Shared helpers for the publications repo tooling.

Importable by any sibling script invoked via ``uv run scripts/<name>.py`` --
uv puts ``scripts/`` on ``sys.path`` so ``import publib`` resolves. Depends on
the standard library plus PyYAML and pydantic-settings (every importing script
declares both in its own ``# /// script`` header, so they are available here).

Provides:
  * ``get_logger`` -- structured JSON logging to stderr, with an optional
    fire-and-forget push to Loki when ``PUBLICATIONS_LOKI_URL`` is set. This
    mirrors the homelab structured-logging convention while staying portable
    for a public repo (no homelab module import, no hard Loki dependency).
  * ``iter_entries`` / ``Entry`` -- walk ``Publications/`` and ``Abstracts/``,
    yielding parsed metadata + the resolved PDF for each folder.
"""

from __future__ import annotations

import json
import socket
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY_DIRS = ("Publications", "Abstracts")


class LogSettings(BaseSettings):
    """Logging-related config. The only env read in the tooling is the optional
    Loki endpoint; absent it, logging is stderr-only and fully portable."""

    model_config = SettingsConfigDict(extra="ignore")
    publications_loki_url: HttpUrl | None = None


# --------------------------------------------------------------------------- #
# Structured logging
# --------------------------------------------------------------------------- #
@dataclass
class Logger:
    """Minimal structured logger: one JSON object per event to stderr.

    Buffers events and, on ``flush()``, pushes them to Loki in a single batch
    iff ``PUBLICATIONS_LOKI_URL`` is set. The push never blocks correctness:
    failures are swallowed and the timeout is short.
    """

    script: str
    _t0: float = field(default_factory=time.monotonic)
    _buf: list[tuple[str, str]] = field(default_factory=list)

    def _emit(self, level: str, msg: str, ctx: dict) -> None:
        rec = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": level,
            "script": self.script,
            "msg": msg,
            **ctx,
        }
        line = json.dumps(rec, ensure_ascii=False)
        print(line, file=sys.stderr, flush=True)
        self._buf.append((str(time.time_ns()), line))

    def info(self, msg: str, **ctx) -> None:
        self._emit("info", msg, ctx)

    def warn(self, msg: str, **ctx) -> None:
        self._emit("warn", msg, ctx)

    def error(self, msg: str, **ctx) -> None:
        self._emit("error", msg, ctx)

    def elapsed(self) -> float:
        return round(time.monotonic() - self._t0, 3)

    def flush(self) -> None:
        url = LogSettings().publications_loki_url
        if not url or not self._buf:
            return
        payload = {
            "streams": [
                {
                    "stream": {
                        "job": "publications",
                        "script": self.script,
                        "host": socket.gethostname(),
                    },
                    "values": [[ns, line] for ns, line in self._buf],
                }
            ]
        }
        try:
            req = urllib.request.Request(
                str(url),
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3).close()
        except Exception:
            pass  # logging must never break the script


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
