#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source schema does not exist: {args.source}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "datamodel-codegen",
            "--input",
            str(args.source),
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--output",
            str(args.out),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
