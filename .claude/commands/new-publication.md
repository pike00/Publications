---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, AskUserQuestion
description: Add a new publication or abstract to the repository. Fetches metadata from PubMed, creates the folder, handles the PDF, and updates README.md.
---

# Add New Publication

Add a new publication to the Publications repository.

The user provided: $ARGUMENTS

## Repository Layout

```
Publications/NNN Short Title/   -- published journal articles
  metadata.yml                  -- curated publication metadata (validated by schemas/metadata.schema.json)
  Paper Title.pdf               -- the paper PDF
Abstracts/NNN Short Title/      -- conference abstracts/posters
  metadata.yml                  -- includes abstract_id field if applicable
  Paper Title.pdf
Unpublished/                    -- unpublished work (flat, no subfolders)
  Paper Title.pdf
README.md                       -- index with links to all PDFs
schemas/metadata.schema.json    -- JSON Schema for metadata.yml validation
```

Default type is **Publication** unless the user says otherwise.

## Step 1: Parse Input

The user may provide any combination of:
- A PubMed ID (PMID): a number like 39454471
- A DOI: starts with "10." (e.g., 10.1016/j.msard.2024.105921)
- A URL from pubmed.ncbi.nlm.nih.gov, doi.org, sciencedirect.com, etc.
- A local file path to a PDF they already have
- A search query (title or keywords)
- The type: "abstract" or "unpublished" (default is "publication")

Extract whatever identifiers and paths you can. If nothing usable, ask the user for a PMID, DOI, or paper title.

## Step 2: Resolve to PubMed ID

**From PMID:** Go to step 3.

**From DOI:** Search PubMed:
```
WebFetch https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={DOI}[doi]&retmode=json
```
Extract the PMID from `esearchresult.idlist[0]`.

**From URL:**
- `pubmed.ncbi.nlm.nih.gov/NNNNN` -- extract PMID from the path
- `doi.org/10.XXXX/...` -- extract DOI, then search PubMed as above
- ScienceDirect or journal URL -- fetch the page, look for a DOI in meta tags or page content, then resolve via PubMed

**From search query:** Search PubMed:
```
WebFetch https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=5&term={url_encoded_query}
```
Fetch summaries for the returned IDs (step 3) and present a numbered list to the user showing title, journal, date, and authors. Let them pick the right one.

**If PubMed returns nothing for a DOI**, try CrossRef as a fallback:
```
WebFetch https://api.crossref.org/works/{DOI}
```
Tell the user the paper is not in PubMed yet. Extract what metadata you can (title, authors, journal, date) from the CrossRef JSON. You will not have an info.xml -- note this and proceed.

## Step 3: Fetch PubMed Metadata

Download the eSummary XML directly into a temp location:
```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={PMID}" -o /tmp/info.xml
```

Read the XML and extract these fields:
- **Title**: `<Item Name="Title" Type="String">`
- **Authors**: all `<Item Name="Author">` inside AuthorList
- **Journal**: `<Item Name="Source" Type="String">`
- **Full journal name**: `<Item Name="FullJournalName" Type="String">`
- **PubDate**: `<Item Name="PubDate" Type="Date">`
- **DOI**: `<Item Name="DOI" Type="String">`
- **Volume/Issue/Pages**: respective fields

Show the user a summary: title, authors, journal, date. Confirm this is the right paper.

## Step 4: Determine Next Number

List existing folders in the target directory (Publications/ or Abstracts/) and find the highest number:
```bash
ls Publications/ | grep -oP '^\d+' | sort -n | tail -1
```

The new number is max + 1, zero-padded to 3 digits (e.g., 021).

## Step 5: Create Folder

Suggest a short descriptive folder name. Look at existing folder names for style cues -- they use abbreviations and key terms, not the full title. Examples from this repo:
- "002 IC Opioids" (not "Opioid prescription use in patients with interstitial cystitis")
- "017 Heart Transplant Outcomes in SUD"
- "019 MetALD + AUD + GLP1"

Present the suggested folder name and ask the user to confirm or revise:
> "I'll create `Publications/021 Suggested Name/` -- does this work?"

Then create the folder.

## Step 6: Save Metadata

Write a `metadata.yml` file in the new folder using the extracted metadata fields. The file must conform to `schemas/metadata.schema.json`. Include these fields:

**Required:** `title` (strip trailing period), `authors` (see Author format below), `journal` (full name from FullJournalName), `date_published` (ISO 8601 YYYY-MM-DD; use 1st of month if day unknown)

**Recommended:** `doi`, `pub_type` (e.g., "Journal Article"), `tags` (see Tags below)

**Optional:** `pmid` (integer), `pmc` (e.g., "PMC1234567"), `volume`, `issue`, `pages`, `journal_abbrev` (abbreviated name from Source field)

**Author format (ALWAYS normalize):** initials-first surname, e.g. `CW Pike`, `ML Jackson` -- NOT surname-first (`Pike CW`). Will Pike is ALWAYS `CW Pike` (never `WC Pike`, never `Pike WC`). The personal-site build bolds the self-author by an exact match on `CW Pike`/`W Pike`, so any other spelling renders Will's name unbolded on the live site. Convert every name from CrossRef/PubMed to this form before writing.

**Tags:** add a `tags` array (1-3 topic strings). This is the source of truth for the topic chips on the website -- an entry with no tags renders chip-less. Reuse the vocabulary already in the repo (Cardiology, Endocrinology, Neurology, Urology, Substance Use, Health Informatics, Hepatology, Psychiatry, Orthopedics, Gynecology, Critical Care, Infectious Disease, etc.). Propose tags from the title/journal and confirm with the user if unsure.

Omit optional fields that are empty. For abstracts, ask if there is a poster/abstract ID and include it as `abstract_id`.

Use double-quoted strings in the YAML for consistency. Example:

```yaml
"title": "Paper Title Here"
"authors":
- "CW Pike"
- "J Smith"
"journal": "Journal of Example Medicine"
"date_published": "2025-03-15"
"doi": "10.1234/example"
"pub_type": "Journal Article"
"pmid": 12345678
"tags": ["Cardiology", "Health Informatics"]
```

Delete the temporary `/tmp/info.xml` after extracting metadata -- it is not saved to the folder.

## Step 7: Handle the PDF

**If the user provided a local file path:** Copy it into the folder with a filename based on the paper title.

**If the user provided a direct PDF URL:** Download it:
```bash
curl -L -o "Publications/NNN Folder Name/Title.pdf" "URL"
```

**Otherwise:** Construct a DOI link and open it in the browser:
```bash
open "https://doi.org/{DOI}"
```
Tell the user: "I opened the paper's page in your browser. Download the PDF and give me the file path (or drag it into the terminal)."

**PDF filename:** Use the paper title, removing or replacing characters that are problematic in filenames (: / \ " < > | ? *). Keep hyphens and parentheses. Preserve Unicode like en-dashes in the filename -- only strip truly illegal filesystem characters. End with `.pdf`.

## Step 8: Update README.md

Read README.md. Add the new entry at the **end** of the appropriate section:
- Publication: before `## Abstracts, Posters, and Presentations`
- Abstract: before `## Non-Published Abstracts, Posters, etc.`
- Unpublished: before the closing comment or end of file

Entry format (must match exactly):
```
- [Full Paper Title](<relative/path/to/Paper Title.pdf>)
```

The link text is the full paper title from PubMed (strip trailing period if present). The path is relative to the repo root.

## Step 9: Review and Commit

Show the user everything that was created:
- Folder path
- Files in the folder
- The README entry that was added

Ask if they want to commit. If yes:
1. `git fetch origin` first
2. Create a feature branch: `git checkout -b add-pub-NNN-short-name`
3. Stage the new folder and README.md
4. Commit with message: "Add publication on [short description] and update README"

Do NOT push unless the user explicitly asks.

## Edge Cases

- If the paper is not indexed in PubMed and CrossRef also fails, ask the user to provide the required metadata fields (title, authors, journal, date_published) and any optional fields (doi, pub_type, etc.) to write `metadata.yml` directly.
- For abstracts, ask if they have a poster/abstract ID. If so, include it as the `abstract_id` field in `metadata.yml`.
- For unpublished work, skip the folder creation -- just place the PDF directly in `Unpublished/` and update README.
- If the PDF download fails (403, paywall, etc.), fall back to opening the DOI URL in the browser.
