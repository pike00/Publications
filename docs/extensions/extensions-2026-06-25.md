# Extension Ideas: publications

Date: 2026-06-25
Context: Canonical, hand-curated list of Will Pike's papers/abstracts (39 `metadata.yml`, 51 PDFs, spanning 2018-2026), consumed by `personal-site` as a git submodule and rendered at pikemd.com.

## Homelab integration surface

This repo is a structured data set (`metadata.yml` per entry) with one downstream consumer (`personal-site` → Cloudflare Pages) and a manual deploy path (`just update-pubs` + `just deploy`). The adjacent homelab services that make it interesting to extend: the **Gitea instance + colocated ares runner** (could validate/build on push where the dead GitHub workflow can't), **Mattermost/janet** (new-paper notifications + deploy trigger), **kindred** (co-authors are real contacts), the **LiteLLM/pikellm proxy** (auto-tagging, plain-language summaries), and **Loki/Grafana** (script logging + a citation dashboard). External APIs already in play: PubMed e-utils, CrossRef, plus the Web of Science / HubSpot exports referenced in `HANDOFF.md`.

## Quick wins

### Fix (or delete) the dead site-notify workflow
- **Effort:** S · **Impact:** high
- **Anchor:** `.github/workflows/notify-site.yml:5` triggers `on: push: branches: [master]`; `CLAUDE.md:9` records the default branch was renamed `master`→`main` on 2026-06-25.
- **Why:** The repository-dispatch that rebuilds personal-site can never fire again because no push ever lands on `master`. Either repoint it to `main` (and reconcile with CLAUDE.md's "pushing here triggers nothing" claim) or delete the file so it stops implying an automation that doesn't exist.

### Regenerate README to match the folders on disk
- **Effort:** S · **Impact:** high
- **Anchor:** README has 23 Publication links + 8 Abstract links; disk has 26 Pub folders + 15 Abstract folders. Pubs 023/024 and Abstracts 013/016/017/018/020/021/022/023 are present but unlinked (`HANDOFF.md:71` "README.md not yet updated"). Make a manifest.yaml type script that generates the list automatically, and checks on pre-push that this is up to date. 
- **Why:** The public index silently omits ~10 real entries, so the website renders an incomplete CV. This is the most visible defect in the repo right now.

### Tag the 14 untagged abstracts
- **Effort:** S · **Impact:** med
- **Anchor:** every entry under `Abstracts/` lacks a `tags:` field (001-006, 013, 016-018, 020-023); all `Publications/` entries have them. `CLAUDE.md:46` "An entry with no `tags` renders chip-less."
- **Why:** Abstracts render without topic chips on the site while papers don't, for no reason other than they were backfilled before tags became first-class.

### Delete the stray `To Download.md`
- **Effort:** S · **Impact:** low
- **Anchor:** `To Download.md` is a 4-line curl recipe already superseded by `.claude/commands/new-publication.md:72`.
- **Why:** Leftover scratch note duplicating skill content; clutters the repo root.

### Archive the finished reformat-author-names project
- **Effort:** S · **Impact:** low
- **Anchor:** `docs/projects/reformat-abstract-author-names/README.md` — the work it describes shipped in commit `a79d350`.
- **Why:** Per your "archive completed projects aggressively" rule; run `/project-archive` so it stops reading as active.

## New features

### README generator from metadata (single source of truth)
- **Effort:** M · **Impact:** high
- **Anchor:** README links and `metadata.yml` files are maintained by hand in parallel, which is exactly how the 26-vs-23 / 15-vs-8 drift above happened.
- **Why:** A `scripts/generate_readme.py` that walks `Publications/`/`Abstracts/`, reads each `metadata.yml`, and emits the index makes drift structurally impossible. README becomes a build artifact, not a thing humans edit.

### Reconcile the author-format contradiction
- **Effort:** M · **Impact:** high
- **Anchor:** `enrich_author_names.py:38-42` rewrites authors to *full forenames* ("C William Pike"); `CLAUDE.md:37-41` and `new-publication.md:117` mandate the *opposite* (initials-first "CW Pike"). On disk both coexist: `025/metadata.yml` has "CW Pike" / "AT Ayers", `Abstracts/013` has "Derek Liu" / "C William Pike".
- **Why:** The personal-site bolds the self-author by exact match on `CW Pike`/`W Pike` (`src/lib/authors.ts`), so every "C William Pike" entry renders Will's name unbolded. The enrich script actively fights the house style; either retire it or split into `authors` (canonical short) + an optional `authors_full`.

### DOI / link validator script
- **Effort:** M · **Impact:** med
- **Anchor:** 30/39 entries carry a `doi:`; nothing checks they resolve. Schema only pattern-matches `^10\.` (`schemas/metadata.schema.json:13`).
- **Why:** A `scripts/check_links.py` that HEADs each DOI and verifies each README PDF path exists catches typo'd DOIs and broken links before they ship to the public site.

### Extract abstract text into metadata
- **Effort:** L · **Impact:** med
- **Anchor:** 51 PDFs on disk; `metadata.yml` stores only bibliographic fields, no `abstract`. Schema has no abstract field (`schemas/metadata.schema.json`).
- **Why:** Pulling the abstract (from PubMed efetch where `pmid` exists, else the PDF) into an `abstract:` field makes the site searchable and lets you show summaries without re-fetching. Pairs with the pikellm summary idea below.

### Standalone publications.pdf
- **Effort:** L · **Impact:** low
- **Anchor:** the same metadata that builds the website could build a formatted CV; today there is no publications CV output.


### pikellm auto-tagging for the untagged abstracts
- **Effort:** M · **Impact:** med
- **Anchor:** 14 abstracts have no `tags`; `CLAUDE.md:43-48` defines the controlled vocabulary (Cardiology, Hepatology, Substance Use, …).
- **Why:** A script that sends title+journal to the LiteLLM proxy (`deepseek-v4-pro-cloud`) with a JSON-schema response constrained to the existing tag vocabulary backfills chips in one pass, with you approving the diff. **Services: LiteLLM/pikellm proxy + the metadata `tags` field.**


### improved logging in the scripts
- **Effort:** S · **Impact:** low
- **Anchor:** `validate_metadata.py` / `enrich_author_names.py` `print()` to stdout only; your global rule requires host-run scripts to emit JSON logs. 


### Make metadata the single source of truth
- **Effort:** M · **Impact:** high
- **Anchor:** README index + `metadata.yml` are two parallel hand-maintained sources (the drift in Quick wins is the symptom).
- **Why:** Combine the README generator + Gitea drift-check so the metadata files are authoritative and README/site are derived. Eliminates an entire class of "forgot to update the README" bugs.

### Bring scripts up to the host scripting standard
- **Effort:** M · **Impact:** med
- **Anchor:** `scripts/*.py` import `yaml`/`jsonschema` bare with no dependency declaration; no `pyproject.toml`/`requirements.txt`; no `pydantic-settings`.
- **Why:** Convert each to a `uv` inline-script header (`# /// script … ///`) so `uv run scripts/validate_metadata.py` is hermetic, and add a `justfile` (`validate`, `enrich`, `readme`, `deploy`) so the workflow isn't tribal knowledge. Aligns with your uv-first + project-kit conventions.

### Tighten the schema
- **Effort:** S · **Impact:** med
- **Anchor:** `schemas/metadata.schema.json:14` types `pub_type` as a free string; on disk it holds 5 inconsistent values ("Abstract/Poster", "Case Reports", "Review Paper", "Comparative Study", "Journal Article").
- **Why:** Make `pub_type` an `enum`, and consider `required: [tags]` plus new optional `abstract`/`orcid`/`citation_count` fields so the validator enforces what the site actually depends on.


### Plain-language summaries per paper
- **Effort:** L · **Impact:** med
- **Anchor:** titles are dense ("Real-World Evidence Assessment of the Risk of Non-fatal Stroke in Patients Prescribed SGLT2 Inhibitors"); no lay summary exists. These should land in a new pr branch that rqeuires my review. Use deepseek-v4-pro-cloud
- **Why:** A pikellm-generated one-paragraph plain-language summary per entry (stored as `summary:` in metadata, reviewed by you) makes the publications page readable to non-specialists. Pairs with the abstract-extraction feature.
