"""Check committed Draft 2020-12 schemas and all contract examples offline."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from siftgrain_state.contract import validate
from siftgrain_state.core import check_packet


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    schemas = {}
    for path in sorted((root / "schemas").glob("v*/*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[(int(path.parent.name[1:]), path.name.split(".")[0])] = schema
    count = 0
    for path in sorted((root / "examples").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if path.name == "public-keys.json":
            Draft202012Validator(schemas[(2, "public-keys")]).validate(value)
            from siftgrain_state.signatures import load_public_keys

            load_public_keys(path)
            count += 1
            continue
        if "schema_version" not in value:
            Draft202012Validator(schemas[(1, "counts")]).validate(value)
            count += 1
            continue
        kind = "packet" if "requirements" in value else "report"
        version = value["schema_version"]
        Draft202012Validator(schemas[(version, kind)]).validate(value)
        if kind == "packet":
            validate(value)
            verifier = None
            if value.get("require_signatures"):
                from siftgrain_state.signatures import load_public_keys

                verifier = load_public_keys(root / "examples" / "public-keys.json")
            report = check_packet(value, verifier)
            Draft202012Validator(schemas[(version, "report")]).validate(report)
            for collection, row_kind in [
                ("requirements", "requirement"),
                ("observations", "observation"),
                ("baselines", "baseline"),
            ]:
                for row in value.get(collection, []):
                    Draft202012Validator(schemas[(version, row_kind)]).validate(row)
        count += 1
    print(f"PASS: {len(schemas)} schemas and {count} contract examples")


if __name__ == "__main__":
    main()
