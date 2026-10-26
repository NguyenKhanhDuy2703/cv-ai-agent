"""
Tests for Markdown CV parser (src/yaml_layer/markdown_parser.py).
Tests converting Markdown text into structured CvInput.
"""
import pytest
from src.yaml_layer.markdown_parser import parse_markdown_to_cv_input
from src.schemas.cv_input import CvInput


SAMPLE_MARKDOWN_CV = """# Nguyen Van A
**Target Position:** Senior Backend Engineer
**Objective:** 5 years of backend engineering experience specializing in high-concurrency microservices and Python.

## Work Experience

### FPT Software — Senior Backend Developer
*January 2021 - Present*
- Architected microservices handling 15k requests per second with 99.99% uptime.
- Optimized PostgreSQL database indexes and caching layers, reducing query latency by 40%.

### VNG Corporation — Backend Developer
*June 2019 - December 2020*
- Developed RESTful APIs using Python FastAPI and Redis.
- Implemented automated CI/CD pipeline using GitHub Actions and Docker.

## Projects

### E-commerce Microservices
- Built distributed payment service with RabbitMQ message broker.
- Technologies: Python, FastAPI, Docker, RabbitMQ.

## Education

### Hanoi University of Science and Technology
- Bachelor of Science in Computer Science (2015 - 2019)
- GPA: 3.6/4.0

## Certifications & Achievements
- AWS Certified Solutions Architect (2022)
- Hackathon First Prize Winner (2021)

## Interests
- Open source contribution, Cloud architecture, Marathon running
"""


class TestMarkdownParser:
    def test_parse_structured_markdown_to_cv_input(self):
        cv_input = parse_markdown_to_cv_input(SAMPLE_MARKDOWN_CV)

        assert isinstance(cv_input, CvInput)
        assert cv_input.name == "Nguyen Van A"
        assert cv_input.position == "Senior Backend Engineer"
        assert "5 years of backend engineering" in cv_input.objective

        # Experience
        assert len(cv_input.experience) == 2
        exp1 = cv_input.experience[0]
        assert "FPT Software" in exp1.company
        assert "Senior Backend Developer" in exp1.title
        assert len(exp1.highlights) == 2
        assert "15k requests per second" in exp1.highlights[0]

        # Projects
        assert len(cv_input.projects) >= 1
        assert "E-commerce Microservices" in cv_input.projects[0].name

        # Education
        assert len(cv_input.education) == 1
        assert "Hanoi University of Science and Technology" in cv_input.education[0].institution

        # Achievements & Interests
        assert len(cv_input.achievements) >= 1
        assert len(cv_input.interests) >= 1

    def test_parse_markdown_missing_name_raises(self):
        bad_markdown = "## Experience\n- Some bullet"
        with pytest.raises(ValueError, match="Could not extract candidate name"):
            parse_markdown_to_cv_input(bad_markdown)

    def test_load_cv_input_from_text_auto_detects(self):
        from src.yaml_layer.io import load_cv_input_from_text

        # Test Markdown
        cv_md = load_cv_input_from_text(SAMPLE_MARKDOWN_CV)
        assert cv_md.name == "Nguyen Van A"
        assert len(cv_md.experience) == 2

        # Test YAML
        sample_yaml = """
name: Le Thi C
position: Data Analyst
objective: Data enthusiast with SQL and Python skills.
experience:
  - company: ABC Data
    title: Analyst
    start: "2022"
    highlights: ["Created automated BI reports"]
education:
  - institution: National Economics University
    degree: B.S. Economics
"""
        cv_yaml = load_cv_input_from_text(sample_yaml)
        assert cv_yaml.name == "Le Thi C"
        assert cv_yaml.position == "Data Analyst"
