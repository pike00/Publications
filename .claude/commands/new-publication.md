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
  info.xml                      -- raw PubMed eSummary XML
  Paper Title.pdf               -- the paper PDF
Abstracts/NNN Short Title/      -- conference abstracts/posters
  info.xml
  Paper Title.pdf
  abstract_id.txt               -- poster/abstract ID if applicable
Unpublished/                    -- unpublished work (flat, no subfolders)
  Paper Title.pdf
README.md                       -- index with links to all PDFs
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

Move the info.xml into the new folder:
```bash
mv /tmp/info.xml "Publications/NNN Folder Name/info.xml"
```

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

- If the paper is not indexed in PubMed and CrossRef also fails, ask the user to provide the metadata manually (title, authors, journal, date, DOI) and skip the info.xml.
- For abstracts, ask if they have a poster/abstract ID. If so, save it to `abstract_id.txt` in the folder.
- For unpublished work, skip the folder creation -- just place the PDF directly in `Unpublished/` and update README.
- If the PDF download fails (403, paywall, etc.), fall back to opening the DOI URL in the browser.
