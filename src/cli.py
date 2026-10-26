"""
CV AI Agent Command-Line Interface (CLI).

Provides commands to parse, validate, and tailor CVs using the AI pipeline:
  - python -m src.cli tailor -i <input_path> [-j <jd_path>] [-o <output_path>] [-r <report_path>]
  - python -m src.cli parse -i <input_path> [-o <output_path>]
  - python -m src.cli validate -i <input_path>
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .llm import LLMProvider
from .pipeline.orchestrator import CvTailorPipeline
from .schemas.cv_input import CvInput
from .yaml_layer.io import load_cv_input_from_text, serialize_yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cv-cli")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _read_file(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path_str}")
    return path.read_text(encoding="utf-8")


def _write_file(path_str: str, content: str) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def _run_tailor(
    cv_input: CvInput,
    output_path: Optional[str] = None,
    report_path: Optional[str] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> int:
    pipeline = CvTailorPipeline()

    async def on_progress(event: dict):
        step = event.get("step", "progress")
        msg = event.get("message", "")
        print(f"[{step.upper()}] {msg}")

    print(f"Starting CV tailoring for '{cv_input.name}' (Target: {cv_input.position})...")
    cv_yaml, report, tailored_cv = await pipeline.tailor(
        cv_input=cv_input,
        llm_provider=llm_provider,
        on_progress=on_progress,
    )

    if output_path:
        _write_file(output_path, cv_yaml)
        print(f"[SUCCESS] Tailored CV written to: {output_path}")
    else:
        print("\n--- TAILORED CV YAML ---")
        print(cv_yaml)

    if report_path:
        report_yaml = serialize_yaml(report.model_dump())
        _write_file(report_path, report_yaml)
        print(f"[SUCCESS] Audit report written to: {report_path}")

    return 0


def cmd_tailor(args: argparse.Namespace, llm_provider: Optional[LLMProvider] = None) -> int:
    try:
        raw_text = _read_file(args.input)
        cv_input = load_cv_input_from_text(raw_text)

        if args.jd:
            cv_input.jd = _read_file(args.jd)

        if args.locale:
            cv_input.control.locale = args.locale

        if args.industry:
            cv_input.control.industry = args.industry

        if args.locked:
            cv_input.control.locked = [x.strip() for x in args.locked.split(",") if x.strip()]

        return asyncio.run(
            _run_tailor(
                cv_input=cv_input,
                output_path=args.output,
                report_path=args.report,
                llm_provider=llm_provider,
            )
        )
    except Exception as exc:
        logger.error("Tailor failed: %s", exc)
        return 1


def cmd_parse(args: argparse.Namespace) -> int:
    try:
        raw_text = _read_file(args.input)
        cv_input = load_cv_input_from_text(raw_text)
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
        raw_text = _read_file(args.input)
        cv_input = load_cv_input_from_text(raw_text)
        print(f"[VALID] Schema valid:")
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
        description="CV AI Agent - CLI tool for tailoring, parsing and validating CVs",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: tailor
    tailor_parser = subparsers.add_parser("tailor", help="Tailor a CV using AI against a Job Description")
    tailor_parser.add_argument("-i", "--input", required=True, help="Path to input CV file (YAML or Markdown)")
    tailor_parser.add_argument("-j", "--jd", required=False, help="Path to target Job Description text file")
    tailor_parser.add_argument("-o", "--output", required=False, help="Path to save tailored CV YAML")
    tailor_parser.add_argument("-r", "--report", required=False, help="Path to save audit report YAML")
    tailor_parser.add_argument("--locale", choices=["vi", "en"], help="Force locale (vi or en)")
    tailor_parser.add_argument("--industry", help="Industry code (e.g. it_software, architecture_construction, data_ai)")
    tailor_parser.add_argument("--locked", help="Comma-separated section paths to lock (e.g. 'experience[0],education')")

    # Subcommand: parse
    parse_parser = subparsers.add_parser("parse", help="Parse a Markdown or YAML CV into normalized YAML")
    parse_parser.add_argument("-i", "--input", required=True, help="Path to input CV file (YAML or Markdown)")
    parse_parser.add_argument("-o", "--output", required=False, help="Path to save parsed YAML")

    # Subcommand: validate
    val_parser = subparsers.add_parser("validate", help="Validate a CV file against the CvInput schema")
    val_parser.add_argument("-i", "--input", required=True, help="Path to input CV file")

    return parser


def main(argv: Optional[List[str]] = None, llm_provider: Optional[LLMProvider] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "tailor":
        return cmd_tailor(args, llm_provider=llm_provider)
    elif args.command == "parse":
        return cmd_parse(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
