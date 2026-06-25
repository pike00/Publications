#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "pydantic-settings", "pydantic-ai-slim[openai]"]
# ///
"""Generate a one-line plain-language hook per entry via the LLM proxy
(pydantic-ai) and store it in the metadata ``hook`` field. The hook is the
headline that leads each entry on the publications page: a single punchy
sentence stating the finding or the stakes, not a "Researchers examined..."
preamble (that is what ``summary`` is for).

The hook is grounded in the FULL paper text (extracted from the folder's PDF via
pdftotext), with the abstract kept as a clean anchor for the headline finding;
it falls back to abstract, then summary, for entries with no PDF.

These are LLM-drafted and MUST be reviewed: run this on a dedicated branch and
open a PR. Idempotent (skips entries that already have a hook; --force to
regenerate). The hook is appended as a JSON-encoded YAML scalar so the rest of
each metadata.yml is preserved.
"""

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import publib

MAX_CHARS = 160  # keep in sync with schemas/metadata.schema.json ("hook" maxLength)
FULLTEXT_CHARS = 80000  # cap of extracted PDF text fed to the model (~20k tokens)


def fulltext(folder: Path) -> str:
    """Extract the full paper text from the entry's PDF via pdftotext. Prefers
    the named paper PDF over a bare ``Pubmed.pdf`` (which is only the abstract);
    on multiple candidates picks the largest. Returns '' when there is no PDF or
    extraction fails (caller falls back to abstract/summary)."""
    pdfs = [p for p in folder.glob("*.pdf") if p.name.lower() != "pubmed.pdf"]
    if not pdfs:
        pdfs = list(folder.glob("*.pdf"))  # only a Pubmed.pdf -> use it
    if not pdfs:
        return ""
    pdf = max(pdfs, key=lambda p: p.stat().st_size)
    try:
        out = subprocess.run(
            ["pdftotext", "-q", "-nopgbrk", str(pdf), "-"],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    text = re.sub(r"[ \t]+", " ", out.stdout)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean(text: str) -> str:
    """Normalize LLM output to the house style: strip preamble/labels and stray
    quotes, no em/en dashes, no smart quotes, no trailing period, single clause
    (drop a 'subhead | clickbait' tail). Leaves a bare headline string."""
    text = text.strip()
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"'))
    text = text.splitlines()[0].strip() if text else text      # first line only
    text = re.sub(r"^(hook|headline|title)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip('"').strip("'").strip()          # peel wrapping quotes
    text = text.split(" | ")[0].strip()                        # drop pipe-tail clickbait
    text = re.sub(r"(?<=\d)\s*–\s*(?=\d)", "-", text)  # ranges: 50–90 -> 50-90
    text = re.sub(r"\s*[—–]\s*", ", ", text)      # other dashes -> comma
    text = re.sub(r"\s{2,}", " ", text)
    return text.rstrip(".").strip()


# Openers that turn a hook back into a dry abstract. The prompt bans them; this
# regex is a backstop so a stray "A study found..." gets caught and reworked.
# Only research-FRAMING openers are banned: a hook may legitimately start with an
# article + a concrete subject ("A patient's...", "The diabetes drug...", "The
# racial gap..."), so we never ban a bare article alone.
BANNED_OPENER = re.compile(
    r"^("
    r"researchers?\b|research\b|scientists?\b|investigators?\b|we\b|"
    r"stud(y|ies)\b|findings?\b|results?\b|analy(sis|ses)\b|"
    r"(a|an|the|this|our)\s+(new\s+|recent\s+|large\s+|major\s+|retrospective\s+)?"
    r"(stud(y|ies)|paper|analysis|review|trial|cohort|dataset|case report|research)\b|"
    r"(a|an)\s+(new|recent|large|major)\s+|"
    r"doctors?\s+(examined|looked|found|studied)\b"
    r")",
    re.IGNORECASE,
)

# Number tokens used by the fabrication heuristic. Match standalone quantities
# only: a digit run NOT glued to a letter (so drug/disease names like SGLT2,
# GLP-1, COVID-19 are ignored), plus standalone fraction words. A hook number
# absent from the source text is flagged for review.
_NUM_TOKEN = re.compile(r"(?<![A-Za-z0-9-])\d+(?:\.\d+)?%?(?![A-Za-z0-9])"
                        r"|\b(?:two-thirds|three-quarters|three quarters|half|"
                        r"third|thirds|quarter|quarters|fifth|tenth|double|triple)\b",
                        re.IGNORECASE)


def unsourced_numbers(hook: str, source: str) -> list[str]:
    """Standalone quantities in the hook that do not appear in the source text.
    Heuristic flag for human review; paraphrases (28% -> 'a quarter') may show
    here and are not necessarily wrong."""
    src = source.lower()
    out = []
    for tok in _NUM_TOKEN.findall(hook):
        t = tok.strip().lower()
        if t and t.rstrip("%") not in src and t not in src:
            out.append(t)
    return out

INSTRUCTIONS = (
    "You write the one-line HOOK that headlines a medical paper on a personal "
    "academic website, for a smart general reader with no clinical training. "
    "Write ONE plain declarative sentence (about 8-18 words, max 150 characters) "
    "that states what the paper FOUND, or the question it settles. Lead with the "
    "takeaway, not the method. Start the sentence with the SUBJECT of the finding "
    "(a drug, a test, a patient group, a disease, a clinic), never with a word "
    "about the research itself. Use ONLY facts present in the supplied text. Do "
    "not introduce any number, percentage, or fraction (like '75%', 'three "
    "quarters', 'half', 'doubled') unless that exact figure appears in the text. "
    "If the text says 'many' or 'most', keep it qualitative, do not invent a "
    "precise proportion.\n\n"
    "STYLE: Sentence case, like a newspaper sentence (capitalize only the first "
    "word and proper nouns, NOT Every Word). Calm and factual, never breathless. "
    "Spell drug classes out in plain terms (say 'the diabetes drug semaglutide' "
    "or 'a class of diabetes drugs known as GLP-1 agonists', never a bare "
    "abbreviation like 'GLP-1 RA' or 'UDT').\n\n"
    "HARD BANS: Do not open with 'Researchers', 'Research', 'A study', 'This "
    "study', 'A new/recent/large/major study', 'Scientists', 'Investigators', "
    "'Analysis', 'We', or any 'they examined / looked at / sought to' framing, do "
    "not describe that a study happened, state its result. No Title Case. No "
    "colon-label prefix. No subtitle or ' | ' tail. No quotation marks, no "
    "trailing period, no hype words ('revolutionary', 'groundbreaking', "
    "'impactful', 'transform'), no question-mark clickbait.\n\n"
    "Examples of the right voice (match this register; do not reuse a line unless "
    "the paper truly matches it):\n"
    "- A urologist's online star rating has little to do with their subspecialty\n"
    "- An inhaled lung drug lifts oxygen in only about half of ventilated COVID patients\n"
    "- The diabetes drug semaglutide shows no sign of raising fracture risk\n"
    "- Surgeons largely dropped a routine pre-op bladder test after a landmark trial said to skip it\n"
    "- More than a quarter of women with this painful bladder condition still get opioid prescriptions\n\n"
    "Output only the single line, nothing else."
)


def build_prompt(entry) -> str:
    """Ground the hook in the FULL paper text (authoritative) plus the abstract.
    Source priority: the abstract and the matching full text are authoritative;
    the plain-language summary is only a rough fallback and must NOT be preferred
    over them (a summary can itself be a lossy paraphrase that softens or even
    inverts the real finding). The full text PDF may be a conference proceedings
    page bundling several unrelated abstracts, so the model is told to use only
    the portion matching the title."""
    meta = entry.metadata
    parts = [f"Title: {meta.get('title','')}", f"Journal: {meta.get('journal','')}"]
    if meta.get("abstract"):
        parts.append(f"Abstract (authoritative): {meta['abstract']}")
    ft = fulltext(entry.folder)
    if ft:
        parts.append(
            "Full paper text, extracted from the folder PDF (authoritative for the "
            "exact numbers and direction of the finding). It MAY contain OCR noise "
            "or, for posters, OTHER unrelated abstracts from the same proceedings "
            "page: use ONLY the portion matching the Title above. Do not state a "
            f"finding from an unrelated abstract.\n{ft[:FULLTEXT_CHARS]}")
    if meta.get("summary"):
        parts.append(
            "Plain-language summary (rough fallback only; if it disagrees with the "
            f"abstract or full text, trust those, not this): {meta['summary']}")
    return "\n\n".join(parts)


def main() -> None:
    log = publib.get_logger("hook")
    force = "--force" in sys.argv[1:]
    targets = [
        e for e in publib.iter_entries()
        if e.metadata.get("title") and (force or not e.metadata.get("hook"))
    ]
    log.info("started", targets=len(targets), force=force)
    if not targets:
        log.info("complete", note="nothing to hook", elapsed_s=log.elapsed())
        log.flush()
        return

    import llm

    agent = llm.build_agent(llm.LLMSettings(), instructions=INSTRUCTIONS)
    # Low temperature: a headline should be faithful to the source, not creative.
    model_settings = {"temperature": 0.2}

    def run(entry):
        prompt = build_prompt(entry)
        text = clean(agent.run_sync(prompt, model_settings=model_settings).output)
        if BANNED_OPENER.match(text):  # one retry with an explicit nudge
            nudge = prompt + (
                "\n\nYour previous attempt began with a banned opener. Rewrite it "
                "to lead straight with the finding."
            )
            text = clean(agent.run_sync(nudge, model_settings=model_settings).output)
        return entry, text

    written = 0
    # Short outputs; the bottleneck is per-request model latency, so run more in
    # parallel than summarize.py (whose paragraphs are heavier).
    with ThreadPoolExecutor(max_workers=8) as pool:
        for fut in as_completed([pool.submit(run, e) for e in targets]):
            try:
                entry, text = fut.result()
            except Exception as exc:  # noqa: BLE001
                log.error("llm_error", detail=str(exc))
                continue
            rel = getattr(entry, "rel_folder", "?")
            if not text or len(text) < 15:
                log.warn("weak_hook", entry=rel, chars=len(text or ""))
                continue
            if len(text) > MAX_CHARS:
                log.warn("hook_too_long", entry=rel, chars=len(text), text=text)
                continue
            # Quality flags surface a hook for human review but do NOT drop it,
            # so every entry still gets a draft hook (run on a branch, reviewed).
            if BANNED_OPENER.match(text):
                log.warn("formulaic_hook", entry=rel, text=text)
            source = " ".join(filter(None, [
                entry.metadata.get("abstract", ""),
                entry.metadata.get("summary", ""),
                fulltext(entry.folder),
            ]))
            bad_nums = unsourced_numbers(text, source)
            if bad_nums:
                log.warn("number_not_in_source", entry=rel, numbers=bad_nums, text=text)
            meta_path = entry.folder / "metadata.yml"
            # Replace any existing hook line(s) rather than append, so --force is
            # idempotent and never leaves a duplicate YAML key.
            kept = [ln for ln in meta_path.read_text().splitlines()
                    if not ln.lstrip().startswith('"hook":')]
            new_body = "\n".join(kept).rstrip("\n") + "\n"
            meta_path.write_text(new_body + f'"hook": {json.dumps(text, ensure_ascii=False)}\n')
            written += 1
            log.info("wrote_hook", entry=rel, chars=len(text))

    log.info("complete", written=written, elapsed_s=log.elapsed())
    log.flush()


if __name__ == "__main__":
    main()
