---
title: WoS / ORCID reconciliation to find missing papers
status: planned
repos: [publications]
started: 2026-06-25
last_updated: 2026-06-25
effort: L
impact: med
next_step: Pull Will's ORCID works list (public API) and diff its DOIs/titles against the repo's metadata.yml set to produce a "published but not in the repo" gap list
---

# WoS / ORCID reconciliation to find missing papers

## Goal

Turn the one-off cross-reference job started in `HANDOFF.md` into a repeatable
check that answers "which of Will's published papers/abstracts are NOT yet in
this repo?" The repo should be the complete record; today there is no automated
way to detect a missing entry.

## Why

- `HANDOFF.md:12` records the Web of Science profile listing **46 entries**;
  the repo currently has **39** entry folders (25 Publications + 14 Abstracts),
  several of which were backfilled metadata-only. That gap is exactly the set of
  papers worth finding.
- There are **zero** `orcid` references anywhere in the repo, even though the
  schema now has an optional `orcid` field. ORCID's public API
  (`https://pub.orcid.org/v3.0/<orcid-id>/works`) returns Will's full works
  list with DOIs and titles, which is the cleanest authoritative source to diff
  against `metadata.yml`.
- `HANDOFF.md:103-168` already records the WoS UT identifiers for the
  conference abstracts (007-019) that were never completed; those are a second
  reconciliation source.

## Approach

1. Get Will's ORCID iD (one-time; store it, e.g. an `orcid:` field on entries or
   a repo-level constant).
2. Fetch the ORCID works summary via the public API (no auth needed for public
   records). Extract `{doi, title, year}` for each work.
3. Build the local set from `metadata.yml` (`publib.iter_entries` already yields
   every entry's parsed metadata, including `doi`).
4. Diff: report ORCID works whose DOI/title is absent from the repo
   ("missing from repo"), and repo entries absent from ORCID ("not on ORCID",
   e.g. conference abstracts ORCID may not list).
5. Optionally cross-check against the WoS UTs in `HANDOFF.md` for the abstracts
   that predate the ORCID record.
6. Wire it as `scripts/reconcile_orcid.py` (uv header + `publib` logging, same
   pattern as the other scripts) and add a `just reconcile` recipe. Output is a
   gap report, not an automatic write -- new entries still go through
   `/new-publication`.

## Tasks

- [ ] Obtain and record Will's ORCID iD
- [ ] `scripts/reconcile_orcid.py`: fetch ORCID works, diff against `metadata.yml`
- [ ] Produce the "published but missing from repo" gap list
- [ ] Reconcile the gap (create the missing entries via `/new-publication`)
- [ ] Decide whether to persist `orcid` per entry (schema already supports it)
- [ ] Add `just reconcile` + consider folding the check into CI as a warning

## Anchors

- `HANDOFF.md:12` -- WoS profile lists 46 entries (vs 39 repo folders today)
- `HANDOFF.md:103-168` -- recorded WoS UT ids for abstracts 007-019
- `schemas/metadata.schema.json` -- optional `orcid` field already added
- `scripts/publib.py` -- `iter_entries()` builds the local DOI/title set
- ORCID public API: `https://pub.orcid.org/v3.0/<orcid-id>/works`
