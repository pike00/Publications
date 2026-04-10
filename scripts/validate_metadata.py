#!/usr/bin/env python3
"""Validate all metadata.yml files against the JSON Schema."""

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "metadata.schema.json"


def main() -> None:
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    validator = Draft202012Validator(schema)

    passed = 0
    failed = 0

    for yml_path in sorted(REPO_ROOT.rglob("metadata.yml")):
        rel_path = yml_path.relative_to(REPO_ROOT)

        try:
            with open(yml_path) as f:
                metadata = yaml.safe_load(f)

            errors = list(validator.iter_errors(metadata))
            if errors:
                print(f"  FAIL: {rel_path}")
                for err in errors:
                    print(f"    - {err.json_path}: {err.message}")
                failed += 1
            else:
                print(f"  OK: {rel_path}")
                passed += 1

        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
