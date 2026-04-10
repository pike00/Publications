#!/usr/bin/env python3
"""Enrich metadata.yml files with full author names from PubMed eFetch.

For each metadata.yml with a pmid, fetches the full article XML from PubMed
and replaces abbreviated author names (e.g., "Pike CW") with full forenames
(e.g., "C William Pike").
"""

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_full_authors(pmid: int) -> list[str] | None:
    """Fetch full author names from PubMed eFetch API."""
    url = f"{EFETCH_URL}?db=pubmed&id={pmid}&retmode=xml"
    try:
        with urlopen(url, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"  FETCH ERROR for PMID {pmid}: {e}")
        return None

    root = ET.fromstring(xml_bytes)
    author_list = root.find(".//AuthorList")
    if author_list is None:
        return None

    authors = []
    for author in author_list.findall("Author"):
        last = author.findtext("LastName", "").strip()
        fore = author.findtext("ForeName", "").strip()
        if last and fore:
            authors.append(f"{fore} {last}")
        elif last:
            authors.append(last)
    return authors if authors else None


def yaml_representer_str(dumper: yaml.Dumper, data: str) -> yaml.Node:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


def process_metadata(metadata_path: Path) -> bool:
    """Update a single metadata.yml with full author names. Returns True if updated."""
    with open(metadata_path) as f:
        data = yaml.safe_load(f)

    if not data or not data.get("pmid"):
        return False

    pmid = data["pmid"]
    full_authors = fetch_full_authors(pmid)
    if not full_authors:
        return False

    old_authors = data.get("authors", [])
    if old_authors == full_authors:
        return False

    data["authors"] = full_authors

    dumper = yaml.Dumper
    dumper.add_representer(str, yaml_representer_str)
    with open(metadata_path, "w") as f:
        yaml.dump(
            data,
            f,
            Dumper=dumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    print(f"  UPDATED: {metadata_path.parent.name}")
    for old, new in zip(old_authors, full_authors):
        if old != new:
            print(f"    {old} -> {new}")
    return True


def main() -> None:
    updated = 0
    skipped = 0

    for directory in ["Publications", "Abstracts"]:
        dir_path = REPO_ROOT / directory
        if not dir_path.exists():
            continue

        print(f"Processing {directory}/...")
        for metadata_path in sorted(dir_path.rglob("metadata.yml")):
            if process_metadata(metadata_path):
                updated += 1
                time.sleep(0.4)  # respect NCBI rate limit
            else:
                skipped += 1

    print(f"\nDone: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()
