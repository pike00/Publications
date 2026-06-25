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

`publib.py` (shared helpers) and `llm.py` (shared pydantic-ai client) are imported
by the others, not run directly.

## Configuration

Only the LLM scripts (`autotag.py`, `summarize.py`) need config. It is read via
**pydantic-settings** in `llm.py` from the environment and an optional repo-root
**`.env`** file. Copy `.env.example` to `.env` (gitignored) and fill it in:

| Variable | Default | Notes |
|---|---|---|
| `LITELLM_BASE_URL` | `http://127.0.0.1:4000/v1` | OpenAI-compatible endpoint (include `/v1`) |
| `LITELLM_API_KEY` | — | Required. Also read from `OPENAI_API_KEY`, `LITELLM_GATEWAY_KEY`, `AUDIT_SKILLS_PIKELLM_KEY` |
| `PUBLICATIONS_MODEL` | `deepseek-v4-pro-cloud` | Model id served by the endpoint |

Settings are validated at construction (a missing key fails fast), and the LLM
client is only built when there is work to do, so an already-tagged /
already-summarized repo runs with no key.

Optional: set `PUBLICATIONS_LOKI_URL` to push the JSON logs to a Loki endpoint
(otherwise logging is stderr-only).
