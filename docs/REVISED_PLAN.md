# Plan: Revised Architecture & Task Breakdown

| | |
|---|---|
| **Ngày** | 2026-10-12 |
| **Trạng thái** | DRAFT — chờ xác nhận trước khi implement |

---

## Câu hỏi cần làm rõ trước khi bắt đầu

Trả lời 3 câu này sẽ quyết định kiến trúc của toàn bộ hệ thống:

| # | Câu hỏi | Tại sao quan trọng |
|---|---|---|
| Q1 | User nhập thông tin theo **kiểu nào**: điền form từng bước (wizard), hay paste file/text một lần? | Quyết định flow có SSE chat hay POST đơn thuần |
| Q2 | **LLM nào** bạn đang dùng với API key đó? (Gemini? OpenAI? Anthropic?) | Quyết định SDK nào tích hợp |
| Q3 | Bạn muốn output là **file YAML** (để render), hay **text trả về API** cho frontend hiển thị? | Quyết định format đầu ra |

Tôi sẽ **đặt giả định mặc định** cho mỗi câu và ghi rõ, bạn có thể đổi sau.

---

## Task 1 — Env Validation (Fail-Fast)

### Vấn đề hiện tại

```python
# config.py hiện tại
class Settings(BaseSettings):
    ai_api_key: str = Field(default="")   # ← Trống vẫn OK → server khởi động rồi crash khi gọi LLM
    ai_model: str  = Field(default="")   # ← Không biết thiếu cho đến lúc gọi
```

Server khởi động bình thường dù thiếu key. Lỗi chỉ xuất hiện khi user gọi API → trải nghiệm tệ.

### Giải pháp

Tách settings thành 2 nhóm:

```
AlwaysRequired (bắt buộc mọi lúc):
  AI_PORT, FRONTEND_ORIGIN

ConditionalRequired (bắt buộc khi AI_PROVIDER != "mock"):
  AI_API_KEY   → phải có khi provider = gemini | openai
  AI_MODEL     → phải có khi provider = gemini | openai
  AI_API_URL   → chỉ bắt buộc khi provider = openai (custom endpoint)
```

**Hành vi mong muốn:**

```
# Trường hợp 1: provider=core (mock/stub) — OK dù thiếu key
AI_PROVIDER=core
→ Server khởi động ✅

# Trường hợp 2: provider=gemini nhưng thiếu key
AI_PROVIDER=gemini
AI_API_KEY=
→ Server dừng ngay, log rõ: "AI_API_KEY is required when AI_PROVIDER=gemini"

# Trường hợp 3: đầy đủ
AI_PROVIDER=gemini
AI_API_KEY=your_key_here
AI_MODEL=gemini-2.0-flash
→ Server khởi động ✅
```

**File thay đổi:** `src/config.py`
**Không thêm dependency mới.**

---

## Task 2 — Redesign Input Schema

### Vấn đề hiện tại

`CoreCvInput` hiện có `sections: List[Dict]` — quá generic, không validation, không rõ field nào bắt buộc.

### CV fields cần có

Theo yêu cầu của bạn, mọi CV đều có:

| Field | Bắt buộc? | Ghi chú |
|---|---|---|
| `name` | ✅ | Họ tên đầy đủ |
| `position` | ✅ | Vị trí/job title đang apply (hoặc hiện tại) |
| `objective` | ✅ | Mục tiêu nghề nghiệp / Career summary |
| `experience` | ✅ | Danh sách kinh nghiệm làm việc |
| `projects` | Khuyến nghị | Dự án đã làm |
| `education` | ✅ | Học vấn |
| `achievements` | Tuỳ chọn | Giải thưởng, chứng chỉ |
| `interests` | Tuỳ chọn | Sở thích, hoạt động |
| `bonus` | Tuỳ chọn | Thông tin bổ sung cho AI (không in ra CV) |
| `jd` | Tuỳ chọn | Job description của công ty muốn apply |

### Schema mới đề xuất

```yaml
# Ví dụ input YAML — bạn submit cái này lên API
name: "Nguyễn Văn A"
position: "Senior Backend Engineer"          # vị trí muốn apply
objective: "5 năm kinh nghiệm backend, muốn..."  # career summary

experience:
  - company: "FPT Software"
    title: "Backend Engineer"
    start: "2021-01"
    end: "2024-06"
    highlights:
      - "Xây dựng microservice xử lý 10k req/s"
      - "Tối ưu database giảm latency 40%"

projects:
  - name: "CV AI Agent"
    url: "https://github.com/..."
    highlights:
      - "FastAPI + Pydantic v2"

education:
  - institution: "ĐH Bách Khoa HN"
    degree: "Kỹ sư CNTT"
    year: "2020"

achievements:
  - "Google Cloud Certified Professional"
  - "Giải nhất Hackathon 2022"

interests:
  - "AI/ML, Open Source, Running"

# Bonus — chỉ cho AI đọc, không in ra CV
bonus:
  notes:
    - "Dự án FPT tôi lead team 8 người, nhưng chưa ghi vào highlights"
    - "Biết thêm Kubernetes nhưng chưa có dự án thực tế"
  directives:
    - "Nhấn mạnh kinh nghiệm backend, không nhắc frontend"
    - "Viết theo giọng tự tin, không khiêm tốn quá"

# JD của công ty muốn apply
jd: |
  We are looking for a Senior Backend Engineer with 3+ years experience
  in microservices, strong in Python/Go, familiar with Kubernetes...

# Control
locale: vi          # ngôn ngữ CV output
locked: [education] # không được sửa phần này
```

**Pydantic models tương ứng:**

```
CvInput (top-level)
 ├── name: str                      (required)
 ├── position: str                  (required)
 ├── objective: str                 (required)
 ├── experience: List[Experience]   (required, min 1 item)
 ├── projects: List[Project]        (optional)
 ├── education: List[Education]     (required, min 1 item)
 ├── achievements: List[str]        (optional)
 ├── interests: List[str]           (optional)
 ├── bonus: BonusInput              (optional)
 ├── jd: Optional[str]              (optional)
 └── control: ControlConfig         (optional, defaults apply)

Experience:
 ├── company: str
 ├── title: str
 ├── start: str
 ├── end: Optional[str]   (None = "present")
 ├── location: Optional[str]
 └── highlights: List[str]  (min 1)

Project:
 ├── name: str
 ├── url: Optional[str]
 ├── tech: List[str]
 └── highlights: List[str]

Education:
 ├── institution: str
 ├── degree: str
 ├── year: Optional[str]
 └── gpa: Optional[str]
```

**File thay đổi:**
- `src/schemas/cv_input.py` (tạo mới, thay thế `CoreCvInput` trong `proposal.py`)
- `src/schemas/proposal.py` (giữ BonusInput, ControlConfig; xoá CoreCvInput cũ)

---

## Task 3 — User Input Workflow + LLM Pipeline

### Giả định (Q1): User nhập từng bước qua SSE chat

Flow mong muốn:

```
[User] POST /v1/tailor/start
       body: { name, position, jd (optional) }
       ↓
[Agent] SSE stream bắt đầu
       ↓
Stage 1: Thu thập thông tin cơ bản
  → Event: question("Hãy mô tả kinh nghiệm làm việc gần nhất của bạn")
  → User trả lời
  → Event: question("Dự án nào bạn tự hào nhất?")
  → ...
       ↓
Stage 2: AI đọc JD + phân tích
  → Event: progress("Đang phân tích JD...")
  → LLM trích keywords từ JD
  → Event: progress("Tìm thấy 12 từ khoá phù hợp")
       ↓
Stage 3: AI viết lại CV
  → Event: progress("Đang viết lại phần Experience...")
  → LLM viết highlights theo STAR + match JD keywords
  → Guard kiểm tra (không bịa số liệu)
  → Event: partial_update(yaml_patch)   ← cập nhật từng section
       ↓
Stage 4: Báo cáo
  → Event: done(cv_yaml, report)
```

### Pipeline steps

```
Bước ①  Validate input (code thuần)
         → Kiểm các field bắt buộc, size limits

Bước ②  Phân tích JD (LLM)
         → Input: JD text
         → Output: {keywords[], required_skills[], nice_to_have[], seniority}
         → Bỏ qua nếu không có JD

Bước ③  Load Industry Context (code thuần)
         → get_industry_context(industry) → whitelist terms, style notes
         → MVP: trả rỗng

Bước ④  Gắn Bonus vào sections (code + LLM)
         → Tách bonus notes thành Fragments (mỗi mảnh 1 ý)
         → attach_to rõ → gắn thẳng
         → attach_to không rõ → LLM gợi ý section phù hợp

Bước ⑤  Chọn lọc nội dung (LLM)
         → Mỗi experience/project: tính độ liên quan với JD keywords
         → Quyết định highlight nào đưa lên, từ khóa nào nhấn mạnh

Bước ⑥  Viết lại theo STAR + JD (LLM)
         → Input: experience entry + relevant fragments + JD keywords
         → Output: highlights[] mới (cùng số lượng)
         → Gọi song song, concurrency = 3
         → Mỗi câu trả về kèm source_ids[]

Bước ⑦  Guard chống bịa (code thuần)
         → Số liệu, tên riêng trong output phải có trong input
         → Từ cấm không được xuất hiện
         → Thất bại → retry LLM với lý do (tối đa 2 vòng)
         → Vẫn fail → giữ câu gốc

Bước ⑧  Tổng hợp & xuất (code thuần)
         → Ghép kết quả vào YAML tree
         → Tạo report (changes, used_bonus, missing_keywords, score)
         → Validate output với Pydantic
         → Trả cv_yaml + report
```

### Prompt design (quan trọng)

LLM **không viết YAML**. LLM chỉ trả về text cho từng bullet:

```json
// LLM trả về JSON này
{
  "bullets": [
    {
      "text": "Phát triển microservice xử lý 10k req/s, giảm latency 40% so với hệ thống cũ",
      "source_ids": ["exp_0_highlight_0", "exp_0_highlight_1"]
    }
  ]
}
```

Code Python ghép vào YAML. LLM không biết gì về cấu trúc YAML.

Dữ liệu user luôn được đặt trong boundary markers chống prompt injection:

```
<USER_EXPERIENCE>
Công ty: FPT Software
...nội dung user nhập...
</USER_EXPERIENCE>
```

---

## Task 4 — Real LLM Integration (Gemini)

### ⚠️ Về API Key

**Tuyệt đối không paste key vào chat hoặc code.** Chỉ đặt trong `.env`:

```env
# .env (file này đã có trong .gitignore)
AI_PROVIDER=gemini
AI_API_KEY=your_new_key_here
AI_MODEL=gemini-2.0-flash
```

### Giả định (Q2): Đây là Gemini API key

SDK sử dụng: `google-genai` (đã có trong `requirements.txt`).

### GeminiProvider sẽ làm gì

```python
class GeminiProvider(LLMProvider):
    async def generate_structured(schema, messages, opts) → BaseModel:
        # Dùng google-genai SDK
        # Bật response_schema để Gemini trả JSON đúng cấu trúc
        # Không cần parse thủ công
        response = await client.generate_content(
            contents=messages,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema.model_json_schema()
            }
        )
        return schema.model_validate_json(response.text)
```

### So sánh mock vs real

| | Mock Provider | Real Gemini Provider |
|---|---|---|
| Dùng cho | Tests (luôn) | Production |
| Cần API key | ❌ | ✅ |
| Chi phí | \$0 | Tính theo token |
| Deterministic | ✅ (cùng input → cùng output) | ❌ |
| Tốc độ | ~0ms | ~1-5s |

> **Quy tắc:** Tests **luôn** dùng mock. Mock không bị bỏ đi — nó là công cụ test quan trọng. Khi run server thật thì dùng Gemini.

### Cách chuyển đổi provider

```python
# Chỉ cần đổi env, không sửa code
AI_PROVIDER=gemini   → dùng GeminiProvider
AI_PROVIDER=openai   → dùng OpenAIProvider
AI_PROVIDER=core     → dùng MockProvider (stub hiện tại)
```

---

## Task 5 — Internal Data Contracts là gì và tại sao cần?

### Tại sao cần?

Pipeline có 8 bước. Mỗi bước nhận dữ liệu từ bước trước và truyền cho bước sau. Nếu không có type rõ ràng:

```python
# Không có internal types — dễ crash
def step7_rewrite(data):        # data là gì? Dict? List? String?
    for item in data["bullets"]:   # KeyError nếu sai key
        ...

# Có internal types — an toàn, rõ ràng
def step7_rewrite(units: list[RewriteUnit]) → list[RewriteResult]:
    for unit in units:
        unit.leaves    # IDE biết đây là list[Leaf]
        unit.fragments # IDE biết đây là list[Fragment]
```

### 4 types cần tạo

```
Leaf — Một đoạn văn bản có thể sửa trong CV gốc
────────────────────────────────────────────────
path:   "experience[0].highlights[1]"  ← địa chỉ chính xác trong YAML
text:   "Phụ trách dự án 12 tầng"      ← nội dung gốc
locked: False                           ← có bị khóa không

Ví dụ dùng: YAML layer dùng path để patch, Guard dùng text để build corpus


Fragment — Một mảnh thông tin rút từ Bonus notes
──────────────────────────────────────────────────
id:        "frag_0"
text:      "Lead team 8 người"         ← thông tin gốc từ user
attach_to: "experience[0]"             ← gắn vào experience nào
target:    None                        ← (sau khi LLM xử lý sẽ có)
unplaced:  False

Ví dụ dùng: LLM đọc cùng với Leaf để viết lại highlights


Constraint — Chỉ dẫn đã được cấu trúc hoá từ directives
──────────────────────────────────────────────────────────
ban_terms:  ["frontend", "company Y"]  ← không được nhắc
emphasize:  ["BIM", "microservice"]    ← nhấn mạnh từ này
tone:       "confident"                ← giọng văn
raw:        "Nhấn mạnh BIM hơn concept" ← directive gốc trước khi parse

Ví dụ dùng: Đưa vào prompt LLM + Guard kiểm tra ban_terms


RewriteResult — Cái LLM trả về cho 1 bullet
─────────────────────────────────────────────
path:        "experience[0].highlights[1]"  ← địa chỉ để patch
text:        "Phát triển microservice 10k req/s, giảm latency 40%"
source_ids:  ["leaf_exp0_h0", "frag_0"]     ← chứng minh nguồn gốc

Ví dụ dùng: Guard verify source_ids hợp lệ → YAML layer patch vào tree
```

### Flow data qua pipeline

```
YAML Input
   │
   ▼
[parse_yaml()]
   │
   ├──► CoreCvInput (validate Pydantic)
   │
   ├──► collect_leaves() → List[Leaf]        ← tất cả text có thể sửa
   │
   └──► normalize_bonus() → List[Fragment]   ← bonus notes → fragments
                          → Constraint       ← directives → structured

                    │
                    ▼
[LLM: analyze_jd()] → JDProfile {keywords, required, seniority}

                    │
                    ▼
[select_content()] → RewriteUnit = {leaf, fragments, jd_keywords}

                    │
                    ▼
[LLM: rewrite()]  → List[RewriteResult]    ← LLM trả về

                    │
                    ▼
[guard.verify()]  → accepted[], rejected[] + reasons

                    │
                    ▼
[retry if rejected] → max 2 vòng → fallback to original

                    │
                    ▼
[patch() + serialize()] → cv.yaml + report.yaml
```

---

## Kế hoạch implement theo thứ tự

Dưới đây là thứ tự tôi đề xuất. Mỗi task xây trên task trước.

| Bước | Task | Files thay đổi | Ước lượng |
|---|---|---|---|
| **1** | T1: Env validation | `src/config.py` | Nhanh |
| **2** | T2: Schema CV Input mới | `src/schemas/cv_input.py` (new) | Nhanh |
| **3** | T5: Internal types | `src/schemas/internal.py` (new) | Nhanh |
| **4** | YAML layer | `src/yaml_layer/io.py` (new) | Trung bình |
| **5** | Round-trip tests | `tests/golden/*.yaml` (new) | Trung bình |
| **6** | LLM Interface + Mock | `src/llm/base.py`, `src/llm/mock_provider.py` | Nhanh |
| **7** | T4: Gemini Provider (real) | `src/llm/gemini_provider.py` | Trung bình |
| **8** | Prompt templates | `prompts/rewrite.v1.md` | Nhanh |
| **9** | T3: Pipeline steps ①-⑧ | `src/pipeline/steps/` | Lớn |
| **10** | CLI + E2E test | `src/cli.py` | Trung bình |
| **11** | API `/v1/tailor` | `src/api/routes.py` | Trung bình |

---

## Câu hỏi cần bạn xác nhận

Trước khi bắt đầu code, tôi cần biết:

1. **API key là Gemini hay loại khác?**
   - Nếu Gemini → dùng `google-genai` SDK (đã có trong requirements)
   - Format key của Gemini thường là `AIza...` hoặc `AQ...`

2. **User nhập thông tin theo kiểu nào?**
   - Option A: Paste một đoạn text/YAML một lần → AI xử lý một phát
   - Option B: Điền từng phần qua chat (wizard từng bước)
   - Option C: Cả hai (mode simple và mode wizard)

3. **Output mong muốn là gì?**
   - Option A: File YAML để render thành PDF (theo PLAN.md gốc)
   - Option B: Text/JSON trả về cho frontend hiển thị trực tiếp

---

## Những gì KHÔNG thay đổi

- Flow SSE stream hiện tại (`/v1/ai/stream-generate`) giữ nguyên
- `/health` endpoint giữ nguyên
- Pydantic v2, FastAPI, ruamel.yaml — giữ nguyên
- Mock provider giữ nguyên trong tests (chỉ bỏ mock trong production)
