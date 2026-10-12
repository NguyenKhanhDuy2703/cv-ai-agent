

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export interface AiContext {
  prompt: string;
  cvYaml?: string;
  jd?: string;
  language?: string;
  history?: ChatMessage[];
}

export interface AIModelClient {
  analyzeJd(context: AiContext): Promise<{ summary: string }>;
  generateExperience(
    analysis: { summary: string },
    context: AiContext,
  ): Promise<{ yaml: string; fullCvYaml: string }>;
}
