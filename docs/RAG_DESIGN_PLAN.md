# Kế hoạch thiết kế RAG cho CV AI Agent

**Phiên bản:** 1.0  
**Ngày:** 2026-10-22  
**Vai trò tài liệu:** Business Analysis + Solution Design  
**Liên quan:** `BA_PROJECT_BACKLOG.md`, Epic E3

## 1. Kết luận thiết kế

RAG của dự án không nên là một kho CV mẫu để AI sao chép. RAG chỉ nên cung cấp tri thức hướng dẫn viết CV, thuật ngữ nghề nghiệp, tiêu chí ATS và quy tắc trình bày. Mọi tuyên bố về ứng viên phải đến từ Candidate Evidence đã được xác minh.

Kiến trúc bắt buộc tách ba nguồn context:

```text
Candidate Evidence  → Những gì ứng viên thực sự đã làm
Job Description     → Nhà tuyển dụng đang cần gì
Knowledge RAG       → Nên mô tả và trình bày như thế nào
```

Không nguồn nào được thay thế vai trò của nguồn khác.

Hiện repository chỉ có ba knowledge pack Markdown, tổng kích thước rất nhỏ. Vì vậy chưa nên triển khai vector database ngay ở bước đầu. Nên xây đúng metadata, ingestion, chunk contract, retrieval interface và evaluation trước; sau đó mới thêm embedding/pgvector khi corpus đủ lớn và lexical retrieval không còn đáp ứng tốt.

## 2. Vấn đề cần giải quyết

RAG cần giúp agent trả lời các câu hỏi sau:

1. Với vị trí và ngành này, thuật ngữ nào thường được sử dụng?
2. Một Experience bullet tốt nên có cấu trúc như thế nào?
3. Quy tắc ATS nào liên quan đến section đang viết?
4. Cách diễn đạt nào phù hợp với ngôn ngữ và seniority mục tiêu?
5. Trong số các hướng dẫn hiện có, đoạn nào liên quan nhất tới JD và evidence hiện tại?

RAG không được trả lời:

- Ứng viên đã đạt thành tích gì nếu evidence không nói.
- Ứng viên biết công nghệ nào chỉ vì JD hoặc knowledge pack nhắc tới.
- Một số liệu kết quả giả định như `giảm X%`, `Y req/s` hay `99.99% uptime`.
- Chức danh, chứng chỉ, tên dự án hoặc khách hàng không có trong hồ sơ ứng viên.

## 3. Đánh giá implementation hiện tại

Implementation hiện tại trong `src/industry/context.py`:

1. Nhận tên ngành.
2. Ánh xạ alias sang một file Markdown.
3. Đọc toàn bộ file vào bộ nhớ.
4. Đưa toàn bộ nội dung file vào prompt.

Đây là static context injection, chưa phải retrieval-augmented generation đầy đủ.

### Những hạn chế hiện tại

- Không có document/chunk ID.
- Không có metadata filter.
- Không có ranking hoặc relevance score.
- Không có lexical/vector search.
- Không có citations.
- Không có version và content hash.
- Không có source/license/owner.
- Không đo được retrieval quality.
- Nội dung không liên quan vẫn được gửi vào prompt.
- Khi corpus tăng, token usage tăng tuyến tính.

### Rủi ro trong ba knowledge pack hiện tại

Các pack hiện chứa:

- Danh sách công nghệ tổng quát.
- Action verbs.
- Hướng dẫn STAR.
- Ví dụ kết quả như `X%`, `Y req/s`, `99.99% uptime`.

Các ví dụ placeholder này có nguy cơ trở thành số liệu giả nếu prompt hoặc guard hoạt động không đúng. Trước khi đưa vào RAG production, phải:

- Đánh dấu chúng là `example_only`.
- Không cho phép example-only text trở thành candidate claim.
- Ưu tiên chuyển hướng dẫn thành rule, không thành câu mẫu hoàn chỉnh.
- Bổ sung nguồn, quyền sử dụng, version và reviewer.

## 4. Mục tiêu và phạm vi RAG MVP

### Mục tiêu MVP

- Hỗ trợ viết Experience bullet cho IT/Software.
- Hỗ trợ tiếng Việt và tiếng Anh.
- Truy xuất tối đa 4–6 chunks liên quan cho mỗi Experience entry.
- Mọi chunk có ID và metadata.
- Output ghi lại chunk nào đã được dùng.
- Có thể tắt RAG mà pipeline vẫn chạy.
- RAG không làm tăng fabricated-claim rate.

### Ngoài phạm vi MVP

- RAG từ CV của người dùng khác.
- RAG từ dữ liệu crawl Internet tự động.
- Agent tự học trực tiếp từ feedback production.
- Knowledge graph.
- Fine-tuning embedding hoặc LLM.
- Reranker trả phí.
- Multi-modal retrieval từ hình ảnh/PDF scan.

## 5. Taxonomy của knowledge corpus

Không nên tổ chức corpus chỉ theo `industry`. Cần taxonomy nhiều chiều:

| Dimension | Ví dụ |
|---|---|
| `knowledge_type` | `writing_rule`, `ats_rule`, `terminology`, `action_verb`, `section_pattern`, `anti_pattern` |
| `section_type` | `summary`, `experience`, `project`, `skills`, `education` |
| `industry` | `it_software`, `data_ai`, `architecture_construction` |
| `role_family` | `backend`, `frontend`, `devops`, `data_engineering`, `bim` |
| `seniority` | `intern`, `junior`, `mid`, `senior`, `lead`, `manager` |
| `language` | `vi`, `en`, `bilingual` |
| `locale` | `vi-VN`, `en-US`, `general` |
| `evidence_policy` | `guidance_only`, `example_only`, `safe_phrase` |
| `status` | `draft`, `approved`, `deprecated`, `disabled` |

Một chunk có thể mang nhiều giá trị metadata, nhưng phải có đúng một `knowledge_type`, `section_type`, `language`, `status` và `version` rõ ràng.

## 6. Nguồn tri thức

### Nguồn được phép

- Hướng dẫn nội bộ do nhóm tự viết.
- Public career guides có điều khoản sử dụng phù hợp.
- Tài liệu ATS/writing chính thức được phép tóm tắt.
- Taxonomy kỹ năng/nghề nghiệp công khai có license rõ ràng.
- Quy tắc được rút ra từ chuyên gia tuyển dụng và đã được reviewer phê duyệt.

### Nguồn không được phép mặc định

- CV riêng tư của ứng viên.
- CV lấy từ Internet không rõ quyền sử dụng.
- Nội dung tuyển dụng có bản quyền được lưu toàn văn lâu dài nếu chưa được phép.
- Output LLM chưa qua review được tự động đưa ngược vào corpus.
- Các câu thành tích mẫu có thể bị nhầm là fact thực tế.

### Manifest bắt buộc

Mỗi document cần manifest:

```yaml
id: it-experience-writing-v1
title: Experience Writing Rules for Software Engineering
version: 1.0.0
status: approved
language: bilingual
industry:
  - it_software
role_family:
  - backend
  - frontend
  - devops
section_type: experience
knowledge_type: writing_rule
source:
  type: internal
  uri: null
license: internal-approved
owner: cv-content-team
reviewed_by: reviewer-id
reviewed_at: 2026-10-22
content_file: industries/it/software-experience.md
```

## 7. Logical architecture

```text
                     OFFLINE / ADMIN PATH

Approved documents
       ↓
Manifest validation
       ↓
Markdown-aware parsing
       ↓
Semantic chunking
       ↓
Metadata enrichment
       ↓
Content hash + versioning
       ↓
Embedding generation
       ↓
Lexical index + Vector index


                     ONLINE REQUEST PATH

Canonical CV + Candidate Evidence + JDProfile
       ↓
Retrieval Query Builder
       ↓
Metadata pre-filter
       ↓
Lexical search ───────┐
                     ├→ Fusion → Deduplicate → Threshold → Top-K
Vector search ────────┘
       ↓
RetrievedKnowledgeChunk[]
       ↓
Prompt assembly in a GUIDANCE-only channel
       ↓
Typed LLM output with evidence IDs
       ↓
Deterministic guards
       ↓
Semantic patches + citations
```

## 8. Tách Candidate Evidence và RAG Knowledge

### Candidate Evidence

Candidate Evidence là nguồn duy nhất được phép hỗ trợ claim về ứng viên:

```json
{
  "id": "evidence-exp-01-bullet-02",
  "sourcePath": "cv.sections[id=experience].entries[id=exp-01].highlights[2]",
  "type": "achievement",
  "text": "Giảm thời gian build từ 20 phút xuống 8 phút",
  "verified": true
}
```

### Knowledge chunk

Knowledge chunk chỉ hướng dẫn cách viết:

```json
{
  "id": "knowledge-it-experience-0042",
  "text": "A strong engineering bullet states the technical action, scope and measurable outcome when the outcome is supported by evidence.",
  "knowledgeType": "writing_rule",
  "sectionType": "experience",
  "industry": ["it_software"],
  "roleFamily": ["backend", "devops"],
  "language": "en",
  "evidencePolicy": "guidance_only",
  "documentVersion": "1.0.0"
}
```

### Enforcement rule

LLM output phải khai báo cả hai loại reference riêng biệt:

```json
{
  "text": "Tối ưu pipeline CI, giảm thời gian build từ 20 phút xuống 8 phút.",
  "evidenceIds": ["evidence-exp-01-bullet-02"],
  "knowledgeChunkIds": ["knowledge-it-experience-0042"]
}
```

Nếu `evidenceIds` rỗng, claim không được apply. `knowledgeChunkIds` có thể rỗng nếu không tìm thấy guidance phù hợp.

## 9. Data model đề xuất

### `knowledge_documents`

| Field | Type | Ý nghĩa |
|---|---|---|
| `id` | UUID/string | ID ổn định |
| `external_id` | string | ID từ manifest |
| `title` | string | Tên tài liệu |
| `version` | string | Semantic version |
| `status` | enum | draft/approved/deprecated/disabled |
| `source_type` | string | internal/web/public-standard |
| `source_uri` | string nullable | Nguồn tham khảo |
| `license` | string | Quyền sử dụng |
| `language` | string | vi/en/bilingual |
| `content_hash` | string | Kiểm tra thay đổi/idempotency |
| `metadata` | JSONB | Industry, role, section... |
| `created_at` | timestamp | Audit |
| `reviewed_at` | timestamp nullable | Governance |

### `knowledge_chunks`

| Field | Type | Ý nghĩa |
|---|---|---|
| `id` | UUID/string | Citation ID |
| `document_id` | FK | Tài liệu cha |
| `ordinal` | integer | Thứ tự trong document |
| `heading_path` | string[] | Chuỗi heading |
| `content` | text | Nội dung chunk |
| `token_count` | integer | Budget planning |
| `content_hash` | string | Idempotent update |
| `embedding` | vector | Dense embedding |
| `search_text` | tsvector/text index | Lexical retrieval |
| `metadata` | JSONB | Filters |
| `enabled` | boolean | Soft disable |

### `retrieval_runs` — chỉ lưu metadata nếu cần audit

| Field | Ý nghĩa |
|---|---|
| `run_id` | Liên kết AI run |
| `query_hash` | Không lưu nguyên PII query |
| `filters` | Filter metadata |
| `chunk_ids` | Kết quả đã trả |
| `scores` | Score theo từng retriever |
| `latency_ms` | Performance |
| `index_version` | Reproducibility |

## 10. Ingestion pipeline

### Bước 1 — Validate manifest

Reject document nếu thiếu:

- ID/version.
- Owner/reviewer.
- Source/license.
- Language.
- Knowledge type.
- Section type.
- Approval status.

### Bước 2 — Parse tài liệu

Với Markdown:

- Giữ `heading_path`.
- Giữ list item cùng section liên quan.
- Không trộn table với section khác.
- Loại navigation, boilerplate và duplicate headings.

### Bước 3 — Semantic chunking

Thông số khởi đầu:

- Target: 300–500 tokens/chunk.
- Maximum: 700 tokens.
- Overlap: 50–80 tokens chỉ khi paragraph bị chia.
- Một rule ngắn có thể là một chunk độc lập.
- Không nối hai `knowledge_type` khác nhau vào cùng chunk.

Các thông số này phải cấu hình được và được điều chỉnh bằng evaluation, không coi là giá trị cố định vĩnh viễn.

### Bước 4 — Normalize và enrich metadata

- Lowercase/normalize aliases cho filter.
- Không thay đổi nội dung gốc để tạo citation.
- Tạo riêng `normalized_text` cho lexical search nếu cần.
- Tính token count và content hash.

### Bước 5 — Embed và index

- Batch embedding.
- Bounded retry cho lỗi tạm thời.
- Không retry lỗi auth/config.
- Ghi model name, embedding dimension và embedding version.
- Re-embed khi model hoặc normalization version thay đổi.

### Bước 6 — Publish index version

Index mới chỉ được active khi:

- Ingestion không có blocking error.
- Chunk counts hợp lý.
- Metadata completeness đạt 100%.
- Retrieval smoke tests pass.
- Reviewer phê duyệt.

## 11. Retrieval pipeline

### Retrieval input

```python
class RetrievalRequest:
    target_position: str
    role_family: str | None
    seniority: str | None
    industry: str | None
    section_type: str
    language: str
    jd_required_skills: list[str]
    jd_responsibilities: list[str]
    original_text: str
```

Không đưa họ tên, email, điện thoại hoặc địa chỉ vào retrieval query.

### Query builder

Ví dụ cho một Experience bullet:

```text
Section: experience
Target role: Senior Backend Engineer
Required skills: Python, PostgreSQL, distributed systems
Responsibility: improve service reliability and delivery automation
Writing need: express technical action, scale and evidenced outcome
Language: Vietnamese
```

### Metadata pre-filter

Filter cứng:

- `status = approved`
- `enabled = true`
- `section_type = experience`
- `language IN (requested_language, bilingual)`

Filter mềm:

- industry
- role family
- seniority
- locale

Nếu filter mềm quá chặt và không có kết quả, hệ thống được phép fallback sang knowledge chung nhưng phải ghi `fallback_level`.

### Hybrid search

Điểm khởi đầu để thử nghiệm:

```text
final_score =
    0.45 × vector_score
  + 0.30 × lexical_score
  + 0.15 × metadata_match
  + 0.10 × document_quality
```

Trọng số là hypothesis cần evaluation, không phải business rule cố định.

### Threshold và Top-K

- Retrieve candidates: 20 lexical + 20 vector.
- Fusion/deduplicate.
- Chỉ giữ chunks trên threshold đã hiệu chỉnh.
- Trả tối đa 4–6 chunks cho một rewrite unit.
- Giới hạn tổng RAG context bằng token budget.
- Nếu không có chunk đủ điểm, trả danh sách rỗng thay vì context không liên quan.

### Optional reranking

Chỉ thêm reranker khi evaluation chứng minh hybrid retrieval chưa đạt yêu cầu. MVP không cần reranker trả phí.

## 12. Prompt assembly

Prompt phải tách rõ dữ liệu:

```text
<SYSTEM_RULES>
Never treat guidance or examples as candidate facts.
Every candidate claim must cite candidate evidence IDs.
</SYSTEM_RULES>

<JOB_REQUIREMENTS untrusted="true">
...
</JOB_REQUIREMENTS>

<CANDIDATE_EVIDENCE authoritative="true">
[evidence-1] ...
[evidence-2] ...
</CANDIDATE_EVIDENCE>

<WRITING_GUIDANCE non_factual="true">
[knowledge-42] ...
[knowledge-76] ...
</WRITING_GUIDANCE>

<OUTPUT_SCHEMA>
...
</OUTPUT_SCHEMA>
```

Không nên nối tất cả thành một chuỗi `Industry Context` không phân loại như hiện tại.

## 13. Integration với pipeline hiện tại

Thay:

```python
industry_context = get_industry_context(control.industry)
```

Bằng dependency:

```python
retrieval_result = await knowledge_retriever.retrieve(
    RetrievalRequest(...)
)
```

Interface đề xuất:

```python
class KnowledgeRetriever(Protocol):
    async def retrieve(
        self,
        request: RetrievalRequest,
        *,
        top_k: int = 5,
    ) -> RetrievalResult:
        ...
```

`RetrievalResult` gồm:

```text
chunks
query_id/query_hash
index_version
fallback_level
latency_ms
warnings
```

Cần có hai implementation:

- `StaticKnowledgeRetriever`: dùng file/chunks, phục vụ test và Phase A.
- `PgVectorKnowledgeRetriever`: hybrid search production.

Pipeline không được import trực tiếp pgvector, database client hoặc embedding SDK.

## 14. Lộ trình triển khai theo phase

### Phase R0 — Corpus safety trước khi có vector DB

**Mục tiêu:** Biến ba knowledge pack hiện tại thành corpus có quản trị.

- Tạo manifest.
- Tách nội dung thành rule chunks có ID.
- Xóa hoặc đánh dấu placeholder examples.
- Thêm source/license/reviewer/version.
- Tạo static retriever có filter.
- Viết retrieval fixtures.

**Exit gate:** Static retriever trả đúng chunk theo industry, section và language; không có candidate-like claim được đánh dấu `guidance_only` sai.

### Phase R1 — Lexical retrieval

**Mục tiêu:** Chứng minh query và metadata design trước embedding.

- In-memory BM25/FTS hoặc PostgreSQL full-text.
- Metadata filters.
- Top-K và threshold.
- Citation IDs.
- Recall@K evaluation.

**Exit gate:** Recall@5 đạt baseline trên bộ 20 query và context nhỏ hơn full-pack injection.

### Phase R2 — Vector + hybrid retrieval

**Mục tiêu:** Tìm được guidance liên quan khi từ khóa không trùng chính xác.

- Embedding interface và mock.
- pgvector schema/index.
- Batch ingestion.
- Vector retrieval.
- Fusion lexical + vector.
- Versioned index.

**Exit gate:** Hybrid retrieval cải thiện metric đã chọn so với lexical baseline mà không tăng irrelevant-result rate quá ngưỡng.

### Phase R3 — Pipeline integration

**Mục tiêu:** RAG cải thiện wording nhưng không làm giảm factuality.

- Query theo từng rewrite unit.
- Prompt channel separation.
- Knowledge citations trong report.
- Degraded mode khi RAG lỗi.
- Token budget.

**Exit gate:** Schema-valid output 100%; fabricated-claim rate không tăng so với no-RAG baseline.

### Phase R4 — Operations và governance

**Mục tiêu:** Có thể cập nhật corpus an toàn.

- Admin ingestion command/API.
- Draft → review → publish workflow.
- Disable/deprecate documents.
- Index rollback.
- Retrieval metrics và alerting.
- Retention/audit policy.

## 15. Backlog chi tiết

### RAG-001 — Xác nhận use cases và boundaries

**Priority:** P0  
**Estimate:** 0.5 ngày

**Acceptance criteria:**

- Danh sách use case MVP được phê duyệt.
- Candidate Evidence và Knowledge RAG được định nghĩa riêng.
- Quy định “RAG không phải nguồn candidate facts” xuất hiện trong product requirement và prompt policy.

### RAG-002 — Thiết kế knowledge taxonomy và metadata schema

**Priority:** P0  
**Estimate:** 1 ngày  
**Dependency:** RAG-001

**Acceptance criteria:**

- Metadata schema validate được bằng Pydantic.
- Alias ngành/role được chuẩn hóa.
- Có version/status/source/license/reviewer.
- Có migration path từ ba pack hiện tại.

### RAG-003 — Audit và làm sạch knowledge packs hiện tại

**Priority:** P0  
**Estimate:** 1 ngày  
**Dependency:** RAG-002

**Acceptance criteria:**

- Placeholder `X%`, `Y req/s`, `99.99%` được xóa hoặc đánh dấu example-only.
- Mỗi rule có section/language/industry metadata.
- Không có câu nào ngụ ý một thành tích thực tế của ứng viên.
- Reviewer phê duyệt nội dung MVP.

### RAG-004 — Tạo manifest và document loader

**Priority:** P0  
**Estimate:** 1 ngày  
**Dependency:** RAG-002

**Acceptance criteria:**

- Invalid manifest bị reject với lỗi theo field.
- Chỉ document `approved` được publish.
- Content hash ổn định qua nhiều lần chạy.
- Loader không đọc file ngoài knowledge root.

### RAG-005 — Implement semantic Markdown chunker

**Priority:** P0  
**Estimate:** 1.5 ngày  
**Dependency:** RAG-004

**Acceptance criteria:**

- Chunk giữ heading path và metadata.
- Không trộn knowledge types.
- Token limit được kiểm soát.
- Cùng input/config tạo cùng chunk IDs.
- Unit tests có heading, list, table, tiếng Việt và Unicode.

### RAG-006 — Implement StaticKnowledgeRetriever

**Priority:** P0  
**Estimate:** 1 ngày  
**Dependency:** RAG-005

**Acceptance criteria:**

- Filter theo language, industry và section.
- Trả chunk IDs và deterministic score.
- Không tìm thấy thì trả rỗng, không throw.
- Pipeline tests không cần database hoặc embedding API.

### RAG-007 — Tạo retrieval evaluation dataset

**Priority:** P0  
**Estimate:** 1 ngày  
**Dependency:** RAG-005

**Acceptance criteria:**

- Có tối thiểu 20 query cases.
- Mỗi case có expected relevant chunk IDs.
- Bao phủ vi/en, generic/IT và negative queries.
- Dataset không chứa PII.

### RAG-008 — Implement lexical retrieval baseline

**Priority:** P1  
**Estimate:** 1.5 ngày  
**Dependency:** RAG-006, RAG-007

**Acceptance criteria:**

- Có tokenization phù hợp tối thiểu cho vi/en.
- Kết quả có lexical score.
- Top-K/threshold cấu hình được.
- Evaluation tạo báo cáo Recall@K, MRR và irrelevant rate.

### RAG-009 — Thiết kế database migration cho pgvector

**Priority:** P1  
**Estimate:** 1 ngày  
**Dependency:** RAG-002

**Acceptance criteria:**

- Tables/indexes và schema isolation được review.
- Dimension không hard-code ngoài embedding model config/migration.
- Có unique constraint cho document version và chunk hash.
- Có rollback plan.

### RAG-010 — Implement embedding provider abstraction

**Priority:** P1  
**Estimate:** 1 ngày  
**Dependency:** RAG-005

**Acceptance criteria:**

- Provider protocol độc lập SDK.
- Mock embedding deterministic.
- Batch, timeout và bounded retry được hỗ trợ.
- Model/dimension/version được ghi cùng embeddings.

### RAG-011 — Implement idempotent ingestion service

**Priority:** P1  
**Estimate:** 1.5–2 ngày  
**Dependency:** RAG-009, RAG-010

**Acceptance criteria:**

- Chạy lại cùng corpus không tạo duplicate.
- Chỉ chunk mới/thay đổi được embed lại.
- Failure không publish index version dở dang.
- Có dry-run report.

### RAG-012 — Implement pgvector retrieval và hybrid fusion

**Priority:** P1  
**Estimate:** 2 ngày  
**Dependency:** RAG-008, RAG-011

**Acceptance criteria:**

- Dense và lexical retrieval chạy độc lập được.
- Fusion score có test.
- Metadata filter được áp dụng trước hoặc trong query, không filter muộn toàn bộ kết quả.
- Query latency và result count được đo.

### RAG-013 — Tích hợp retriever vào tailoring pipeline

**Priority:** P1  
**Estimate:** 1.5 ngày  
**Dependency:** RAG-006; nâng cấp hybrid sau RAG-012

**Acceptance criteria:**

- Pipeline phụ thuộc `KnowledgeRetriever` interface.
- Query được tạo theo từng Experience entry.
- Prompt tách evidence và guidance.
- Report chứa knowledge chunk IDs và index version.
- Retrieval failure chuyển sang no-RAG degraded mode.

### RAG-014 — Add RAG factuality regression tests

**Priority:** P1  
**Estimate:** 1 ngày  
**Dependency:** RAG-013

**Acceptance criteria:**

- Knowledge pack có công nghệ không tồn tại trong evidence nhưng output không được thêm công nghệ đó.
- Example-only metric không xuất hiện trong output.
- RAG-on và RAG-off đều giữ nguyên company/title/date.
- Fabricated-claim metric không xấu hơn baseline.

### RAG-015 — Add retrieval observability và governance commands

**Priority:** P2  
**Estimate:** 1.5 ngày  
**Dependency:** RAG-012

**Acceptance criteria:**

- Có ingest dry-run, publish, disable và rollback command.
- Metrics gồm latency, empty retrieval, fallback level, top scores và index version.
- Không log raw candidate/JD query.
- Có hướng dẫn update corpus và xử lý lỗi.

## 16. Thứ tự thực hiện cho một developer

```text
RAG-001
  ↓
RAG-002
  ├─→ RAG-003
  └─→ RAG-004 → RAG-005 → RAG-006 → RAG-007 → RAG-008
                                              ↓
                     RAG-009 → RAG-010 → RAG-011 → RAG-012
                                              ↓
                         RAG-013 → RAG-014 → RAG-015
```

### Sprint RAG đầu tiên — chưa dùng vector DB

Thực hiện:

1. RAG-001
2. RAG-002
3. RAG-003
4. RAG-004
5. RAG-005
6. RAG-006
7. RAG-007
8. RAG-008

Kết quả sprint:

- Corpus sạch và có quản trị.
- Chunk IDs ổn định.
- Có retrieval thật dựa trên relevance thay vì nạp toàn bộ file.
- Có baseline evaluation.
- Pipeline vẫn chạy offline và test không cần API embedding.

Chỉ bắt đầu pgvector sau khi baseline này hoàn tất.

## 17. Evaluation framework

### Retrieval metrics

| Metric | Ý nghĩa | Mục tiêu khởi đầu |
|---|---|---:|
| Recall@5 | Có ít nhất một relevant chunk trong Top-5 | ≥ 85% |
| MRR | Relevant chunk xuất hiện sớm | ≥ 0.70 |
| Irrelevant@5 | Tỷ lệ chunk không liên quan | ≤ 20% |
| Empty retrieval | Không tìm thấy context | Theo dõi theo domain, không ép bằng 0 |
| P95 latency | Thời gian retrieval online | ≤ 300 ms, chưa tính embedding query từ remote nếu có |

### Generation metrics liên quan RAG

| Metric | Mục tiêu |
|---|---:|
| Output hợp lệ schema | 100% |
| Candidate claims có evidence IDs | 100% |
| Fabricated numeric claims | 0% |
| Knowledge-only technology bị thêm vào CV | 0 blocking cases |
| Citation IDs tồn tại trong retrieval result | 100% |
| Token context giảm so với full-pack injection | ≥ 40% khi corpus đủ lớn |

### A/B evaluation

Mỗi fixture chạy hai chế độ:

- Baseline: RAG off.
- Candidate: RAG on.

RAG chỉ được release nếu:

- Retrieval quality đạt gate.
- Factuality không giảm.
- Schema validity không giảm.
- Human reviewer đánh giá wording hoặc relevance được cải thiện.

## 18. Security và privacy

- Không embed họ tên, email, điện thoại, địa chỉ hoặc raw CV vào shared knowledge index.
- Không lưu raw retrieval query nếu query có candidate/JD content; chỉ lưu hash và metadata an toàn.
- JD là untrusted input và có thể chứa prompt injection.
- Retrieved documents cũng là untrusted content; corpus approval không thay thế prompt isolation.
- Loader phải chặn path traversal và symlink escape.
- Ingestion API, nếu có, phải là admin-only.
- Knowledge document không tự động active sau upload.
- Database credentials chỉ có quyền trên schema RAG cần thiết.
- Không trả toàn bộ source document cho client nếu user chỉ cần citation metadata.

## 19. Failure modes

| Failure | Hành vi mong muốn |
|---|---|
| Không có relevant chunk | Chạy no-RAG, ghi warning |
| Embedding provider lỗi | Fallback lexical nếu khả dụng |
| Vector DB unavailable | Fallback static/lexical hoặc degraded response |
| Index version đang publish | Tiếp tục dùng version active trước đó |
| Chunk chứa placeholder metric | Guard không cho thành candidate claim |
| Query chứa PII | Redact khỏi log; không lưu raw query |
| Corpus document bị disable | Không xuất hiện trong request mới |
| Citation ID không tồn tại | Reject proposal hoặc đánh dấu validation failure |

## 20. Quyết định BA cần xác nhận

Trước Phase R2 cần xác nhận:

1. PostgreSQL hiện tại có được phép bật extension `pgvector` không?
2. Agent dùng cùng PostgreSQL cluster với Render nhưng schema riêng, hay database riêng?
3. Embedding provider nào được phép dùng và dữ liệu có được gửi ra dịch vụ bên ngoài không?
4. Nguồn tài liệu nào được phê duyệt cho corpus đầu tiên?
5. Ai là reviewer có quyền chuyển document từ `draft` sang `approved`?
6. Có cần hiển thị citation cho end user hay chỉ dùng cho audit/internal report?
7. Ngôn ngữ MVP là Việt + Anh hay chỉ Việt trước?

## 21. Khuyến nghị cuối cùng

Không bắt đầu bằng việc cài vector database. Bước đúng đầu tiên là RAG-001 đến RAG-008: chuẩn hóa mục đích, làm sạch corpus, tạo chunk contract, static/lexical retrieval và evaluation baseline.

Khi chưa có evaluation, thêm embedding chỉ làm hệ thống phức tạp hơn mà không chứng minh được retrieval tốt hơn. Khi baseline đã đo được, pgvector trở thành một nâng cấp có thể đánh giá rõ ràng thay vì một quyết định theo xu hướng.

