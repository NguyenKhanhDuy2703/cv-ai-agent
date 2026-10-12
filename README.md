# cv-ai-agent

Autonomous AI Agent Service for Intelligent CV Creation & Optimization.

`cv-ai-agent` is an independent, headless AI microservice designed to power automated CV creation pipelines, real-time CV copilot chatbots, and ATS keyword optimization. It is built to serve multiple clients across platforms (Web, Mobile, Telegram/Zalo, Chrome Extensions, and B2B APIs).

---

## Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │                 Clients                       │
                      │ (RenderCV Web, Telegram Bot, Chrome Extension)│
                      └──────────────────────┬────────────────────────┘
                                             │ HTTP POST / SSE
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │                  cv-ai-agent                  │
                      │               (Port 8001 / NestJS)            │
                      ├───────────────────────────────────────────────┤
                      │ • JD Analyzer Agent (ATS keywords extraction) │
                      │ • Industry RAG Engine (Architecture, IT, Mkt) │
                      │ • CV Synthesizer (Anti-hallucination, STAR)   │
                      │ • Schema Guard (RenderCV YAML Validator)      │
                      └──────────────────────┬────────────────────────┘
                                             │ Model-Agnostic
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │              LLM Providers                    │
                      │ (Google Gemini, OpenAI GPT, Anthropic Claude) │
                      └───────────────────────────────────────────────┘
```

---

## Features

- **Model-Agnostic LLM Provider**: Easily switch between Google Gemini, OpenAI, or local engines via environment variables.
- **Real-Time Streaming**: Delivers progress, questions, and YAML partial updates via Server-Sent Events (SSE).
- **Anti-Hallucination Policy**: Enforces factual constraints based solely on verified user input, elevating wording with strong action verbs.
- **RenderCV Schema Compliance**: Generates valid YAML matching the RenderCV standard specification.
- **Industry Specialization (RAG)**: Incorporates domain-specific knowledge (e.g., Architecture, Software Engineering, Marketing).

---

## Getting Started

### 1. Prerequisites
- Node.js >= 20.0.0
- npm >= 9.0.0

### 2. Installation
```bash
npm install
```

### 3. Configuration
Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```

```env
AI_PORT=8001
FRONTEND_ORIGIN=http://localhost:5173
AI_PROVIDER=core
AI_API_KEY=your_api_key_here
```

### 4. Running the Service
```bash
# Development mode with hot-reload
npm run dev

# Production build and run
npm run build
npm start
```

---

## API Endpoints

### 1. Stream Generation / Chat
* **Route:** `POST /v1/ai/stream-generate`
* **Content-Type:** `application/json`
* **Response:** `text/event-stream` (SSE)
* **Body:**
```json
{
  "prompt": "Create experience section for a Junior Architect",
  "cvYaml": "cv:\n  name: Nguyen Van A...",
  "jdText": "Looking for Junior Architect proficient in Revit and AutoCAD...",
  "language": "vi"
}
```

---

## License
MIT
