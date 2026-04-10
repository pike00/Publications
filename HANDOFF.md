# Handoff: Cross-Reference Publications Repo with HubSpot CRM and Web of Science

## Goal

Exhaustively cross-reference the Publications repository against two external data sources
(HubSpot CRM export and Web of Science JSON) to ensure every published publication and
abstract where Will Pike (C William Pike) is an author is represented in the repo with
correct metadata, PDFs, and README entries.

Data sources (both provided as conversation attachments, not on disk):
- HubSpot CRM: `hubspot-crm-exports-all-records-2026-04-10.csv`
- Web of Science: `www.webofscience.com.json` (46 entries for Pike's WoS profile)

## Current Progress

### Completed

1. **Fixed existing repo issues:**
   - README.md: Added missing Pub_009 (Accuracy of NIBP) entry
   - README.md: Fixed broken Pub_011 link (was pointing to `010 MDD in MS`, now `011 MDD in MS`)
   - Abstract_006 PNH Model: Updated abbreviated author names to full names

2. **Added 3 new publications (folder + metadata.yml + PDF):**
   - `Publications/022 AUD Pharmacotherapy in Hospitalized Patients/` -- COMPLETE
     - "A missed opportunity: a retrospective cohort study of alcohol use disorder pharmacotherapy in hospitalized patients"
     - Alcohol and Alcoholism, 2026-03, DOI: 10.1093/alcalc/agag008, PMID: 41785413
   - `Publications/023 Statin Use and Crohns Disease Stricture/` -- COMPLETE
     - "Statin use is associated with lower rates of stricture development in patients with Crohn's disease"
     - J Crohn's Colitis, 2026-03, DOI: 10.1093/ecco-jcc/jjag034, PMID: 41903936
   - `Publications/024 Answering Clinical Questions with LLM/` -- COMPLETE
     - "Answering real-world clinical questions using large language model, retrieval-augmented generation, and agentic systems"
     - Digital Health, 2025, DOI: 10.1177/20552076251348850, PMID: 40510193, PMC: PMC12159471

3. **Added 2 new abstracts with PDFs and metadata (fully complete):**
   - `Abstracts/020 hs-CRP Testing in ASCVD Prevention/` -- COMPLETE
     - "Utilization of High-Sensitivity C-Reactive Protein Testing in Primary and Secondary ASCVD Prevention"
     - Cardiometabolic Health Congress (CMHC), October 2024
     - Authors: Emil deGoma, Yung Chyung, John Walsh, C William Pike, Jananee Muralidharan, Vincent Marino, J Craig Davis, Saurabh Gombar, Michael D Shapiro
   - `Abstracts/021 Post-Liver Transplant Outcomes in Elderly/` -- COMPLETE
     - "Increase in Mortality and Allograft Rejection Post-Liver Transplant in a Cohort Between 50-90 Years Old"
     - American Journal of Gastroenterology (ACG 2025), Abstract ID: S2879
     - Authors: Hiba Khan, Nikki Duong, C William Pike, Jananee Muralidharan

4. **Added 4 new abstracts with metadata only (no PDFs):**
   - `Abstracts/013 IBD Surveillance Colonoscopy Steroids/metadata.yml` -- COMPLETE
     - Authors: Derek Liu, Chiraag Kulkarni, C William Pike, Gavin Hui, Saurabh Gombar, Sidhartha Sinha
     - IBD journal, 2025-02-28, DOI: 10.1093/ibd/izae282.040
   - `Abstracts/016 GLP-1 Liver Disease MetALD/metadata.yml` -- COMPLETE
     - Authors: Amir Gougol, C William Pike, Niloufar Khanna, Paul Kwo
     - Gastroenterology, DDW 2024
   - `Abstracts/017 IBD Statins PSC/metadata.yml` -- COMPLETE
     - Authors: Chiraag Kulkarni, C William Pike, John Mark Gubatan, Saurabh Gombar, George Cholankeril, Aparna Goel, Sidhartha Sinha
     - Gastroenterology, DDW 2024
   - `Abstracts/018 Cannabis Hyperemesis Leukocytosis/metadata.yml` -- COMPLETE
     - Authors: Leila Neshatian, Elisa Karhu, Nielsen Fernandez-Becker, Linda Anh B Nguyen, Yen Low, C William Pike
     - Gastroenterology, DDW 2024

### Not Yet Completed

5. **9 abstract folders created but MISSING metadata.yml (no author data yet):**
   - `Abstracts/007 AF Disparities/` -- needs metadata
   - `Abstracts/008 Liver Transplant GLP-1 vs Non-GLP-1/` -- needs metadata
   - `Abstracts/009 SGLT-2 Liver Transplant HCC/` -- needs metadata
   - `Abstracts/010 SGLT-2 Diabetes Cirrhosis/` -- needs metadata
   - `Abstracts/011 GLP-1 RA T2DM Cirrhosis/` -- needs metadata
   - `Abstracts/012 Barretts Esophagus Screening/` -- needs metadata
   - `Abstracts/014 Bariatric Surgery MetALD/` -- needs metadata
   - `Abstracts/015 GLP-1 RA Malignancy T2DM/` -- needs metadata
   - `Abstracts/019 GDMT Adherence HFrEF/` -- needs metadata

6. **README.md not yet updated** with any of the new entries (Pub 022-024, Abstracts 007-021).

7. **No PDFs obtained** for Abstracts 007-019. These are conference abstracts published in
   journal supplements -- most don't have standalone PDFs.

## What Worked

- PubMed E-utilities API (esearch + efetch) for full publication metadata (Pubs 022-024)
- Reading poster PDFs directly for author extraction (Abstracts 020, 021)
- WebFetch on DDW digitellinc.com and eposters.ddw.org for author lists (Abstracts 016, 017, 018)
- WebFetch on academic.oup.com for IBD supplement abstract (Abstract 013)

## What Didn't Work

- WebFetch on gastrojournal.org (Elsevier) -- returns 403 for all DDW 2025 Gastroenterology supplement articles
- WebFetch on ahajournals.org -- returns 402/403 (Abstract 007, Circulation AHA supplement)
- WebFetch on jacc.org -- returns 403 (Abstract 019, JACC ACC supplement)
- WebFetch on diabetesjournals.org -- redirects then fails (Abstract 015)
- Elsevier DOI redirects (linkinghub.elsevier.com) return only JavaScript/tracking code, no content

## Next Steps

### 1. Complete the 9 remaining abstract metadata files

Each needs a metadata.yml with title, authors, journal, date_published, pub_type, and
optional fields (doi, volume, issue, journal_abbrev). Here is the known info for each:

**Abstract_007 -- AF Disparities**
- Title: "Disparities in Atrial Fibrillation Clinical Outcomes: Race, Ethnicity, and Sex Differences in Risk of Incident Heart Failure, Stroke, and Mortality"
- Journal: Circulation (AHA Scientific Sessions 2025 Supplement)
- Date: 2025-11-04
- DOI: 10.1161/CIRC.152.SUPPL_3.4367607
- WoS UT: WOS:001613881400007
- HubSpot URL: https://www.ahajournals.org/doi/10.1161/circ.152.suppl_3.4367607
- NEED: author list

**Abstract_008 -- Liver Transplant GLP-1 vs Non-GLP-1**
- Title: "Outcomes in Liver Transplant Recipients with Type 2 Diabetes; A Comparison of GLP-1 Receptor Agonists and Non-GLP-1 Therapies"
- Journal: Gastroenterology (DDW 2025 Supplement)
- Date: 2025-05-03
- WoS UT: WOS:001532668300092
- HubSpot URL: https://www.gastrojournal.org/article/S0016-5085(25)04732-8/abstract
- NEED: author list

**Abstract_009 -- SGLT-2 Liver Transplant HCC**
- Title: "SGLT-2 Inhibitor Therapy in Liver Transplant Recipients May Reduce the Risk of Developing New Hepatocellular Carcinoma"
- Journal: Gastroenterology (DDW 2025 Supplement)
- Date: 2025-05-03
- WoS UT: WOS:001531610700081
- HubSpot URL: https://www.gastrojournal.org/article/S0016-5085(25)01430-1/abstract
- NEED: author list

**Abstract_010 -- SGLT-2 Diabetes Cirrhosis**
- Title: "SGLT-2 Inhibitor Use in Patients with Diabetes and Cirrhosis is Associated with Reduced Liver-Related Adverse Events and Improved Survival"
- Journal: Gastroenterology (DDW 2025 Supplement)
- Date: 2025-05-03
- WoS UT: WOS:001532668300016
- HubSpot URL: https://www.gastrojournal.org/article/S0016-5085(25)04657-8/abstract
- NEED: author list

**Abstract_011 -- GLP-1 RA T2DM Cirrhosis**
- Title: "GLP-1 Receptor Agonist Use in Patients with Type 2 Diabetes and Cirrhosis is Associated with Improved Survival Outcomes"
- Journal: Gastroenterology (DDW 2025 Supplement)
- Date: 2025-05-03
- WoS UT: WOS:001532668300020
- HubSpot URL: https://www.gastrojournal.org/article/S0016-5085(25)04660-8/abstract
- NEED: author list

**Abstract_012 -- Barretts Esophagus Screening**
- Title: "Prevalence of Endoscopic Screening for Barrett's Esophagus in a National Screening Colonoscopy Cohort"
- Journal: Gastroenterology (DDW 2025 Supplement)
- Date: 2025-05-03
- WoS UT: WOS:001532305900117
- HubSpot URL: https://www.gastrojournal.org/article/S0016-5085(25)02666-6/abstract
- NEED: author list

**Abstract_014 -- Bariatric Surgery MetALD**
- Title: "Long-term Outcomes of Bariatric Surgery in Patients with Combined Metabolic Dysfunction and Increased Alcohol Consumption (MetALD)"
- Journal: Hepatology (Liver Meeting 2024 Supplement)
- Date: 2024-10-01
- WoS UT: WOS:001366004001406
- HubSpot URL: https://journals.lww.com/hep/fulltext/2024/10001/category_index.3.aspx
- NEED: author list

**Abstract_015 -- GLP-1 RA Malignancy T2DM**
- Title: "GLP-1 RA and Risk of Malignancy in Patients with Type 2 Diabetes"
- Journal: Diabetes (ADA 84th Scientific Sessions 2024 Supplement)
- Date: 2024-06-01
- DOI: 10.2337/DB24-746-P
- WoS UT: WOS:001301361102079
- Redirect URL: https://diabetesjournals.org/diabetes/article/73/Supplement_1/746-P/155867/746-P-GLP-1-RA-and-Risk-of-Malignancy-in-Patients
- NEED: author list

**Abstract_019 -- GDMT Adherence HFrEF**
- Title: "Impact of Adherence to Guideline-Directed Medical Therapy on Clinical Outcomes in Older Patients with Heart Failure with Reduced Ejection Fraction"
- Journal: JACC (ACC 2024 Supplement)
- Date: 2024-04-02
- WoS UT: WOS:001324901500729
- HubSpot URL: https://www.jacc.org/doi/10.1016/S0735-1097(24)02718-9
- Note: authors are likely Xichong Liu, Chan Hee J Choi, C William Pike, Gavin Hui, Jananee Muralidharan, Shriram Nallamshetty (same as the full paper Pub_013), but verify
- NEED: confirmation of author list

**Approach suggestions for getting authors:**
- Try the `/new-publication` skill which may have PubMed lookup capabilities
- Try Google Scholar search for the exact titles
- For Abstract_019, the authors are almost certainly the same as Pub_013 -- verify and use
- For the DDW 2025 Gastroenterology abstracts (008-012), try the DDW eposter site:
  https://eposters.ddw.org/ddw/2025/ddw-2025/ -- search by title
- For Abstract_014, try the Liver Meeting eposter site
- Ask the user directly -- they authored these and likely know the author lists

### 2. Update README.md

Add all new entries to README.md in the appropriate sections:

**Publications section** (add after Pub_021 entry):
- Pub_022: A missed opportunity (AUD pharmacotherapy)
- Pub_023: Statin use and Crohn's disease stricture
- Pub_024: Answering real-world clinical questions using LLM

**Abstracts section** (add after Abstract_006 entry):
- Abstracts 007-021 (15 new abstracts total)

Follow the existing link format:
```
- [Title](<Abstracts/NNN Folder Name/PDF filename.pdf>)
```

For abstracts without PDFs, either:
- Link to the folder instead of a PDF
- Or note them without a link

### 3. Validate all metadata

Run the existing validation script:
```
python scripts/validate_metadata.py
```

### 4. Consider: PDFs for conference abstracts

Most conference abstracts (007-019) don't have standalone PDFs. Options:
- Download supplement pages from journals (if accessible)
- Screenshot/export from eposter sites
- Leave without PDFs (acceptable for conference abstracts)

## Reference: Schema for metadata.yml

Located at `schemas/metadata.schema.json`. Required fields:
- title (string)
- authors (array of strings, min 1)
- journal (string)
- date_published (YYYY-MM-DD)

Optional: doi, pub_type, pmid (integer), pmc (PMC\d+), volume, issue, pages, journal_abbrev, abstract_id
