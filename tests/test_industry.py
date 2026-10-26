"""
Tests for Industry Context RAG packs (src/industry/context.py).
"""
import pytest
from src.industry.context import get_industry_context


class TestIndustryContext:
    def test_default_empty_when_no_industry_provided(self):
        assert get_industry_context(None) == ""
        assert get_industry_context("") == ""

    def test_it_software_pack_loaded(self):
        ctx = get_industry_context("it_software")
        assert ctx != ""
        assert "Microservices" in ctx or "software" in ctx.lower()
        assert "Action Verbs" in ctx or "action verbs" in ctx.lower()

    def test_architecture_bim_pack_loaded(self):
        ctx = get_industry_context("architecture_bim")
        assert ctx != ""
        assert "BIM" in ctx or "Revit" in ctx

    def test_normalization_and_aliases(self):
        # Case insensitive and hyphen/underscore normalization
        assert get_industry_context("IT-Software") != ""
        assert get_industry_context("it") != ""
        assert get_industry_context("architecture") != ""

    def test_unknown_industry_returns_empty(self):
        assert get_industry_context("unknown_nonexistent_field_123") == ""
