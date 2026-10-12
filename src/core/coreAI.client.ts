// src/core/coreAI.client.ts
import { Injectable } from '@nestjs/common';
import type { AIModelClient, AiContext } from './model-client.interface';

/**
 * Default AI client.
 * Replace the mock bodies with real HTTP/SDK calls to whichever LLM you choose.
 * All credentials come from environment variables – no hard-coded values.
 *
 * The key responsibility of this client is to BUILD A RICH SYSTEM PROMPT
 * that gives the model all the context it needs to respond correctly.
 */
@Injectable()
export class CoreAIClient implements AIModelClient {
  private readonly apiKey = process.env.AI_API_KEY;
  private readonly apiUrl = process.env.AI_API_URL;
  private readonly model = process.env.AI_MODEL;

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * Builds the system-level prompt that frames the model's role and context.
   * The richer this is, the more accurate and relevant the AI responses will be.
   */
  private buildSystemPrompt(ctx: AiContext): string {
    const lang = ctx.language ?? 'en';
    const lines: string[] = [
      `You are an expert CV/Resume writer and career coach.`,
      `Always reply in language code: "${lang}".`,
      `Your goal is to help the user improve their CV to match the target job.`,
    ];

    if (ctx.cvYaml) {
      lines.push(
        `\n--- CURRENT CV (YAML) ---\n${ctx.cvYaml}\n--- END CV ---`,
      );
    }

    if (ctx.jd) {
      lines.push(
        `\n--- TARGET JOB DESCRIPTION ---\n${ctx.jd}\n--- END JD ---`,
      );
    }

    if (ctx.history && ctx.history.length > 0) {
      const historyText = ctx.history
        .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.text}`)
        .join('\n');
      lines.push(`\n--- CONVERSATION HISTORY ---\n${historyText}\n--- END HISTORY ---`);
    }

    lines.push(`\nNow respond to the user's latest message: "${ctx.prompt}"`);
    return lines.join('\n');
  }

  // ---------------------------------------------------------------------------
  // AIModelClient implementation
  // ---------------------------------------------------------------------------

  async analyzeJd(ctx: AiContext): Promise<{ summary: string }> {
    const systemPrompt = this.buildSystemPrompt(ctx);

    // TODO: replace with real HTTP call using this.apiKey / this.apiUrl / this.model
    console.log('[CoreAIClient] System prompt built:\n', systemPrompt);

    return new Promise((resolve) =>
      setTimeout(() => {
        resolve({
          summary: `[Mock] Analyzed JD for prompt: "${ctx.prompt}" (cv length: ${ctx.cvYaml?.length ?? 0} chars)`,
        });
      }, 300),
    );
  }

  async generateExperience(
    analysis: { summary: string },
    ctx: AiContext,
  ): Promise<{ yaml: string; fullCvYaml: string }> {
    // TODO: pass analysis + ctx into a real LLM call
    return new Promise((resolve) =>
      setTimeout(() => {
        const yaml = `experience:\n  - company: Example Corp\n    role: Engineer\n    period: "2020-2023"\n    # Based on: ${analysis.summary}`;
        resolve({ yaml, fullCvYaml: `cv:\n  ${yaml}` });
      }, 500),
    );
  }
}
