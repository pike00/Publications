#!/usr/bin/env python3
"""Convert PubMed eSummary info.xml files to metadata.yml.

Walks Publications/ and Abstracts/ directories, parses each info.xml,
and writes a validated metadata.yml alongside it.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "metadata.schema.json"

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def parse_pubmed_date(date_str: str) -> str:
    """Convert PubMed date string to ISO 8601 YYYY-MM-DD.

    Examples:
        "2019 Jul 2"  -> "2019-07-02"
        "2018 Oct"    -> "2018-10-01"
        "2020 Nov 25" -> "2020-11-25"
        "2019"        -> "2019-01-01"
    """
    parts = date_str.strip().split()
    if len(parts) == 3:
        year, month_str, day = parts
        month = MONTH_MAP.get(month_str, "01")
        return f"{year}-{month}-{int(day):02d}"
    if len(parts) == 2:
        year, month_str = parts
        month = MONTH_MAP.get(month_str, "01")
        return f"{year}-{month}-01"
    if len(parts) == 1 and parts[0].isdigit():
        return f"{parts[0]}-01-01"
    raise ValueError(f"Cannot parse PubMed date: {date_str!r}")


def get_item_text(doc_sum: ET.Element, name: str) -> str:
    """Extract text from a named Item element."""
    for item in doc_sum.findall("Item"):
        if item.get("Name") == name:
            return (item.text or "").strip()
    return ""


def get_item_list(doc_sum: ET.Element, name: str) -> list[str]:
    """Extract text from all sub-Items of a named List Item."""
    for item in doc_sum.findall("Item"):
        if item.get("Name") == name and item.get("Type") == "List":
            return [
                (sub.text or "").strip()
                for sub in item.findall("Item")
                if (sub.text or "").strip()
            ]
    return []


def get_pmc_id(doc_sum: ET.Element) -> str | None:
    """Extract PMC ID from ArticleIds list."""
    for item in doc_sum.findall("Item"):
        if item.get("Name") == "ArticleIds" and item.get("Type") == "List":
            for sub in item.findall("Item"):
                if sub.get("Name") == "pmc" and sub.text:
                    text = sub.text.strip()
                    if text.startswith("PMC"):
                        return text
    return None


def parse_info_xml(xml_path: Path) -> dict:
    """Parse a PubMed eSummary XML file into a metadata dict."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    doc_sum = root.find("DocSum")
    if doc_sum is None:
        raise ValueError(f"No DocSum element in {xml_path}")

    # Title -- strip trailing period
    title = get_item_text(doc_sum, "Title")
    title = re.sub(r"\.\s*$", "", title)

    # Authors
    authors = get_item_list(doc_sum, "AuthorList")

    # Journal (full name preferred, fall back to abbreviation)
    journal = get_item_text(doc_sum, "FullJournalName")
    journal_abbrev = get_item_text(doc_sum, "Source")
    if not journal:
        journal = journal_abbrev

    # Date -- prefer EPubDate, fall back to PubDate
    epub_date = get_item_text(doc_sum, "EPubDate")
    pub_date = get_item_text(doc_sum, "PubDate")
    date_str = epub_date if epub_date else pub_date
    date_published = parse_pubmed_date(date_str)

    # DOI
    doi = get_item_text(doc_sum, "DOI")

    # Publication type
    pub_types = get_item_list(doc_sum, "PubTypeList")
    pub_type = pub_types[0] if pub_types else None

    # PMID
    pmid_str = doc_sum.findtext("Id", "").strip()
    pmid = int(pmid_str) if pmid_str.isdigit() else None

    # PMC
    pmc = get_pmc_id(doc_sum)

    # Citation details
    volume = get_item_text(doc_sum, "Volume")
    issue = get_item_text(doc_sum, "Issue")
    pages = get_item_text(doc_sum, "Pages")

    # Build metadata dict, omitting empty optional fields
    metadata: dict = {
        "title": title,
        "authors": authors,
        "journal": journal,
        "date_published": date_published,
    }
    if doi:
        metadata["doi"] = doi
    if pub_type:
        metadata["pub_type"] = pub_type
    if pmid:
        metadata["pmid"] = pmid
    if pmc:
        metadata["pmc"] = pmc
    if volume:
        metadata["volume"] = volume
    if issue:
        metadata["issue"] = issue
    if pages:
        metadata["pages"] = pages
    if journal_abbrev and journal_abbrev != journal:
        metadata["journal_abbrev"] = journal_abbrev

    return metadata


def load_schema() -> Draft202012Validator:
    """Load and return the JSON Schema validator."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def yaml_representer_str(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """Force double-quoted strings for clean YAML output."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


def write_metadata_yml(metadata: dict, output_path: Path) -> None:
    """Write metadata dict to a YAML file with consistent formatting."""
    dumper = yaml.Dumper
    dumper.add_representer(str, yaml_representer_str)
    with open(output_path, "w") as f:
        yaml.dump(
            metadata,
            f,
            Dumper=dumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def convert_directory(root: Path, validator: Draft202012Validator) -> tuple[int, int]:
    """Convert all info.xml files under root to metadata.yml.

    Returns (converted_count, error_count).
    """
    converted = 0
    errors = 0

    for xml_path in sorted(root.rglob("info.xml")):
        folder = xml_path.parent
        output_path = folder / "metadata.yml"
        rel_path = xml_path.relative_to(REPO_ROOT)

        try:
            metadata = parse_info_xml(xml_path)

            # Merge abstract_id.txt if present
            abstract_id_path = folder / "abstract_id.txt"
            if abstract_id_path.exists():
                abstract_id = abstract_id_path.read_text().strip()
                if abstract_id:
                    metadata["abstract_id"] = abstract_id

            # Validate
            validation_errors = list(validator.iter_errors(metadata))
            if validation_errors:
                for err in validation_errors:
                    print(f"  VALIDATION ERROR: {err.message}")
                errors += 1
                continue

            write_metadata_yml(metadata, output_path)
            print(f"  OK: {rel_path} -> metadata.yml")
            converted += 1

        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")
            errors += 1

    return converted, errors


def main() -> None:
    validator = load_schema()

    print("Converting Publications/...")
    pub_converted, pub_errors = convert_directory(REPO_ROOT / "Publications", validator)

    print("\nConverting Abstracts/...")
    abs_converted, abs_errors = convert_directory(REPO_ROOT / "Abstracts", validator)

    total_converted = pub_converted + abs_converted
    total_errors = pub_errors + abs_errors

    print(f"\nDone: {total_converted} converted, {total_errors} errors")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
