# Scripts

Tooling for the publications repo. Every script is a self-contained `uv` script
(inline `# /// script` dependency header) and emits structured JSON logs to
stderr via `publib.py`. Run them through the `justfile` at the repo root.

| Recipe | Script | What it does |
|---|---|---|
| `just validate` | `validate_metadata.py` | Validate every `metadata.yml` against `schemas/metadata.schema.json` |
| `just readme` | `generate_readme.py` | Regenerate `README.md` from metadata (single source of truth) |
| `just readme-check` | `generate_readme.py --check` | Fail if `README.md` is stale (used by CI / pre-push) |
| `just links` | `check_links.py` | Verify DOIs are registered and README link targets exist |
| `just normalize` | `normalize_authors.py` | Normalize author names to initials-first (`CW Pike`) |
| `just convert` | `convert_xml_to_yaml.py` | Convert downloaded PubMed `info.xml` into `metadata.yml` |
| `just abstracts` | `extract_abstracts.py` | Pull abstracts from PubMed into the `abstract` field (`--pdf` fallback) |
| `just cv` | `build_cv.py` | Render `build/publications.pdf` |
| `just autotag` | `autotag.py` | Propose topic tags for untagged entries (LLM) |
| `just summarize` | `summarize.py` | Draft plain-language summaries (LLM; run on a branch) |
| `just check` | — | validate + readme drift + links/DOIs |

`publib.py` (shared helpers) and `llm.py` (shared pydantic-ai client over the
OpenAI-compatible endpoint) are imported by the others, not run directly.

## Conventions

- **`uv` inline-script scripts**, `requires-python >= 3.14`. Run with `uv run`;
  no virtualenv or `requirements.txt` to manage.
- **Direct HTTP via `httpx`** (never `requests`/`urllib`); LLM calls go through
  **pydantic-ai** (which uses httpx under the hood).
- **Config via `pydantic-settings`** (typed, validated at construction) - see below.
- **Structured JSON logs to stderr** (`publib.get_logger`); start/end events with
  `elapsed_s`.
- **Generated prose** (summaries) uses no em/en dashes and no smart quotes.

## Configuration

Only the LLM scripts (`autotag.py`, `summarize.py`) need config. It is read via
**pydantic-settings** in `llm.py` from the environment and an optional repo-root
**`.env`** file. Copy `.env.example` to `.env` (gitignored) and fill it in:

| Variable | Default | Notes |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:4000/v1` | OpenAI-compatible endpoint (include `/v1`). Also `LITELLM_BASE_URL` / `OPENAI_BASE_URL` |
| `LLM_API_KEY` | — | Required. Also read from `LITELLM_API_KEY` / `OPENAI_API_KEY` |
| `LLM_MODEL` | `deepseek-v4-pro-cloud` | Model id served by the endpoint. Also `PUBLICATIONS_MODEL` |

Settings are validated at construction (a missing key fails fast), and the LLM
client is only built when there is work to do, so an already-tagged /
already-summarized repo runs with no key.
