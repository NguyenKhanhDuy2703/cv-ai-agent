"""Test-only providers, explicitly injected. Never selectable by production config."""
import re

from src.core.experience_writer import ExperienceRewriteProposals
from src.core.jd_analyzer import JDAnalysisOutput
from src.pipeline.generation import CvGenerationPipeline
from src.schemas.generation import GeneratedProject, GeneratedSummary


class FakeProvider:
    def __init__(self, *, errors=None):
        self.responses = {}
        self.errors = errors or {}
        self.calls = []

    def set_response(self, schema, response):
        self.responses[schema] = response

    async def generate_structured(self, schema, messages, opts=None):
        self.calls.append(schema)
        if schema in self.errors:
            raise self.errors[schema]
        if schema in self.responses:
            return self.responses[schema]
        if schema is JDAnalysisOutput:
            return JDAnalysisOutput(role_family="Backend Engineering", seniority="Senior",
                                    required_skills=["Python"], keywords=["Python", "REST"])
        if schema is ExperienceRewriteProposals:
            return ExperienceRewriteProposals(proposals=[])
        text = messages[-1]["content"]
        items = re.findall(r"^\[([^\]]+)\] (.+)$", text.split("GUIDANCE:")[0], re.MULTILINE)
        if schema is GeneratedSummary:
            return GeneratedSummary(text=" ".join(value for _, value in items[:3]),
                                    evidenceIds=[key for key, _ in items[:3]])
        if schema is GeneratedProject:
            source_id = re.search(r"Source ID: (.+)", text).group(1)
            item = max(items, key=lambda pair: len(pair[1]))
            return GeneratedProject(sourceId=source_id, highlights=[item[1]], evidenceIds=[item[0]])
        raise AssertionError(f"Test provider has no response for {schema.__name__}")


def make_pipeline(**kwargs):
    return CvGenerationPipeline(provider=FakeProvider(), **kwargs)
