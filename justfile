set shell := ["bash", "-uc"]

# list recipes
default:
    @just --list

# install the repo git hooks (pre-push validation)
hooks:
    git config core.hooksPath .githooks
    @echo "core.hooksPath -> .githooks (pre-push will validate)"

# validate every metadata.yml against the schema
validate:
    uv run scripts/validate_metadata.py

# regenerate README.md from metadata (single source of truth)
readme:
    uv run scripts/generate_readme.py

# fail if README.md is stale relative to metadata (CI / pre-push)
readme-check:
    uv run scripts/generate_readme.py --check

# check DOIs resolve + every README link target exists (--offline skips DOIs)
links *ARGS:
    uv run scripts/check_links.py {{ARGS}}

# normalize author names to initials-first house style
normalize:
    uv run scripts/normalize_authors.py

# convert downloaded info.xml files into metadata.yml
convert:
    uv run scripts/convert_xml_to_yaml.py

# pull abstracts from PubMed into the abstract field (--pdf for PDF fallback)
abstracts *ARGS:
    uv run scripts/extract_abstracts.py {{ARGS}}

# render the publications.pdf CV (-> build/)
cv:
    uv run scripts/build_cv.py

# propose tags for untagged entries via the LLM proxy (--apply to write)
autotag *ARGS:
    uv run scripts/autotag.py {{ARGS}}

# draft plain-language summaries via the LLM proxy (run on a branch)
summarize *ARGS:
    uv run scripts/summarize.py {{ARGS}}

# full check: metadata valid + README current + links/DOIs resolve
check:
    uv run scripts/validate_metadata.py
    uv run scripts/generate_readme.py --check
    uv run scripts/check_links.py

# offline check (no network): metadata valid + README current + links exist
check-offline:
    uv run scripts/validate_metadata.py
    uv run scripts/generate_readme.py --check
    uv run scripts/check_links.py --offline
