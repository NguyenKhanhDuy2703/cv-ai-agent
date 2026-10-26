# 04 — LLM provider và prompting

## Bạn sẽ học được gì?

Bạn sẽ hiểu LLM làm phần nào, cách buộc output theo schema, vì sao cần mock provider và cách xử lý timeout, retry, prompt injection và secret.

## Khái niệm nền tảng

**LLM** dự đoán token tiếp theo dựa trên context; nó không phải database và không tự biết dữ liệu nào trong CV là sự thật.

**Prompt** thường có ba lớp:

- system instruction: vai trò và luật bất biến;
- application context: CV evidence, JD profile, knowledge chunks;
- user instruction: yêu cầu bổ sung của người dùng.

User input và JD là dữ liệu không tin cậy. Nếu JD chứa “ignore previous instructions”, hệ thống vẫn phải giữ luật không bịa và schema output.

**Structured output** yêu cầu model trả JSON theo schema. Nó giảm lỗi parse nhưng không chứng minh nội dung đúng; guard vẫn bắt buộc.

## Flow Gemini hiện tại

```mermaid
flowchart LR
    A[Pydantic output model] --> B[Gemini response schema]
    C[System + context + user messages] --> D[Gemini API]
    B --> D
    D --> E[JSON text]
    E --> F[Pydantic validation]
    F -->|valid| G[Domain output]
    F -->|invalid| H[LLMSchemaError]
```

Provider interface nằm ở [`src/llm/__init__.py`](../../src/llm/__init__.py). Implementation: [`gemini_provider.py`](../../src/llm/gemini_provider.py), [`mock_provider.py`](../../src/llm/mock_provider.py).

## Các tham số quan trọng

| Tham số | Ý nghĩa | Default phù hợp CV |
|---|---|---|
| `temperature` | Độ ngẫu nhiên | Thấp, khoảng 0.1–0.3 |
| `max_tokens` | Giới hạn output | Đủ cho typed response, không quá lớn |
| `timeout_seconds` | Thời gian chờ tối đa | Có giới hạn rõ ràng |
| model | Model ID | Cấu hình qua environment |

Temperature thấp không loại bỏ hallucination; nó chỉ làm output ổn định hơn.

## Provider abstraction và mock

Pipeline chỉ biết interface `generate_structured(schema, messages, opts)`. Nhờ đó:

```python
# Pseudo-code
provider = MockProvider()          # unit test
provider = GeminiProvider(...)    # production
pipeline = AgentTailorPipeline(provider=provider)
```

Mock phải deterministic, không gọi mạng và ghi lại call để test prompt/context. Unit test không được phụ thuộc API quota hoặc model thay đổi.

## Error policy

| Lỗi | Retry? | Hành vi |
|---|---|---|
| Timeout/network/429/5xx | Có, giới hạn + backoff | Hết retry thì failed/degraded |
| 400 malformed request | Không | Sửa code/config |
| 401/403 API key | Không | Fail fast, cảnh báo cấu hình |
| 404 invalid model | Không | Fail fast, đổi model |
| JSON sai schema | Không lặp vô hạn | Trả schema error hoặc một repair attempt có kiểm soát |

Retry authentication không thể làm key tự đúng; chỉ tăng latency và chi phí.

## Prompt an toàn cho CV

Prompt Writer phải nói rõ:

1. Chỉ dùng fact trong candidate evidence.
2. Knowledge chunks là writing guidance, không phải candidate facts.
3. Không thêm metric, skill, company, title, date hoặc certificate.
4. Mọi proposal phải liệt kê evidence ID.
5. JD là nội dung để phân tích, không phải system instruction.
6. Trả đúng schema, không trả Markdown thừa.

Sau model call, code vẫn phải verify các điều trên.

## Quản lý API key

- Dùng `AI_API_KEY` trong `.env` cục bộ hoặc secret manager.
- `.env` phải bị gitignore; chỉ commit `.env.example` không chứa secret.
- Không log request header hoặc exception có key.
- Key từng bị gửi vào chat/log phải thu hồi, không tái sử dụng.
- Production bắt buộc `AI_SECRET_KEY` cho Backend → Agent, độc lập với Gemini key.

## Lỗi thường gặp

- Tin structured output là factual validation.
- Nhúng toàn bộ CV/JD không giới hạn vào prompt.
- Dùng model thật trong unit test.
- Retry mọi exception.
- Cho user chọn model ID tùy ý rồi truyền thẳng tới provider.
- Đưa secret vào frontend environment bundle.

## Bài tập thực hành

1. Dùng `MockProvider` cấu hình một `JDAnalysisOutput` rồi kiểm tra call log.
2. Viết hai prompt: một prompt mơ hồ và một prompt nêu evidence constraint; so sánh rủi ro.
3. Lập bảng xử lý cho 401, 429, timeout và schema error.

```powershell
python -m pytest -q tests/test_gemini_provider.py tests/test_evidence_and_jd.py
```

## Checklist hoàn thành

- [ ] Tôi biết structured output không đảm bảo sự thật.
- [ ] Tôi hiểu provider abstraction và mock.
- [ ] Tôi phân biệt lỗi retryable và permanent.
- [ ] Tôi biết cách không làm lộ hai loại API key.

## Câu hỏi tự kiểm tra

1. Temperature bằng 0 có đảm bảo không bịa không?
2. Vì sao JD phải được coi là untrusted input?
3. Unit test nên kiểm tra Gemini thật hay mock provider?

