import asyncio
import logging
from typing import List
from ..config import settings
from ..schemas.context import AiRequestContext
from .model_client import AIModelClient, JdAnalysisResult, ExperienceResult

logger = logging.getLogger(__name__)


class CoreAIClient(AIModelClient):
    """
    Default AI client implementation.
    Reads credentials from settings.
    Builds rich system prompt for LLM and handles generation.
    """

    def __init__(self):
        self.api_key = settings.ai_api_key
        self.api_url = settings.ai_api_url
        self.model = settings.ai_model
        self.provider = settings.ai_provider

    def build_system_prompt(self, ctx: AiRequestContext) -> str:
        lang = ctx.language or "en"
        lines: List[str] = [
            "You are an expert CV/Resume writer and career coach.",
            f'Always reply in language code: "{lang}".',
            "Your goal is to help the user improve their CV to match the target job.",
        ]

        if ctx.cvYaml:
            lines.append(f"\n--- CURRENT CV (YAML) ---\n{ctx.cvYaml}\n--- END CV ---")

        if ctx.jd:
            lines.append(f"\n--- TARGET JOB DESCRIPTION ---\n{ctx.jd}\n--- END JD ---")

        if ctx.history:
            history_text = "\n".join(
                f"{'User' if m.role == 'user' else 'Assistant'}: {m.text}"
                for m in ctx.history
            )
            lines.append(f"\n--- CONVERSATION HISTORY ---\n{history_text}\n--- END HISTORY ---")

        lines.append(f'\nNow respond to the user\'s latest message: "{ctx.prompt}"')
        return "\n".join(lines)

    async def analyze_jd(self, context: AiRequestContext) -> JdAnalysisResult:
        system_prompt = self.build_system_prompt(context)
        logger.info("[CoreAIClient] System prompt built for analyze_jd (length %d)", len(system_prompt))

        # Simulation or LLM call hook
        await asyncio.sleep(0.3)
        cv_len = len(context.cvYaml) if context.cvYaml else 0
        return JdAnalysisResult(
            summary=f'[CoreAI] Analyzed JD for prompt: "{context.prompt}" (cv length: {cv_len} chars)'
        )

    async def generate_experience(
        self, analysis: JdAnalysisResult, context: AiRequestContext
    ) -> ExperienceResult:
        await asyncio.sleep(0.5)
        yaml_content = (
            "experience:\n"
            "  - company: Example Corp\n"
            "    role: Senior Engineer\n"
            '    period: "2020-2023"\n'
            f"    # Based on: {analysis.summary}"
        )
        return ExperienceResult(
            yaml=yaml_content,
            fullCvYaml=f"cv:\n  {yaml_content}",
        )
