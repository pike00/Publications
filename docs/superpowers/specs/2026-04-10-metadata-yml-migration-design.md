# Publication Metadata Migration: info.xml -> metadata.yml

## Problem

4 of 21 publications lack `info.xml` (PubMed eSummary XML), causing the
personal site to render them with empty authors, journal, and year. Two of
these papers (007, 018) are not on PubMed and never will have XML. The XML
format is also opaque, not human-editable, and couples the repo to PubMed's
data structure.

## Solution

Replace `info.xml` with a curated, human-editable `metadata.yml` per
publication folder. A JSON Schema (`schemas/metadata.schema.json`) enforces
types and required fields. Existing XML files are converted via a one-shot
migration script; the 4 missing publications are filled in manually or from
PubMed.

## Schema

### metadata.yml Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Full publication title (no trailing period) |
| `authors` | array of strings | yes | Author list in "Last Initials" format |
| `journal` | string | yes | Full journal name |
| `date_published` | string (YYYY-MM-DD) | yes | Publication date in ISO 8601 |
| `doi` | string | no | DOI (must start with `10.`) |
| `pub_type` | string | no | e.g., "Journal Article", "Review Paper" |
| `pmid` | integer | no | PubMed ID (positive integer) |
| `pmc` | string | no | PubMed Central ID (e.g., "PMC6632102") |
| `volume` | string | no | Journal volume |
| `issue` | string | no | Journal issue |
| `pages` | string | no | Page range or article number |
| `journal_abbrev` | string | no | Abbreviated journal name from PubMed |
| `abstract_id` | string | no | Poster/presentation ID (abstracts only) |

### Validation Rules

- `date_published` must be `YYYY-MM-DD` (full date required, no month-only).
  When PubMed provides only month (e.g., "2018 Oct"), use the 1st of that
  month (`2018-10-01`).
- `doi` must match pattern `^10\.` (standard DOI prefix).
- `pmc` must match pattern `^PMC\d+$`.
- `pmid` must be a positive integer.
- `additionalProperties: false` -- unknown keys fail validation.

### JSON Schema

Location: `schemas/metadata.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Publication Metadata",
  "type": "object",
  "required": ["title", "authors", "journal", "date_published"],
  "additionalProperties": false,
  "properties": {
    "title":          { "type": "string", "minLength": 1 },
    "authors":        { "type": "array", "items": { "type": "string" }, "minItems": 1 },
    "journal":        { "type": "string", "minLength": 1 },
    "date_published": { "type": "string", "pattern": "^\\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])$" },
    "doi":            { "type": "string", "pattern": "^10\\." },
    "pub_type":       { "type": "string" },
    "pmid":           { "type": "integer", "minimum": 1 },
    "pmc":            { "type": "string", "pattern": "^PMC\\d+$" },
    "volume":         { "type": "string" },
    "issue":          { "type": "string" },
    "pages":          { "type": "string" },
    "journal_abbrev": { "type": "string" },
    "abstract_id":    { "type": "string" }
  }
}
```

### Example metadata.yml

```yaml
title: "Online Ratings of Urologists: Comprehensive Analysis"
authors:
  - "Pike CW"
  - "Zillioux J"
  - "Rapp D"
journal: "Journal of medical Internet research"
date_published: "2019-07-02"
doi: "10.2196/12436"
pub_type: "Journal Article"
pmid: 31267982
pmc: "PMC6632102"
volume: "21"
issue: "7"
pages: "e12436"
journal_abbrev: "J Med Internet Res"
```

## Migration Plan

### Inventory

| Source | Count | Method |
|--------|-------|--------|
| Publications with `info.xml` | 17 | Script: parse XML -> YAML |
| Publication 012 (PMID 41467149) | 1 | Fetch XML from PubMed, then convert |
| Publication 019 (PMID 41813606) | 1 | Fetch XML from PubMed, then convert |
| Publication 007 (not on PubMed) | 1 | Hand-create from PDF |
| Publication 018 (ahead-of-print, not indexed) | 1 | Hand-create from PDF |
| Abstracts with `info.xml` (001-005) | 5 | Script: parse XML -> YAML |
| Abstracts with `abstract_id.txt` (001-005) | 5 | Merge into `metadata.yml` |
| Abstract 006 (no XML, PDF only) | 1 | Hand-create from PDF |

### Paper 007 Metadata (from PDF)

- Title: "The Case of Hannah Capes: How Much Does Consciousness Matter?"
- Authors: Shepherd L, Pike CW, Persily JB, Marshall MF
- Journal: Neuroethics
- Date: 2022-03-15 (online publication date from PDF)
- DOI: 10.1007/s12152-022-09480-4
- Volume: "15", Pages: "14"
- Pub type: Review Paper

### Paper 018 Metadata (from PDF)

- Title: "Perioperative Pressure Injuries: A Descriptive Study of Patient Characteristics"
- Authors: Shih C, Pike CW, Hui G, Munro CA
- Journal: Advances in Skin & Wound Care
- Date: 2026-01-01 (ahead-of-print, no final date yet; update when assigned)
- DOI: 10.1097/ASW.0000000000000390
- Pub type: Journal Article
- Note: Paper accepted 2025-09-22. Date should be updated once final
  volume/issue is published and a real publication date is available.

### Migration Script

Location: `scripts/convert_xml_to_yaml.py`

Responsibilities:
1. Walk `Publications/` and `Abstracts/` directories
2. For each `info.xml`, parse the PubMed eSummary XML
3. Convert PubMed date format ("2019 Jul 2") to ISO 8601 ("2019-07-02")
4. If `abstract_id.txt` exists in the same folder, read it and include as
   `abstract_id`
5. Validate output against the JSON Schema before writing
6. Write `metadata.yml` to the same folder
7. Report any validation errors or conversion issues

The script does NOT delete `info.xml` or `abstract_id.txt`. Deletion is a
separate manual step after verification.

Dependencies: `pyyaml`, `jsonschema` (standard Python libraries or
pip-installable).

### Post-Migration Cleanup

1. Verify all `metadata.yml` files pass schema validation
2. Spot-check a sample against their `info.xml` source
3. Delete all `info.xml` files
4. Delete all `abstract_id.txt` files
5. Commit the migration

### Downstream Changes

**`/new-publication` skill** (this repo):
- Update to generate `metadata.yml` instead of fetching/saving `info.xml`
- When PubMed XML is available, parse it into the YAML fields
- When not (CrossRef fallback or manual), prompt for required fields
- Validate against JSON Schema before writing

**`pike00/personal-site`** (separate repo, separate PR):
- Update `publications.ts` to read `metadata.yml` instead of `info.xml`
- Remove XML parsing logic
- The empty-metadata fallback (lines 129-149) becomes unnecessary
- All publications will have complete metadata

## File Changes Summary

### New Files
- `schemas/metadata.schema.json` -- JSON Schema definition
- `scripts/convert_xml_to_yaml.py` -- one-shot migration script
- `*/metadata.yml` -- one per publication/abstract folder (27 total)

### Modified Files
- `.claude/commands/new-publication.md` -- update to generate metadata.yml

### Deleted Files (after migration verification)
- `*/info.xml` -- all 22 XML files
- `*/abstract_id.txt` -- all abstract ID text files
