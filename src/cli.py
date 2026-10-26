"""CLI utilities for parsing and validating source CV files."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .yaml_layer.io import load_cv_input_from_text, serialize_yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cv-cli")


def _read_file(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path_str}")
    return path.read_text(encoding="utf-8")


def _write_file(path_str: str, content: str) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cmd_parse(args: argparse.Namespace) -> int:
    try:
        cv_input = load_cv_input_from_text(_read_file(args.input))
        out_yaml = serialize_yaml(cv_input.model_dump(exclude_none=True))
        if args.output:
            _write_file(args.output, out_yaml)
            print(f"[SUCCESS] Parsed CV written to: {args.output}")
        else:
            print(out_yaml)
        return 0
    except Exception as exc:
        logger.error("Parse failed: %s", exc)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        cv_input = load_cv_input_from_text(_read_file(args.input))
        print("[VALID] Schema valid:")
        print(f"  Name: {cv_input.name}")
        print(f"  Position: {cv_input.position}")
        print(f"  Experience count: {len(cv_input.experience)}")
        print(f"  Education count: {len(cv_input.education)}")
        print(f"  Projects count: {len(cv_input.projects)}")
        return 0
    except Exception as exc:
        logger.error("Validation failed: %s", exc)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv-agent",
        description="CV AI Agent - CLI tools for parsing and validating CV source files",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_parser = subparsers.add_parser("parse", help="Parse a Markdown or YAML CV into normalized YAML")
    parse_parser.add_argument("-i", "--input", required=True)
    parse_parser.add_argument("-o", "--output", required=False)
    validate_parser = subparsers.add_parser("validate", help="Validate a CV file against the CvInput schema")
    validate_parser.add_argument("-i", "--input", required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse":
        return cmd_parse(args)
    if args.command == "validate":
        return cmd_validate(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
