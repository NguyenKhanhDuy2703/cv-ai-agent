// packages/cv-contracts/src/ai.ts
//
// AI Contract – Single source of truth cho:
//   1. cvAiJsonSchema  → JSON Schema (chỉ phần cv + sections) nhúng vào system prompt
//   2. AiRequestContext → Format INPUT FE gửi lên MODULE_AI
//   3. AiResponseEvent  → Format OUTPUT MODULE_AI stream về FE
//
// Cả FE và MODULE_AI đều import từ đây → không bao giờ lệch nhau.

import { z } from 'zod';

// ---------------------------------------------------------------------------
// 1. CV-only JSON Schema (dùng nhúng vào AI system prompt)
//    Chỉ lấy phần `cv` – bỏ design / locale / settings để tiết kiệm token.
// ---------------------------------------------------------------------------

/** Zod schema chỉ cho phần cv (sections + header) – dùng để validate output AI */
const entrySchema = z.discriminatedUnion('type', [
  z.object({ id: z.string(), type: z.literal('Text'), text: z.string() }),
  z.object({
    id: z.string(),
    type: z.literal('Experience'),
    company: z.string(),
    position: z.string(),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    date: z.string().optional(),
    location: z.string().optional(),
    summary: z.string().optional(),
    highlights: z.array(z.string()),
  }),
  z.object({
    id: z.string(),
    type: z.literal('Education'),
    institution: z.string(),
    area: z.string(),
    degree: z.string(),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    date: z.string().optional(),
    location: z.string().optional(),
    summary: z.string().optional(),
    highlights: z.array(z.string()),
  }),
  z.object({
    id: z.string(),
    type: z.literal('Normal'),
    name: z.string(),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    date: z.string().optional(),
    location: z.string().optional(),
    summary: z.string().optional(),
    highlights: z.array(z.string()),
  }),
  z.object({
    id: z.string(),
    type: z.literal('Publication'),
    title: z.string(),
    authors: z.array(z.string()),
    journal: z.string(),
    date: z.string().optional(),
    doi: z.string().optional(),
    url: z.string().optional(),
    summary: z.string().optional(),
  }),
  z.object({ id: z.string(), type: z.literal('One-Line'), label: z.string(), details: z.string() }),
  z.object({ id: z.string(), type: z.literal('Bullet'), bullet: z.string() }),
  z.object({ id: z.string(), type: z.literal('Numbered'), text: z.string(), number: z.number().optional() }),
  z.object({ id: z.string(), type: z.literal('Reversed Numbered'), text: z.string(), number: z.number().optional() }),
]);

const cvAiSchema = z.object({
  name: z.string(),
  headline: z.string(),
  email: z.string(),
  phone: z.string().optional(),
  location: z.string().optional(),
  website: z.string().optional(),
  photo_url: z.string().optional(),
  social_networks: z.array(
    z.object({ id: z.string(), network: z.string(), username: z.string() }),
  ).optional(),
  sections: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      entryType: z.enum([
        'Text', 'Experience', 'Education', 'Publication',
        'One-Line', 'Bullet', 'Numbered', 'Reversed Numbered', 'Normal',
      ]),
      entries: z.array(entrySchema),
    }),
  ),
});

export type CvAiData = z.infer<typeof cvAiSchema>;

/** JSON Schema (OpenAPI 3.0) chỉ phần cv – nhúng thẳng vào AI system prompt */
export const cvAiJsonSchema = z.toJSONSchema(cvAiSchema, {
  io: 'output',           // AI tạo ra (output), không phải parse vào
  target: 'openapi-3.0', // LLM hiểu format này tốt nhất
  unrepresentable: 'any', // Không crash khi gặp type không map được
});

/** Validate YAML output của AI (chỉ phần cv) trước khi gửi về FE */
export function validateAiCvOutput(value: unknown): {
  success: boolean;
  data?: CvAiData;
  errors?: string[];
} {
  const result = cvAiSchema.safeParse(value);
  if (result.success) return { success: true, data: result.data };
  return {
    success: false,
    errors: result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
  };
}

// ---------------------------------------------------------------------------
// 2. AI Request Context – INPUT format (FE → MODULE_AI)
// ---------------------------------------------------------------------------

export interface AiChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

/**
 * Toàn bộ context FE gửi lên AI mỗi lần user nhắn tin.
 * MODULE_AI đọc từ đây để build system prompt.
 */
export interface AiRequestContext {
  /** Câu hỏi / lệnh của user */
  prompt: string;
  /** CV YAML hiện tại (chỉ phần `cv:`) – AI đọc để biết user đang có gì */
  cvYaml?: string;
  /** Job description muốn nhắm tới – AI dùng để tailor gợi ý */
  jd?: string;
  /** Ngôn ngữ trả lời: "vi" | "en" | ... */
  language?: string;
  /** Lịch sử hội thoại để AI nhớ context multi-turn */
  history?: AiChatMessage[];
  /** Phase hiện tại của conversation flow */
  phase?: AiConversationPhase;
}

export type AiConversationPhase =
  | 'intro'        // Phase 0: Mục tiêu / JD
  | 'personal'     // Phase 1: Thông tin cá nhân
  | 'experience'   // Phase 2: Kinh nghiệm làm việc
  | 'education'    // Phase 3: Học vấn
  | 'projects'     // Phase 4: Projects / Skills / Certifications
  | 'review';      // Phase 5: Review & fill gaps

// ---------------------------------------------------------------------------
// 3. AI Response Events – OUTPUT format (MODULE_AI → FE)
//    AI stream về FE dưới dạng SSE, mỗi event là một trong 4 loại dưới đây.
// ---------------------------------------------------------------------------

/** AI đang hỏi thêm thông tin về một field cụ thể */
export interface AiQuestionEvent {
  type: 'question';
  phase: AiConversationPhase;
  question: string;
  /** JSON path của field đang hỏi, vd: "sections[0].entries[0].highlights" */
  field?: string;
  /** true nếu user có thể bỏ qua */
  optional: boolean;
}

/** AI đã thu thập đủ data để cập nhật một phần CV – FE apply vào store ngay */
export interface AiPartialUpdateEvent {
  type: 'partial_update';
  phase: AiConversationPhase;
  /** Mô tả ngắn gọn vừa làm gì */
  message: string;
  /** YAML patch cho tab 'cv' – FE parse và merge vào document store */
  yamlPatch: {
    tab: 'cv';
    /** YAML string hợp lệ, FE dùng parseTabYaml() để parse */
    yaml: string;
  };
}

/** AI phát hiện thiếu thông tin quan trọng – liệt kê và hỏi user */
export interface AiGapReportEvent {
  type: 'gap_report';
  gaps: Array<{
    field: string;
    message: string;
    severity: 'required' | 'recommended';
  }>;
  question: string;
}

/** AI hoàn thành – trả về full CV YAML để FE apply */
export interface AiDoneEvent {
  type: 'done';
  message: string;
  /** Full cv: YAML string – FE parse bằng parseTabYaml(yaml, 'cv') */
  cvYaml: string;
}

/** Union tất cả event types AI có thể stream */
export type AiResponseEvent =
  | AiQuestionEvent
  | AiPartialUpdateEvent
  | AiGapReportEvent
  | AiDoneEvent;

// ---------------------------------------------------------------------------
// Zod schemas để validate AiResponseEvent (FE có thể dùng để type-safe parse)
// ---------------------------------------------------------------------------
export const aiResponseEventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('question'),
    phase: z.enum(['intro', 'personal', 'experience', 'education', 'projects', 'review']),
    question: z.string(),
    field: z.string().optional(),
    optional: z.boolean(),
  }),
  z.object({
    type: z.literal('partial_update'),
    phase: z.enum(['intro', 'personal', 'experience', 'education', 'projects', 'review']),
    message: z.string(),
    yamlPatch: z.object({ tab: z.literal('cv'), yaml: z.string() }),
  }),
  z.object({
    type: z.literal('gap_report'),
    gaps: z.array(z.object({
      field: z.string(),
      message: z.string(),
      severity: z.enum(['required', 'recommended']),
    })),
    question: z.string(),
  }),
  z.object({
    type: z.literal('done'),
    message: z.string(),
    cvYaml: z.string(),
  }),
]);
