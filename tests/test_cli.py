from pathlib import Path
import pytest

from src.cli import main
from src.yaml_layer.io import parse_yaml


@pytest.mark.parametrize("language", ["vi", "en"])
def test_cli_validate_yaml(language):
    source = Path(__file__).parent / "golden" / f"sample_cv_{language}.yaml"
    assert main(["validate", "-i", str(source)]) == 0


def test_cli_validate_markdown():
    source = Path(__file__).parent / "golden" / "sample_cv_markdown.md"
    assert main(["validate", "-i", str(source)]) == 0


def test_cli_parse_markdown_to_yaml(tmp_path: Path):
    output = tmp_path / "parsed_out.yaml"
    source = Path(__file__).parent / "golden" / "sample_cv_markdown.md"
    assert main(["parse", "-i", str(source), "-o", str(output)]) == 0
    data = parse_yaml(output.read_text(encoding="utf-8"))
    assert data["name"] == "Tran Thi Mai"
    assert data["position"] == "Senior BIM Coordinator / Architect"
    assert len(data["experience"]) >= 1


def test_cli_nonexistent_file():
    assert main(["validate", "-i", "tests/golden/nonexistent_cv.yaml"]) == 1
