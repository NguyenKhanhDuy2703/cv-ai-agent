"""
Tests for YAML layer (src/yaml_layer/io.py).
Tests parsing, serializing, comment preservation, and invalid syntax reporting.
"""
import pytest
from src.yaml_layer.io import parse_yaml, serialize_yaml, load_cv_input_from_yaml
from src.schemas.cv_input import CvInput


SAMPLE_YAML = """# Candidate CV
name: "Tran Van B"
position: "DevOps Engineer"
objective: "Experienced DevOps engineer specializing in Kubernetes and CI/CD."
experience:
  - company: "TechCorp"
    title: "Senior DevOps"
    start: "2021-01"
    end: "2024-01"
    highlights:
      - "Maintained 50+ Kubernetes clusters with 99.99% uptime"
      - "Reduced deployment time by 45%"
education:
  - institution: "Bach Khoa University"
    degree: "Computer Engineering"
    year: "2020"
"""


class TestYamlLayer:
    def test_parse_and_serialize_roundtrip(self):
        doc = parse_yaml(SAMPLE_YAML)
        assert doc["name"] == "Tran Van B"
        assert doc["position"] == "DevOps Engineer"
        output = serialize_yaml(doc)
        assert "Tran Van B" in output
        assert "# Candidate CV" in output

    def test_load_cv_input_from_yaml(self):
        cv_input = load_cv_input_from_yaml(SAMPLE_YAML)
        assert isinstance(cv_input, CvInput)
        assert cv_input.name == "Tran Van B"
        assert cv_input.position == "DevOps Engineer"
        assert len(cv_input.experience) == 1
        assert len(cv_input.experience[0].highlights) == 2

    def test_invalid_yaml_raises_clear_error(self):
        bad_yaml = "name: [unclosed list"
        with pytest.raises(ValueError, match="YAML syntax error"):
            parse_yaml(bad_yaml)
