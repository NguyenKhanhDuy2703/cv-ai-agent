# cv-ai-agent

Autonomous AI Agent Service for Intelligent CV Creation & Optimization (YAML in → YAML out).

`cv-ai-agent` là một AI microservice độc lập (headless), được xây dựng bằng **Python (FastAPI + Pydantic v2)** nhằm phục vụ quy trình tự động hóa viết lại và tối ưu CV theo chuẩn STAR, phát hiện xung đột dữ liệu, chống bịa đặt (Anti-hallucination) và stream kết quả thời gian thực qua Server-Sent Events (SSE).

Chi tiết thiết kế và lộ trình phát triển được lưu tại [docs/proposal.md](docs/proposal.md).

---

## Kiến trúc hệ thống

```
                      ┌───────────────────────────────────────────────┐
                      │                 Clients                       │
                      │ (RenderCV Web, Telegram Bot, Chrome Extension)│
                      └──────────────────────┬────────────────────────┘
                                             │ HTTP POST / SSE
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │                  cv-ai-agent                  │
                      │             (Port 8001 / FastAPI)             │
                      ├───────────────────────────────────────────────┤
                      │ • JD Analyzer Agent (ATS keywords extraction) │
                      │ • Industry RAG Engine (Architecture, IT, Mkt) │
                      │ • CV Synthesizer (Anti-hallucination, STAR)   │
                      │ • Schema Guard (Pydantic / YAML Validator)    │
                      └──────────────────────┬────────────────────────┘
                                             │ Model-Agnostic
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │              LLM Providers                    │
                      │ (Google Gemini, OpenAI GPT, Anthropic Claude) │
                      └───────────────────────────────────────────────┘
```

---

## Tính năng cốt lõi

- **Python & FastAPI**: Hiệu năng cao, async ASGI native, Pydantic v2 validation nhanh và sinh schema chuẩn.
- **Model-Agnostic LLM Provider**: Linh hoạt chuyển đổi Google Gemini, OpenAI hoặc local engine qua biến môi trường.
- **Real-Time Streaming (SSE)**: Truyền tải tiến trình, câu hỏi phỏng vấn, và patch YAML từng phần qua Server-Sent Events.
- **Anti-Hallucination Policy**: Kiểm tra bằng code (regex số liệu, ngày tháng, tên riêng) đảm bảo không bịa đặt số liệu không có trong nguồn.
- **YAML in → YAML out**: Nhận dữ liệu CV có cấu trúc cùng thông tin Bonus, xuất CV YAML sạch và báo cáo thay đổi `report.yaml`.
- **Industry Specialization**: Khe cắm plugin tri thức ngành (MVP để rỗng theo thiết kế).

---

## Cấu trúc thư mục

```
cv-ai-agent/
├── docs/
│   └── proposal.md       # Tài liệu Proposal chi tiết
├── src/
│   ├── api/              # FastAPI app, routers, SSE streaming, middleware
│   │   ├── routes.py
│   │   └── server.py
│   ├── config.py         # Pydantic Settings đọc .env
│   ├── core/             # AI client abstraction & Core client
│   │   ├── model_client.py
│   │   └── core_ai_client.py
│   ├── guard/            # Luật chống bịa (Anti-hallucination guard)
│   │   └── anti_hallucination.py
│   ├── industry/         # Plugin tri thức ngành (khe cắm RAG)
│   │   └── context.py
│   ├── pipeline/         # Pipeline 9 bước xử lý CV
│   │   └── orchestrator.py
│   ├── schemas/          # Pydantic models (CV, SSE Events, Context, Proposal)
│   │   ├── context.py
│   │   ├── cv.py
│   │   ├── events.py
│   │   └── proposal.py
│   └── main.py           # Entrypoint khởi chạy server
├── tests/
│   └── test_api_and_schemas.py
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Hướng dẫn cài đặt & Chạy

### 1. Yêu cầu môi trường
- Python >= 3.11 (khuyến nghị Python 3.12 hoặc 3.13)
- `pip` hoặc `uv`

### 2. Cài đặt thư viện
```bash
# Tạo môi trường ảo (khuyến nghị)
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên Linux/macOS:
source .venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
```

```env
AI_PORT=8001
FRONTEND_ORIGIN=http://localhost:5173
AI_PROVIDER=core
AI_API_KEY=your_api_key_here
AI_API_URL=
AI_MODEL=
```

### 4. Khởi chạy dịch vụ
```bash
# Chạy qua entrypoint
python -m src.main

# Hoặc chạy trực tiếp với uvicorn (hỗ trợ hot-reload)
uvicorn src.api.server:app --host 0.0.0.0 --port 8001 --reload
```

Server sẽ sẵn sàng tại `http://localhost:8001`. Tài liệu OpenAPI Swagger có tại `http://localhost:8001/docs`.

---

## API Endpoints

### 1. Stream Generation / Chat
* **Route:** `POST /v1/ai/stream-generate`
* **Content-Type:** `application/json`
* **Response:** `text/event-stream` (SSE)
* **Body mẫu:**
```json
{
  "prompt": "Create experience section for a Junior Architect",
  "cvYaml": "cv:\n  name: Nguyen Van A...",
  "jdText": "Looking for Junior Architect proficient in Revit and AutoCAD...",
  "language": "vi"
}
```

### 2. Health Check
* **Route:** `GET /health`
* **Response:** `{"status": "ok", "provider": "core"}`

---

## Kiểm thử
```bash
pytest tests/
```

---

## License
MIT
