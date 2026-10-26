# Proposal: CV Tailor Agent (YAML in → YAML out)

| | |
|---|---|
| **Phiên bản** | 0.2 (Draft) |
| **Ngày** | 2026-10-12 |
| **Trạng thái** | Đã chốt các quyết định ở mục 0; còn các câu `[?]` ở mục 10 |
| **Quy ước** | `[GIẢ ĐỊNH]` = tôi tự suy ra, cần bạn xác nhận. `[?]` = câu hỏi mở, xem mục 10 |

---

## 0. Quyết định đã chốt (từ phiên hỏi đáp 2026-10-12)

| # | Chủ đề | Quyết định | Nguồn |
|---|---|---|---|
| 1 | Người dùng | **Công khai** (web app / bot) | Bạn chọn |
| 2 | Định dạng Core | **Schema riêng**, chỉ lấy ý tưởng từ RenderCV: dùng YAML, kiến trúc tương tự (khối `cv` + `sections`). Không bắt buộc hợp lệ với RenderCV | Bạn chọn |
| 3 | Nhập Bonus | **Các ô tách riêng** (ghi chú, chỉ dẫn, tham chiếu; ghi chú có thể gắn vào mục CV) | Bạn chọn |
| 4 | Xung đột / mơ hồ | **Chạy tiếp, ghi vào báo cáo**, không dừng hỏi (chế độ hỏi lại để sau) | Bạn chọn |
| 5 | Ngành | **Chưa gắn ngành cụ thể.** Lõi chạy theo quy tắc chung. Industry/RAG là một khe cắm **để rỗng** ở MVP; sau này nạp tri thức theo kinh nghiệm từng ngành | Bạn chọn |
| 6 | Ngôn ngữ CV | **Người dùng chọn `locale` (vi/en) mỗi lần chạy** | `[GIẢ ĐỊNH]` mặc định, bạn chưa có ý kiến |
| 7 | Mức viết lại | **Viết lại theo STAR**: đổi cấu trúc câu, thêm ngữ cảnh/kết quả chỉ khi có trong dữ liệu; **giữ số lượng bullet**. Tái cấu trúc tự do là tùy chọn sau | `[GIẢ ĐỊNH]` mặc định |
| 8 | Stack lõi | **Python** (FastAPI, Pydantic; xem mục 11) | Bạn chọn (đã chuyển từ TypeScript sang Python) |

### Hệ quả của việc công khai (bổ sung vào yêu cầu)

- **Dữ liệu cá nhân (PII):** CV chứa tên, email, điện thoại. Không ghi nội dung CV vào log; xác định thời gian lưu giữ (mặc định: không lưu sau khi trả kết quả).
- **Chống prompt injection:** Bonus, JD và mọi chuỗi người dùng nhập là **dữ liệu, không phải mệnh lệnh**. Chỉ ô "chỉ dẫn" mới được coi là yêu cầu, và vẫn bị giới hạn bởi quy tắc cứng. Chuỗi nhập phải được đưa vào prompt trong khối dữ liệu có ranh giới rõ.
- **Giới hạn chi phí:** giới hạn kích thước đầu vào, số bullet, số vòng retry, số lần gọi mỗi người dùng; có rate limit.
- **Xác thực:** API key hoặc đăng nhập trước khi gọi agent.
- **Độ tin cậy:** timeout, retry, trả lỗi rõ ràng; lỗi LLM không được làm hỏng CV gốc (nếu một bullet thất bại, giữ nguyên bullet gốc và ghi vào báo cáo).
- **Khe cắm RAG rỗng:** pipeline gọi `get_industry_context(industry)` ở bước chọn lọc/viết lại; MVP trả về rỗng. Khi có tri thức ngành chỉ cần nạp dữ liệu, không sửa lõi.

---

## 1. Bối cảnh và vấn đề

Người dùng thường có sẵn thông tin về bản thân nhưng CV của họ:

- viết chung chung, không khớp với từng tin tuyển dụng (JD);
- thiếu những thông tin họ biết nhưng chưa kịp ghi vào CV (dự án, kết quả, công cụ);
- không tối ưu cho hệ thống lọc CV tự động (ATS).

Các công cụ AI hiện có thường có hai lỗi: **bịa kinh nghiệm** để cho khớp JD, và **trả về định dạng không dùng tiếp được** (phải copy-paste, sửa tay).

**Vấn đề cần giải:** nhận dữ liệu CV có cấu trúc cùng thông tin bổ sung của người dùng, tạo ra CV đã được viết lại cho phù hợp mục tiêu, **đúng sự thật**, ở định dạng YAML có thể render ngay.

---

## 2. Mục tiêu và ngoài phạm vi

### Mục tiêu

1. Nhận **YAML** (Core + Bonus) và trả về **YAML** CV hợp lệ, render được ngay.
2. Viết lại câu chữ theo hướng STAR/định lượng, bám theo JD khi có JD.
3. **Không bịa**: mọi số liệu, tên riêng, sự kiện trong đầu ra phải truy được về đầu vào.
4. Cho người dùng thấy AI đã đổi gì, dựa vào đâu, còn thiếu gì (báo cáo).
5. Linh hoạt: thêm ngành, thêm section, đổi LLM mà không sửa lõi.

### Ngoài phạm vi (phiên bản đầu) `[GIẢ ĐỊNH]`

- Đọc PDF/DOCX, quét GitHub/LinkedIn (có thể là bước tiền xử lý sau này, biến mọi nguồn thành YAML đầu vào).
- Giao diện web, bot Telegram/Zalo.
- Thiết kế đồ họa CV (việc của bộ render).
- Lưu trữ tài khoản người dùng.

---

## 3. Người dùng và kịch bản `[GIẢ ĐỊNH]`

| Ai gọi agent | Cách dùng |
|---|---|
| Người dùng cuối (qua ứng dụng của bạn) | Điền form, ứng dụng đóng gói thành YAML rồi gọi agent |
| Chính bạn / dev | Chạy trực tiếp bằng file YAML để thử nghiệm |

**Kịch bản chính:** người dùng có CV cơ bản + một JD cụ thể + vài ghi chú thêm → nhận CV đã chỉnh cho JD đó.

**Kịch bản phụ:** không có JD → agent chỉ chuẩn hóa văn phong, làm CV tổng quát tốt hơn.

---

## 4. Đầu vào

Một file YAML gồm **3 vùng**, vai trò khác nhau:

| Vùng | Bản chất | In ra CV? | AI được làm gì |
|---|---|---|---|
| **Core** | Khung CV, dữ liệu có cấu trúc | Có | Chỉ viết lại câu chữ, không đổi sự kiện |
| **Bonus** | Thông tin tự do người dùng thêm | Không (chỉ làm nguyên liệu) | Đọc, rút ý, dùng làm bằng chứng |
| **Control** | Cách chạy agent | Không | Đọc để biết cần làm gì |

### 4.1 Core (CV nào cũng có)

Tiêu chí giữ lại: *thiếu nó thì không thành CV*.

- Danh tính: tên, email, điện thoại, địa điểm, link
- Tóm tắt (có thể trống)
- Kinh nghiệm: công ty, vị trí, thời gian, mô tả
- Học vấn
- Kỹ năng
- Section tùy chọn có tên bất kỳ (dự án, chứng chỉ, giải thưởng, portfolio...)

### 4.2 Bonus (nội dung thêm cho AI)

Người dùng gõ tự do, hệ thống phân thành 4 loại:

1. **Ghi chú gắn mục**: gắn với một mục Core (vd: dự án ở Công ty X).
2. **Ghi chú chung**: chưa gắn đâu (vd: giải thưởng chưa ghi vào CV).
3. **Chỉ dẫn**: mệnh lệnh, không phải sự kiện (vd: "nhấn mạnh BIM", "giọng khiêm tốn", "không nhắc công ty Y"). **Không bao giờ thành nội dung CV.**
4. **Tài liệu tham chiếu**: JD, link, mô tả dài.

### 4.3 Control

JD mục tiêu, ngôn ngữ (vi/en), ngành, danh sách path bị khóa (không được sửa), số bullet tối đa, chế độ chạy.

### 4.4 Ví dụ hình dạng `[GIẢ ĐỊNH, tên trường chưa chốt]`

```yaml
control:
  jd: "..."
  locale: vi
  industry: architecture
  locked: [education]

core:            # khung CV
  name: ...
  experience: [...]

bonus:
  notes:
    - attach_to: experience[0]     # ghi chú gắn mục
      text: "Dự án nhà ở 12 tầng, phụ trách mặt đứng"
    - text: "Giải nhì thiết kế sinh viên 2021"   # ghi chú chung
  directives:
    - "Nhấn mạnh BIM hơn concept"
  references:
    - "https://behance.net/..."
```

---

## 5. Đầu ra

| File | Nội dung |
|---|---|
| **cv.yaml** | CV mới, cùng định dạng Core, không còn Bonus/Control, render được ngay |
| **report.yaml** | Báo cáo: thay đổi, nguồn của từng câu, Bonus đã dùng/chưa dùng, cờ xung đột, từ khóa JD còn thiếu, điểm khớp |

Báo cáo tách riêng để file CV luôn sạch.

---

## 6. Flow của agent

```
Core + Bonus + Control
   │
① KIỂM TRA CORE       thiếu/sai trường bắt buộc → báo lỗi rõ ràng
② CHUẨN HÓA BONUS     phân 4 loại, tách thành các "mảnh" 1 ý
③ GẮN VÀO CORE        mảnh nào thuộc mục nào; không rõ → đánh dấu "chưa xếp"
④ PHÁT HIỆN XUNG ĐỘT  Bonus ≠ Core (vd 3 năm vs 2 năm) → gắn cờ, KHÔNG tự chọn
⑤ PHÂN TÍCH JD        từ khóa, yêu cầu, mức độ (nếu có JD)
⑥ CHỌN LỌC            mảnh/mục nào lên CV, theo JD + chỉ dẫn
⑦ VIẾT LẠI            câu mới (STAR), mỗi câu ghi nguồn
⑧ KIỂM TRA CHỐNG BỊA  số liệu, tên riêng phải có trong đầu vào; fail → viết lại (tối đa 2 vòng)
⑨ XUẤT                cv.yaml + report.yaml
```

**Nguyên tắc kỹ thuật:** việc xác định được thì dùng code (kiểm tra, ghép, chống bịa), việc cần hiểu ngôn ngữ mới dùng LLM. LLM **không viết YAML**, chỉ trả câu chữ, code ghép vào cây dữ liệu.

---

## 7. Quy tắc cứng

1. **Thứ tự ưu tiên khi mâu thuẫn:** chỉ dẫn khóa/cấm > sự thật trong Core > Bonus > gợi ý của JD.
2. **Bonus là nguyên liệu**, không chép nguyên văn lên CV.
3. **Chỉ dùng Bonus khi liên quan** JD hoặc được chỉ dẫn, tránh CV quá dài.
4. **Từ khóa JD không có bằng chứng** thì ghi vào báo cáo "thiếu", không nhét vào CV.
5. **Mơ hồ hoặc xung đột thì gắn cờ**, không đoán.
6. **Mọi thay đổi truy ngược được** (trước/sau/nguồn).

---

## 8. Phạm vi theo giai đoạn `[GIẢ ĐỊNH]`

| Giai đoạn | Nội dung |
|---|---|
| **MVP** | Bước ①②⑦⑧⑨; Bonus chỉ gồm ghi chú gắn mục + chỉ dẫn; chế độ chạy một lần |
| **V2** | Thêm JD (⑤⑥), ghi chú chung, phát hiện xung đột (③④), báo cáo đầy đủ |
| **V3** | Industry Pack (kiến trúc trước), chế độ hỏi đáp tương tác |
| **Sau** | Tiền xử lý từ PDF/GitHub/LinkedIn, FastAPI API, đa client |

---

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| LLM bịa số liệu/kinh nghiệm | Bước ⑧ kiểm bằng code, không chỉ dựa vào prompt |
| Người dùng dán nháp lộn xộn vào Bonus | Phân loại + chọn lọc, không chép thẳng |
| Chỉ dẫn bị biến thành nội dung CV | Tách riêng loại "chỉ dẫn" ngay từ bước ② |
| YAML đầu ra không render được | Parse lại và kiểm tra schema trước khi trả |
| Chi phí/độ trễ cao | Chia call nhỏ, song song, giới hạn token |
| Không biết chất lượng có tốt không | Bộ test CV/JD mẫu và tiêu chí đo (xem mục 10, câu 9) |

---

## 10. Câu hỏi mở (cần bạn trả lời)

> Đã trả lời, xem mục 0: câu 1, 2, 5, 6, 8, 10; câu 3, 11, 14 đang dùng mặc định (`[GIẢ ĐỊNH]`). Các câu còn lại vẫn mở.

**A. Mục tiêu và người dùng**
1. `[?]` Sản phẩm này phục vụ ai: chính bạn, một nhóm người dùng cụ thể, hay công khai?
2. `[?]` Ngành đầu tiên là kiến trúc đúng không? Ngoài ra có ngành nào cần hỗ trợ sớm?
3. `[?]` Ngôn ngữ CV: chỉ tiếng Việt, chỉ tiếng Anh, hay song ngữ?

**B. Đầu vào**
4. `[?]` YAML đầu vào do ai tạo: người dùng tự viết, hay ứng dụng/form của bạn sinh ra? (quyết định mức độ chặt của kiểm tra Core)
5. `[?]` Core có đúng định dạng RenderCV không, hay là schema riêng của bạn rồi chuyển đổi sau?
6. `[?]` Bonus: bạn muốn người dùng gõ hoàn toàn tự do, hay có sẵn các ô (ghi chú, chỉ dẫn, tham chiếu)?

**C. Đầu ra**
7. `[?]` Đầu ra cần đúng định dạng RenderCV, hay có cần định dạng khác (JSON Resume, DOCX)?
8. `[?]` Người dùng có xem báo cáo (report) không, hay chỉ nhận CV?

**D. Hành vi**
9. `[?]` Thành công đo bằng gì: điểm ATS, người dùng chấp nhận bao nhiêu % câu đã viết lại, hay bạn tự đọc đánh giá?
10. `[?]` Khi gặp xung đột/mơ hồ: chạy tiếp và ghi vào báo cáo (một lần), hay dừng hỏi lại?
11. `[?]` Mức độ viết lại: chỉ làm mượt câu chữ, hay được phép tái cấu trúc cả bullet (gộp, tách, đổi trọng tâm)?
12. `[?]` Có JD trong mọi lần chạy không, hay thường là không có JD?

**E. Kỹ thuật**
13. `[?]` Đã có sẵn LLM/API key nào (Gemini, OpenAI), hay còn chọn?
14. `[?]` Dạng triển khai mong muốn: thư viện/CLI hay dịch vụ API (FastAPI)?
15. `[?]` Có ràng buộc về chi phí mỗi lần tạo CV, hoặc thời gian chờ tối đa?

---

## 11. Tech stack đề xuất (Python)

### 11.1 Quyết định chính: chọn Python

Theo yêu cầu chuyển source qua Python, stack chính thức được định hình xoay quanh hệ sinh thái Python hiện đại (Python 3.12+). Python là lựa chọn hàng đầu cho các bài toán xử lý NLP, LLM prompt engineering, và agent pipeline:

| Tiêu chí | **Python (Stack đã chọn)** | TypeScript (Phương án tham chiếu) |
|---|---|---|
| Schema & Structured Output LLM | **Pydantic v2** (chuẩn hóa schema, native JSON Schema cho LLM, tốc độ C-Rust qua pydantic-core) | Zod |
| Đọc/ghi YAML giữ format & comment | **`ruamel.yaml`** (hỗ trợ bảo toàn comment, thứ tự field và custom tag cực tốt) | `yaml` (`parseDocument`) |
| Web API & Streaming | **FastAPI** + `sse-starlette` (hiệu năng cao, async ASGI native, tự sinh OpenAPI 3.0/Swagger) | Fastify / NestJS |
| Chia sẻ kiểu dữ liệu | Tự động xuất OpenAPI schema / JSON Schema cho các frontend client (Web/React/Next.js) | Cùng schema Zod |
| Hệ sinh thái LLM & Xử lý ngôn ngữ | Rất mạnh: Official Google GenAI SDK, OpenAI SDK, `tiktoken`, các thư viện diff/NLP tiện lợi | Đủ dùng nhưng hệ sinh thái AI hẹp hơn |

### 11.2 Stack Python chi tiết cho MVP

| Lớp | Công cụ | Ghi chú |
|---|---|---|
| Runtime / Quản lý môi trường | Python >= 3.11 (khuyến nghị 3.12), `pip` / `uv` / `poetry` | Môi trường ảo chuẩn `venv` |
| Schema & Validate | **Pydantic v2** (`pydantic`) | Validate Core, Bonus, Control, Report; sinh JSON Schema cho LLM output |
| Đọc/ghi YAML | **`ruamel.yaml`** | Đảm bảo giữ comment, thứ tự thuộc tính, format YAML sạch |
| Gọi LLM | **Official SDKs** (`google-genai`, `openai`) | Xây interface trừu tượng mỏng, chuyển đổi provider qua biến môi trường |
| Ép đầu ra có cấu trúc | Pydantic `model_validate_json` / Structured Outputs API | LLM chỉ trả JSON có cấu trúc tối giản, code ghép lại vào YAML |
| Chạy song song / Concurrency | `asyncio` + `asyncio.Semaphore` | Giới hạn số request đồng thời gọi tới LLM cho từng entry/bullet |
| Retry / Timeout | `tenacity` + `asyncio.wait_for` | Chiến lược exponential backoff khi LLM rate-limit |
| Chống bịa (Guard) | Python thuần (regex trích xuất số liệu/ngày tháng, token matching kiểm tra thực thể) | Nhẹ, nhanh, không phụ thuộc mô hình nặng |
| Web API Service | **FastAPI** + **Uvicorn** + `sse-starlette` | SSE streaming sự kiện thời gian thực, CORS middleware |
| Logging | `structlog` hoặc `loguru` | Cấu hình filter/masking để che toàn bộ PII (tên, email, số điện thoại) |
| Testing | `pytest` + `pytest-asyncio` | Golden tests: so sánh YAML input và output mong đợi |
| Prompts Management | Thư mục `prompts/*.md` có version | Giữ prompt độc lập, không hardcode trong mã nguồn |
| Quản lý cấu hình | `pydantic-settings` | Tải và kiểm tra biến môi trường `.env` một cách type-safe |

### 11.3 Chủ động không dùng ở MVP

- **LangChain / LangGraph / Agent Frameworks cồng kềnh**: Pipeline 9 bước được triển khai dưới dạng các hàm Python thuần (pure async functions) gọi tuần tự. Hạn chế tối đa abstraction thừa không cần thiết theo tinh thần tối giản.
- **Vector DB / RAG ngoài**: Tri thức ngành ban đầu được nạp trực tiếp qua các file YAML/Markdown context nhỏ gọn trong prompt. Chỉ thêm Vector DB khi khối lượng tài liệu vượt quá context window.
- **Cơ sở dữ liệu (Database)**: Agent hoạt động theo cơ chế stateless (YAML in → YAML out), không lưu trữ CV của người dùng (bảo vệ quyền riêng tư).
- **Task Queue / Worker (Celery/Redis)**: Chưa cần thiết ở giai đoạn MVP; bổ sung khi tải hệ thống tăng cao.

### 11.4 Lộ trình mở rộng

| Khi cần | Bổ sung |
|---|---|
| Tương tác trực tiếp Web/Bot | FastAPI endpoints; SSE event stream để cập nhật tiến độ theo từng bước |
| Nhiều người dùng đồng thời | Thêm hàng đợi bất đồng bộ (Celery / ARQ / Redis) |
| Hỏi đáp tương tác đa vòng | State machine / Session store quản lý trạng thái chờ người dùng xác nhận |
| Quan sát & Đánh giá | Tích hợp OpenTelemetry / Langfuse theo dõi latency, token và cost |
| Nhiều nguồn đầu vào | Bộ tiền xử lý (PyMuPDF cho PDF, GitHub API) chuyển hóa thành YAML chuẩn |

### 11.5 Cấu trúc thư mục dự án

```
cv-ai-agent/
  docs/
    proposal.md       # Bản proposal này
  src/
    api/              # FastAPI application, routers, SSE streaming, middleware
      routes.py
      server.py
    schemas/          # Pydantic models: core, bonus, control, report, contracts
      core.py
      bonus.py
      control.py
      report.py
    pipeline/         # Các bước xử lý tuần tự ①–⑨ (pure functions)
      step1_validate_core.py
      step2_normalize_bonus.py
      ...
    llm/              # Abstraction layer & LLM providers (Gemini, OpenAI)
      base.py
      gemini_provider.py
      openai_provider.py
    guard/            # Logic kiểm tra chống bịa đặt (Anti-hallucination guard)
    industry/         # get_industry_context() (MVP trả rỗng)
    prompts/          # Prompt templates (*.md) có gắn version
    config.py         # Pydantic Settings quản lý .env
  tests/
    golden/           # Test cases: input.yaml + expected output
    test_pipeline.py
  requirements.txt    # Danh sách thư viện Python
  pyproject.toml      # Cấu hình dự án Python
```
