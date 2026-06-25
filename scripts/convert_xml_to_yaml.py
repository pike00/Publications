#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "jsonschema", "pydantic-settings"]
# ///
"""Convert PubMed eSummary info.xml files to metadata.yml.

Walks Publications/ and Abstracts/, parses each info.xml, and writes a
validated metadata.yml alongside it. Author names land in PubMed's
"Surname INITIALS" form; run normalize_authors.py afterwards to convert them
to the repo's initials-first house style.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

import publib

REPO_ROOT = publib.REPO_ROOT
SCHEMA_PATH = REPO_ROOT / "schemas" / "metadata.schema.json"

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def parse_pubmed_date(date_str: str) -> str:
    """Convert a PubMed date string to ISO 8601 YYYY-MM-DD."""
    parts = date_str.strip().split()
    if len(parts) == 3:
        year, month_str, day = parts
        return f"{year}-{MONTH_MAP.get(month_str, '01')}-{int(day):02d}"
    if len(parts) == 2:
        year, month_str = parts
        return f"{year}-{MONTH_MAP.get(month_str, '01')}-01"
    if len(parts) == 1 and parts[0].isdigit():
        return f"{parts[0]}-01-01"
    raise ValueError(f"Cannot parse PubMed date: {date_str!r}")


def get_item_text(doc_sum: ET.Element, name: str) -> str:
    for item in doc_sum.findall("Item"):
        if item.get("Name") == name:
            return (item.text or "").strip()
    return ""


def get_item_list(doc_sum: ET.Element, name: str) -> list[str]:
    for item in doc_sum.findall("Item"):
        if item.get("Name") == name and item.get("Type") == "List":
            return [
                (sub.text or "").strip()
                for sub in item.findall("Item")
                if (sub.text or "").strip()
            ]
    return []


def get_pmc_id(doc_sum: ET.Element) -> str | None:
    for item in doc_sum.findall("Item"):
        if item.get("Name") == "ArticleIds" and item.get("Type") == "List":
            for sub in item.findall("Item"):
                if sub.get("Name") == "pmc" and sub.text:
                    text = sub.text.strip()
                    if text.startswith("PMC"):
                        return text
    return None


def parse_info_xml(xml_path: Path) -> dict:
    tree = ET.parse(xml_path)
    doc_sum = tree.getroot().find("DocSum")
    if doc_sum is None:
        raise ValueError(f"No DocSum element in {xml_path}")

    title = re.sub(r"\.\s*$", "", get_item_text(doc_sum, "Title"))
    authors = get_item_list(doc_sum, "AuthorList")

    journal = get_item_text(doc_sum, "FullJournalName")
    journal_abbrev = get_item_text(doc_sum, "Source")
    if not journal:
        journal = journal_abbrev

    epub_date = get_item_text(doc_sum, "EPubDate")
    pub_date = get_item_text(doc_sum, "PubDate")
    date_published = parse_pubmed_date(epub_date or pub_date)

    doi = get_item_text(doc_sum, "DOI")
    pub_types = get_item_list(doc_sum, "PubTypeList")
    pub_type = pub_types[0] if pub_types else None
    pmid_str = doc_sum.findtext("Id", "").strip()
    pmid = int(pmid_str) if pmid_str.isdigit() else None
    pmc = get_pmc_id(doc_sum)
    volume = get_item_text(doc_sum, "Volume")
    issue = get_item_text(doc_sum, "Issue")
    pages = get_item_text(doc_sum, "Pages")

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


def yaml_representer_str(dumper: yaml.Dumper, data: str) -> yaml.Node:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


def write_metadata_yml(metadata: dict, output_path: Path) -> None:
    dumper = yaml.Dumper
    dumper.add_representer(str, yaml_representer_str)
    with open(output_path, "w") as f:
        yaml.dump(
            metadata, f, Dumper=dumper, default_flow_style=False,
            allow_unicode=True, sort_keys=False, width=120,
        )


def convert_directory(root: Path, validator, log) -> tuple[int, int]:
    converted = errors = 0
    for xml_path in sorted(root.rglob("info.xml")):
        folder = xml_path.parent
        rel = xml_path.relative_to(REPO_ROOT).as_posix()
        try:
            metadata = parse_info_xml(xml_path)
            abstract_id_path = folder / "abstract_id.txt"
            if abstract_id_path.exists():
                abstract_id = abstract_id_path.read_text().strip()
                if abstract_id:
                    metadata["abstract_id"] = abstract_id

            validation_errors = list(validator.iter_errors(metadata))
            if validation_errors:
                for err in validation_errors:
                    log.error("invalid", path=rel, detail=err.message)
                errors += 1
                continue

            write_metadata_yml(metadata, folder / "metadata.yml")
            log.info("converted", path=rel)
            converted += 1
        except Exception as e:
            log.error("failed", path=rel, detail=str(e))
            errors += 1
    return converted, errors


def main() -> None:
    log = publib.get_logger("convert_xml_to_yaml")
    with open(SCHEMA_PATH) as f:
        validator = Draft202012Validator(json.load(f))

    log.info("started")
    pub_c, pub_e = convert_directory(REPO_ROOT / "Publications", validator, log)
    abs_c, abs_e = convert_directory(REPO_ROOT / "Abstracts", validator, log)
    total_errors = pub_e + abs_e
    log.info("complete", converted=pub_c + abs_c, errors=total_errors, elapsed_s=log.elapsed())
    log.flush()
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
