# Metadata YAML Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all `info.xml` and `abstract_id.txt` files with validated `metadata.yml` files, making curated publication metadata the canonical source.

**Architecture:** A JSON Schema defines the metadata format. A Python script converts existing XML to YAML. Manual entries fill gaps for non-PubMed papers. The `/new-publication` skill is updated to produce `metadata.yml` instead of `info.xml`.

**Tech Stack:** Python 3 (pyyaml, jsonschema), JSON Schema Draft 2020-12

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `schemas/metadata.schema.json` | Create | JSON Schema for validating metadata.yml |
| `scripts/convert_xml_to_yaml.py` | Create | One-shot migration: parse XML -> YAML |
| `scripts/validate_metadata.py` | Create | Validate all metadata.yml against schema |
| `Publications/*/metadata.yml` | Create (21) | Per-publication metadata |
| `Abstracts/*/metadata.yml` | Create (6) | Per-abstract metadata |
| `Publications/*/info.xml` | Delete (17) | Replaced by metadata.yml |
| `Abstracts/*/info.xml` | Delete (5) | Replaced by metadata.yml |
| `Abstracts/*/abstract_id.txt` | Delete (5) | Merged into metadata.yml |
| `.claude/commands/new-publication.md` | Modify | Update to produce metadata.yml |

---

### Task 1: Create JSON Schema

**Files:**
- Create: `schemas/metadata.schema.json`

- [ ] **Step 1: Create the schema file**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Publication Metadata",
  "description": "Schema for publication and abstract metadata files",
  "type": "object",
  "required": ["title", "authors", "journal", "date_published"],
  "additionalProperties": false,
  "properties": {
    "title":          { "type": "string", "minLength": 1 },
    "authors":        { "type": "array", "items": { "type": "string", "minLength": 1 }, "minItems": 1 },
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

- [ ] **Step 2: Commit**

```bash
git add schemas/metadata.schema.json
git commit -m "Add JSON Schema for publication metadata.yml validation"
```

---

### Task 2: Write Conversion Script

**Files:**
- Create: `scripts/convert_xml_to_yaml.py`

- [ ] **Step 1: Install dependencies**

```bash
pip install pyyaml jsonschema
```

- [ ] **Step 2: Write the conversion script**

The script must:
1. Accept a root directory argument (defaults to repo root)
2. Walk `Publications/` and `Abstracts/` subdirectories
3. For each `info.xml`, parse the eSummary XML using `xml.etree.ElementTree`
4. Extract fields: Title, AuthorList, FullJournalName, Source, PubDate/EPubDate,
   DOI, PubTypeList, Id (PMID), PMC, Volume, Issue, Pages
5. Convert PubMed date strings to ISO 8601 YYYY-MM-DD:
   - "2019 Jul 2" -> "2019-07-02"
   - "2018 Oct" -> "2018-10-01" (first of month when day unknown)
   - "2020 Nov 25" -> "2020-11-25"
6. Strip trailing periods from titles
7. Read `abstract_id.txt` if present in same directory
8. Validate each output against JSON Schema
9. Write `metadata.yml` with fields in schema order
10. Print summary: converted count, errors, skipped

- [ ] **Step 3: Run the script on a single XML to verify**

```bash
python scripts/convert_xml_to_yaml.py --dry-run
```

- [ ] **Step 4: Commit**

```bash
git add scripts/convert_xml_to_yaml.py
git commit -m "Add XML to YAML conversion script for metadata migration"
```

---

### Task 3: Write Validation Script

**Files:**
- Create: `scripts/validate_metadata.py`

- [ ] **Step 1: Write the validation script**

The script must:
1. Walk `Publications/` and `Abstracts/` subdirectories
2. For each `metadata.yml`, load and validate against the JSON Schema
3. Report per-file pass/fail with specific error messages
4. Exit code 0 if all pass, 1 if any fail
5. Print summary count

- [ ] **Step 2: Commit**

```bash
git add scripts/validate_metadata.py
git commit -m "Add metadata.yml validation script"
```

---

### Task 4: Fetch Missing PubMed XML for Publications 012 and 019

**Files:**
- Create: `Publications/012 Fracture Risk GLP v Sleeve Gastrectomy/info.xml`
- Create: `Publications/019 MetALD + AUD + GLP1/info.xml`

- [ ] **Step 1: Fetch XML for PMID 41467149 (publication 012)**

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=41467149" \
  -o "Publications/012 Fracture Risk GLP v Sleeve Gastrectomy/info.xml"
```

- [ ] **Step 2: Fetch XML for PMID 41813606 (publication 019)**

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=41813606" \
  -o "Publications/019 MetALD + AUD + GLP1/info.xml"
```

- [ ] **Step 3: Verify both XML files are valid eSummary results**

Read each file and confirm it has `<DocSum>` with expected fields.

---

### Task 5: Run Conversion Script on All XML

- [ ] **Step 1: Run the converter**

```bash
python scripts/convert_xml_to_yaml.py
```

Expected: 19 publication XMLs + 5 abstract XMLs = 24 metadata.yml files created.

- [ ] **Step 2: Validate all generated files**

```bash
python scripts/validate_metadata.py
```

Expected: 24 files pass validation.

- [ ] **Step 3: Spot-check a few outputs against their XML source**

Compare `Publications/001 Online Ratings of Urologists/metadata.yml` with its
`info.xml` to confirm correct field extraction.

- [ ] **Step 4: Commit generated metadata files**

```bash
git add "Publications/*/metadata.yml" "Abstracts/*/metadata.yml"
git commit -m "Generate metadata.yml from info.xml for all indexed publications"
```

---

### Task 6: Hand-Create Metadata for Non-PubMed Papers

**Files:**
- Create: `Publications/007 Capes Paper/metadata.yml`
- Create: `Publications/018 Perioperative Pressure Injuries/metadata.yml`
- Create: `Abstracts/006 PNH Model/metadata.yml`

- [ ] **Step 1: Create metadata.yml for publication 007**

```yaml
title: "The Case of Hannah Capes: How Much Does Consciousness Matter?"
authors:
  - "Shepherd L"
  - "Pike CW"
  - "Persily JB"
  - "Marshall MF"
journal: "Neuroethics"
date_published: "2022-03-15"
doi: "10.1007/s12152-022-09480-4"
pub_type: "Review Paper"
volume: "15"
pages: "14"
```

- [ ] **Step 2: Create metadata.yml for publication 018**

```yaml
title: "Perioperative Pressure Injuries: A Descriptive Study of Patient Characteristics"
authors:
  - "Shih C"
  - "Pike CW"
  - "Hui G"
  - "Munro CA"
journal: "Advances in Skin & Wound Care"
date_published: "2026-01-01"
doi: "10.1097/ASW.0000000000000390"
pub_type: "Journal Article"
journal_abbrev: "Adv Skin Wound Care"
```

- [ ] **Step 3: Create metadata.yml for abstract 006**

Read the PDF to extract metadata, then create the file.

- [ ] **Step 4: Validate all three files**

```bash
python scripts/validate_metadata.py
```

Expected: all 27 files pass.

- [ ] **Step 5: Commit**

```bash
git add "Publications/007 Capes Paper/metadata.yml" \
       "Publications/018 Perioperative Pressure Injuries/metadata.yml" \
       "Abstracts/006 PNH Model/metadata.yml"
git commit -m "Add metadata.yml for non-PubMed publications (007, 018, abstract 006)"
```

---

### Task 7: Delete info.xml and abstract_id.txt Files

- [ ] **Step 1: Delete all info.xml files**

```bash
find Publications/ Abstracts/ -name "info.xml" -delete
```

- [ ] **Step 2: Delete all abstract_id.txt files**

```bash
find Abstracts/ -name "abstract_id.txt" -delete
```

- [ ] **Step 3: Verify no XML or abstract_id.txt remain**

```bash
find Publications/ Abstracts/ -name "info.xml" -o -name "abstract_id.txt" | wc -l
```

Expected: 0

- [ ] **Step 4: Commit**

```bash
git add -A Publications/ Abstracts/
git commit -m "Remove info.xml and abstract_id.txt, replaced by metadata.yml"
```

---

### Task 8: Update /new-publication Skill

**Files:**
- Modify: `.claude/commands/new-publication.md`

- [ ] **Step 1: Update the skill**

Changes needed:
1. Repository Layout section: replace `info.xml` with `metadata.yml`, remove
   `abstract_id.txt` (now a field in `metadata.yml`)
2. Step 3 (Fetch PubMed Metadata): still fetch XML to `/tmp/info.xml` as a
   transient step, but do not save it to the folder
3. Step 6 (Save Metadata): instead of moving `info.xml`, parse the fetched XML
   and write `metadata.yml` with the schema fields. Validate against
   `schemas/metadata.schema.json` before writing.
4. Edge Cases: when PubMed/CrossRef fails, prompt for required fields
   (title, authors, journal, date_published) and write `metadata.yml` directly.
   For abstracts, ask for `abstract_id` and include it in the YAML.

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/new-publication.md
git commit -m "Update new-publication skill to generate metadata.yml"
```

---

### Task 9: Final Validation and Cleanup

- [ ] **Step 1: Run full validation**

```bash
python scripts/validate_metadata.py
```

Expected: 27 files, all pass.

- [ ] **Step 2: Verify no info.xml or abstract_id.txt remain**

```bash
find Publications/ Abstracts/ -name "info.xml" -o -name "abstract_id.txt"
```

Expected: empty output.

- [ ] **Step 3: Verify every publication/abstract folder has metadata.yml**

```bash
for d in Publications/*/; do [ -f "$d/metadata.yml" ] || echo "MISSING: $d"; done
for d in Abstracts/*/; do [ -f "$d/metadata.yml" ] || echo "MISSING: $d"; done
```

Expected: no output (none missing).
