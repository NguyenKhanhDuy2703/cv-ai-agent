"""
YAML Layer I/O using ruamel.yaml to preserve comments, ordering, and structure.
"""
from io import StringIO
from typing import Any
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ..schemas.cv_input import CvInput


def _get_yaml_instance() -> YAML:
    yaml = YAML(typ="rt")  # round-trip mode
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def parse_yaml(yaml_str: str) -> Any:
    """
    Parses a YAML string into a ruamel.yaml CommentedMap / structure.
    Raises ValueError with line and column information if syntax is invalid.
    """
    yaml = _get_yaml_instance()
    try:
        return yaml.load(yaml_str)
    except YAMLError as exc:
        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark:
            line = problem_mark.line + 1
            col = problem_mark.column + 1
            raise ValueError(f"YAML syntax error at line {line}, column {col}: {exc}") from exc
        raise ValueError(f"YAML syntax error: {exc}") from exc


def serialize_yaml(data: Any) -> str:
    """
    Serializes a ruamel.yaml structure or dict back into a clean YAML string.
    """
    yaml = _get_yaml_instance()
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def load_cv_input_from_yaml(yaml_str: str) -> CvInput:
    """
    Parses YAML and validates into a Pydantic CvInput model.
    """
    parsed = parse_yaml(yaml_str)
    if not isinstance(parsed, dict):
        raise ValueError("Provided YAML must represent a key-value mapping.")

    # Convert ruamel CommentedMap to standard python primitives for Pydantic validation
    # Dumping and reloading with safe loader or json-compatible dict
    import json
    yaml_safe = YAML(typ="safe")
    stream = StringIO()
    _get_yaml_instance().dump(parsed, stream)
    raw_dict = yaml_safe.load(stream.getvalue())

    return CvInput.model_validate(raw_dict)


def load_cv_input_from_text(text: str) -> CvInput:
    """
    Automatically detects whether the provided string is YAML or Markdown,
    and returns a validated CvInput instance.
    """
    text_clean = text.strip()
    if not text_clean:
        raise ValueError("Provided CV text is empty.")

    # If it starts with standard markdown header `# ` or contains section header `\n## `, try markdown first
    if text_clean.startswith("# ") or "\n## " in text_clean:
        try:
            from .markdown_parser import parse_markdown_to_cv_input
            return parse_markdown_to_cv_input(text_clean)
        except Exception:
            pass

    # Attempt YAML loading
    try:
        return load_cv_input_from_yaml(text_clean)
    except Exception as yaml_err:
        try:
            from .markdown_parser import parse_markdown_to_cv_input
            return parse_markdown_to_cv_input(text_clean)
        except Exception:
            raise ValueError(f"Failed to parse input as either YAML or Markdown. YAML error: {yaml_err}")

