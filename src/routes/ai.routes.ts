// src/routes/ai.routes.ts
import { Body, Controller, Header, Inject, Post, Res } from '@nestjs/common';
import { Response } from 'express';
import type { AIModelClient, AiContext } from '../core/model-client.interface';

/**
 * SSE endpoint – accepts a POST body with full context so the AI can produce
 * accurate, personalised responses.
 *
 * Body shape (AiContext):
 *   prompt    – user's question / instruction (required)
 *   cvYaml    – current CV YAML (optional but strongly recommended)
 *   jd        – target job description (optional)
 *   language  – reply language, e.g. "vi" | "en" (optional, default "en")
 *   history   – prior conversation messages for multi-turn memory (optional)
 */
@Controller('v1/ai')
export class AiController {
  constructor(
    @Inject('AI_MODEL_CLIENT') private readonly aiClient: AIModelClient,
  ) {}

  @Post('stream-generate')
  @Header('Content-Type', 'text/event-stream')
  async streamGenerate(@Body() ctx: AiContext, @Res() res: Response) {
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.flushHeaders();

    const send = (event: string, data: unknown) => {
      res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    };

    try {
      // Step 1 – Analyse JD with full context
      send('progress', { step: 'jd-analysis', message: 'Analyzing job description...' });
      const analysis = await this.aiClient.analyzeJd(ctx);
      send('partial', { content: analysis.summary });

      // Step 2 – Generate experience section with full context
      send('progress', { step: 'experience', message: 'Generating experience section...' });
      const expResult = await this.aiClient.generateExperience(analysis, ctx);
      send('partial', { content: expResult.yaml });

      send('done', { final: expResult.fullCvYaml });
    } catch (err) {
      console.error('AI stream error', err);
      send('error', { message: 'AI generation failed' });
    } finally {
      res.end();
    }
  }
}
