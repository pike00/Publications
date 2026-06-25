# CLAUDE.md - Publications repo

Canonical list of Will Pike's publications and abstracts. Consumed by `personal-site`
as a git submodule and rendered on the public website. Adding entries is handled by the
`/new-publication` skill; this file documents the repo-specific guardrails.

## Default branch is `main`

`main` is the default branch (renamed from `master` on 2026-06-25). `origin/main` is
canonical. Do not recreate `master`.

## Before adding ANY entry: fetch first, then check for duplicates

Entries are frequently pre-created upstream as "accepted" placeholders before a paper is
published, then filled in later. Another machine or PR may already have added the folder.
A stale local tree is how duplicate folders get created. So ALWAYS, before creating anything:

1. Sync: `git fetch origin` then `git merge --ff-only origin/main` (or `git pull --ff-only`).
   Never start from a stale tree.
2. Search for an existing entry by title keyword, DOI, and author across BOTH the working
   tree and `origin/main`:
   - `grep -rin "<keyword>\|<doi>" README.md Publications Abstracts`
   - `git ls-tree -r --name-only origin/main | grep -i "<keyword>"`
   - Look in README for plain-text placeholders like `- <Title> (accepted, <Journal>)`.
3. If an entry already exists (folder or placeholder), FILL IT IN - do not create a new
   numbered folder. A placeholder typically has a partial `metadata.yml` (no `doi`/`volume`/
   `pages`), no PDF, and a non-link README line. Finishing it means: add the missing metadata
   fields, drop the PDF into the folder, and turn the README line into a link.

Only when no entry exists: create `Publications/NNN Short Title/` where NNN =
(highest existing number) + 1, zero-padded to 3 digits.

## Metadata

`metadata.yml` must validate against `schemas/metadata.schema.json`.

**Author format (ALWAYS normalize):** initials-first surname, e.g. `CW Pike`, `ML Jackson` -
NOT surname-first (`Pike CW`). Will Pike is ALWAYS `CW Pike` - every variant collapses to it,
including the single-initial `W Pike`/`Pike W`. `just normalize` (`scripts/normalize_authors.py`)
enforces this mechanically. The personal-site build bolds the self-author by an exact match on
`CW Pike`/`W Pike` (`src/lib/authors.ts`), so any other spelling renders Will's name unbolded.
Convert every name pulled from CrossRef/PubMed to this form before writing the entry.

**Tags (source of truth lives here):** the `tags` field (array of strings) drives the topic
chips on the website. Pick 1-3 from the vocabulary already used across the repo - Cardiology,
Endocrinology, Neurology, Urology, Substance Use, Health Informatics, Hepatology, Psychiatry,
Orthopedics, Gynecology, Critical Care, Infectious Disease, etc. An entry with no `tags` renders
chip-less. (Tags used to live in personal-site at `src/content/publication-tags.yaml`; that file
is retired - the metadata `tags` field is now the only source.)

2026+ papers are often not yet in PubMed - fall back to CrossRef
(`https://api.crossref.org/works/<doi>`) and omit `pmid`/`pmc`.

## Scripts and conventions

`metadata.yml` is the single source of truth: `README.md` is a build artifact
(`just readme`), and `just check` (validate + README drift + DOI/link resolution)
gates the pre-push hook (`just hooks`) and CI. Full recipe list and config in
[scripts/README.md](scripts/README.md). Conventions for anything added here:

- **`uv` inline-script scripts**, `requires-python >= 3.14`; run via `uv run` / `just`.
- **Direct HTTP through `httpx`**, never `requests`/`urllib`; **LLM calls through
  `pydantic-ai`** (`scripts/llm.py`), which uses httpx under the hood.
- **Config through `pydantic-settings`** (typed, validated at construction); secrets
  as `SecretStr`. Only the LLM scripts read config (`.env` / env vars; see `.env.example`).
- **Structured JSON logs to stderr** via `publib.get_logger` (start/end + `elapsed_s`).
- **Generated prose** (LLM summaries) carries no em/en dashes and no smart quotes.

## Updating the live site (deployment)

Pushing to THIS repo triggers nothing - the website does not auto-deploy on a submodule
push. To ship a change to the live site, bump the submodule pointer in personal-site and
deploy from there:

```bash
cd ~/projects/personal-site
just update-pubs   # fetch publications main, bump submodule pointer, copy PDFs, commit
git push           # push the pointer bump
just deploy        # build + deploy to Cloudflare Pages
```

`just update-pubs` follows the branch in personal-site's `.gitmodules`
(`submodule.publications.branch`), which is set to `main`.
