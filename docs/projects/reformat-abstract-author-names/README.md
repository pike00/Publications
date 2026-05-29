---
title: Reformat Abstracts author names to FirstInitialMiddleInitial Lastname
status: planned
repos: [publications]
started: 2026-05-29
last_updated: 2026-05-29
effort: S
impact: low
next_step: Reformat the clean Abstracts/*/metadata.yml author lists; manually resolve the malformed "A UA" placeholder entries before converting 001-003
---

# Reformat Abstracts author names to FirstInitialMiddleInitial Lastname

## Goal

Bring the `Abstracts/*/metadata.yml` author lists into the same `FirstInitialMiddleInitial Lastname` style already applied to `Publications/*/metadata.yml` (commit `a79d350`), so author formatting is uniform across the whole `pike00/Publications` repo.

## Why

On 2026-05-29 the 24 `Publications/` author lists were reformatted (e.g. `"C William Pike"` -> `"CW Pike"`, `"Pike CW"` -> `"CW Pike"`). The 13 `Abstracts/` entries were intentionally left untouched at the time for two reasons:

1. **Not site-rendered.** The personal-site loader reads only `Publications/` (`personal-site:src/lib/publications.ts:7`, `PUBLICATIONS_DIR = path.resolve("publications/Publications")`). Abstracts are not displayed anywhere on pikemd.com, so the impact is data consistency only, not a user-facing change.
2. **Malformed source data.** Three abstracts have a single placeholder author `"A UA"`, which the mechanical transform would turn into the nonsense `"UA A"`. Those need real author data (or deletion) before any reformat.

Leaving the repo half-converted (Publications in initials form, Abstracts in mixed full-name/Vancouver form) is the thing this project closes out.

## Approach

Reuse the exact transform already validated on `Publications/`:

- Split each name on whitespace.
- **Reversed "Surname INITIALS"** (2 tokens, 2nd is all-caps 1-3 letters, e.g. `"Pike CW"`, `"Clements M"`) -> `"INITIALS Surname"`.
- **Normal "Given... Surname"**: last token is the surname; concatenate the first letter of each leading given-name token (splitting hyphenated given names into both initials) -> `"INITIALS Surname"`.
- Preserve accents, hyphenated surnames, and apostrophes verbatim.

The `Abstracts` metadata.yml use the same `"authors":`-block + `- "Name"` YAML shape as `Publications`, so the same line-targeted rewrite (edit only the quoted author strings, leave all other keys/format byte-identical) applies. Do **not** round-trip through a YAML dumper — it reflows the whole file.

## Tasks

- [ ] Resolve the `"A UA"` placeholder authors in abstracts 001, 002, 003 (get real author lists, or drop the field) — blocks converting those three
- [ ] Run the validated transform over `Abstracts/*/metadata.yml` (skip the unresolved placeholders)
- [ ] Diff-review every changed author line (same care as the Publications pass)
- [ ] Validate all `Abstracts/*/metadata.yml` still parse as YAML
- [ ] Commit to `pike00/Publications` master; no personal-site pointer bump needed (docs/data-only, no site effect)

## Preview (clean entries, already computed 2026-05-29)

Mechanical results for the 13 abstracts. The `<--` lines convert cleanly; the `A UA` rows are the placeholders that must be fixed first.

- 001 / 002 / 003: `"A UA"` -> `"UA A"`  **(placeholder — do NOT ship; needs real authors)**
- 004 Pre-operative Urodynamics: `Clements M`->`M Clements`, `Pike CW`->`CW Pike`, `Zillioux JM`->`JM Zillioux`, `Rapp D`->`D Rapp`
- 005 Opioid Prescriptions in IC: `Zillioux JM`->`JM Zillioux`, `Pike CW`->`CW Pike`, `Clements M`->`M Clements`, `Rapp D`->`D Rapp`
- 006 PNH Model: `Jananee Muralidharan`->`J Muralidharan`, `C William Pike`->`CW Pike`, `Saurabh Gombar`->`S Gombar`, `Sandeep Jain`->`S Jain`, `Jason Jones`->`J Jones`
- 013 IBD Surveillance Colonoscopy Steroids: `Derek Liu`->`D Liu`, `Chiraag Kulkarni`->`C Kulkarni`, `C William Pike`->`CW Pike`, `Gavin Hui`->`G Hui`, `Saurabh Gombar`->`S Gombar`, `Sidhartha Sinha`->`S Sinha`
- 016 GLP-1 Liver Disease MetALD: `Amir Gougol`->`A Gougol`, `C William Pike`->`CW Pike`, `Niloufar Khanna`->`N Khanna`, `Paul Kwo`->`P Kwo`
- 017 IBD Statins PSC: `Chiraag Kulkarni`->`C Kulkarni`, `C William Pike`->`CW Pike`, `John Mark Gubatan`->`JM Gubatan`, `Saurabh Gombar`->`S Gombar`, `George Cholankeril`->`G Cholankeril`, `Aparna Goel`->`A Goel`, `Sidhartha Sinha`->`S Sinha`
- 018 Cannabis Hyperemesis Leukocytosis: `Leila Neshatian`->`L Neshatian`, `Elisa Karhu`->`E Karhu`, `Nielsen Fernandez-Becker`->`N Fernandez-Becker`, `Linda Anh B Nguyen`->`LAB Nguyen`, `Yen Low`->`Y Low`, `C William Pike`->`CW Pike`
- 020 hs-CRP Testing in ASCVD: `Emil deGoma`->`E deGoma`, `Yung Chyung`->`Y Chyung`, `John Walsh`->`J Walsh`, `C William Pike`->`CW Pike`, `Jananee Muralidharan`->`J Muralidharan`, `Vincent Marino`->`V Marino`, `J Craig Davis`->`JC Davis`, `Saurabh Gombar`->`S Gombar`, `Michael D Shapiro`->`MD Shapiro`
- 021 Post-Liver Transplant Outcomes in Elderly: `Hiba Khan`->`H Khan`, `Nikki Duong`->`N Duong`, `C William Pike`->`CW Pike`, `Jananee Muralidharan`->`J Muralidharan`
- 022 COVID Vaccine Autoimmune Disease: `Srinivasan N`->`N Srinivasan`, `Jackson M`->`M Jackson`, `Pike W`->`W Pike`, `Sarin K`->`K Sarin`

## Anchors

- `Abstracts/*/metadata.yml` — 13 abstract metadata files (this project's targets)
- `Publications/*/metadata.yml` — the 24 already reformatted (reference for the target format; commit `a79d350`)
- `personal-site:src/lib/publications.ts:7` — site loader reads `Publications/` only; confirms Abstracts are not rendered
- `personal-site:src/lib/authors.ts` — `SELF_AUTHOR = ["CW Pike", "W Pike"]`; if any Abstract self-author renders elsewhere later, the initials must match this set
