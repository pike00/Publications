#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml", "jsonschema"]
# ///
"""Validate every metadata.yml against schemas/metadata.schema.json.

Exit 0 when all entries pass, 1 otherwise. Emits structured JSON logs to
stderr (see publib.get_logger).
"""

import json
import sys

from jsonschema import Draft202012Validator

import publib

SCHEMA_PATH = publib.REPO_ROOT / "schemas" / "metadata.schema.json"


def main() -> None:
    log = publib.get_logger("validate_metadata")
    with open(SCHEMA_PATH) as f:
        validator = Draft202012Validator(json.load(f))

    entries = [e for e in publib.iter_entries() if (e.folder / "metadata.yml").exists()]
    log.info("started", total=len(entries))

    passed = failed = 0
    for entry in entries:
        rel = (entry.folder / "metadata.yml").relative_to(publib.REPO_ROOT).as_posix()
        errors = sorted(validator.iter_errors(entry.metadata), key=str)
        if errors:
            failed += 1
            for err in errors:
                log.error("invalid", path=rel, at=err.json_path, detail=err.message)
        else:
            passed += 1

    log.info("complete", passed=passed, failed=failed, elapsed_s=log.elapsed())
    log.flush()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
