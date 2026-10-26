# 08 — Implementation workbook

Workbook biến kiến thức thành tám checkpoint. Chỉ chuyển checkpoint khi Definition of Done (DoD) đã đạt. Ghi lỗi và bài học ngay trong issue/nhật ký cá nhân, không sửa trực tiếp tài liệu chuẩn bằng thông tin tạm thời.

## Cách dùng

Mỗi checkpoint theo vòng lặp:

```text
Đọc → Dự đoán → Chạy test → Thay đổi nhỏ → Chạy lại → Giải thích kết quả
```

Các lệnh dưới đây chạy từ `D:\Projects\cv-ai-agent` bằng PowerShell, trừ khi ghi rõ Render.

## Checkpoint 1 — Python 3.12 và test suite

**Đọc trước:** [Agent workflow](02-agent-workflow.md), [Evaluation](06-guardrails-and-evaluation.md).

**Quan sát:** `pyproject.toml`, `requirements.txt`, `tests/conftest.py`.

**Task:**

- Tạo `.venv` bằng Python 3.12.
- Cài dependencies trong môi trường sạch.
- Chạy collect và full suite; xác định test treo/thất bại.
- Pin phiên bản test dependencies tương thích.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest --collect-only -q
python -m pytest -q
```

**Kết quả mong đợi:** suite kết thúc, không gọi mạng mặc định.

**DoD:** tất cả test xanh hoặc mỗi failure có issue tái hiện độc lập; không còn hang.

**Tự hỏi:** async test khác sync test ở lifecycle nào? Vì sao global Python environment gây nhiễu?

## Checkpoint 2 — Portable fixtures

**Đọc trước:** [Contract](03-contract-evidence-patch.md).

**Quan sát:** các test có `FIXTURES_DIR`, Render `packages/cv-contracts/fixtures`.

**Task:** loại hard-coded `D:/Projects/Render`; dùng fixture versioned trong repo hoặc package contract có cơ chế rõ ràng.

```powershell
rg -n "D:/Projects|d:/Projects|FIXTURES_DIR" tests
python -m pytest -q tests/test_canonical_validator.py tests/test_patch_applier.py
```

**DoD:** test chạy khi checkout riêng `cv-ai-agent`; không phụ thuộc folder hàng xóm.

**Tự hỏi:** copy fixture và consume package có trade-off gì về schema drift?

## Checkpoint 3 — Canonical contract

**Đọc trước:** [Contract](03-contract-evidence-patch.md).

**Quan sát:** Python `src/schemas/`, Render `packages/cv-contracts/src`, Backend tailor DTOs.

**Task:** chốt shared types/schema, trạng thái `validated/rejected/unchanged`, versioning và schema drift check.

**Test scenarios:** request thiếu field, stable ID trùng, entry type sai, patch field không hỗ trợ, hash sai.

**DoD:** cùng fixture được TypeScript và Python accept/reject nhất quán.

**Tự hỏi:** file nào là source of truth? Nếu schema version không hỗ trợ thì API trả gì?

## Checkpoint 4 — Agent pipeline

**Đọc trước:** [Agent workflow](02-agent-workflow.md), [LLM](04-llm-provider-and-prompting.md).

**Quan sát:** `agent_orchestrator.py`, evidence extractor, JD analyzer, writer và guard.

**Task:** canonical pipeline là production path; legacy path được đánh dấu deprecation. Mọi LLM call dùng typed output và mock trong test.

```powershell
python -m pytest -q tests/test_agent_orchestrator.py tests/test_evidence_and_jd.py tests/test_writer_and_guards.py
```

**DoD:** valid input tạo validated patch; hallucination bị reject; lỗi giữ nguyên document.

**Tự hỏi:** bước nào được fallback? Status nào cho partial/degraded?

## Checkpoint 5 — Static RAG

**Đọc trước:** [RAG](05-rag-fundamentals.md).

**Quan sát:** `src/knowledge/` và `tests/test_knowledge_eval.py`.

**Task:** cấu hình `null|static`; runtime mặc định static, test inject rõ ràng; metadata có approved/version/source; proposal lưu citation.

```powershell
python -m pytest -q tests/test_knowledge_eval.py tests/test_agent_orchestrator.py
```

**DoD:** top chunks đúng language/industry/section; empty retrieval an toàn; knowledge không tạo candidate fact.

**Tự hỏi:** Recall@5 hiện tại là bao nhiêu? Case nào lexical retrieval bỏ sót?

## Checkpoint 6 — Render Backend

**Đọc trước:** [Architecture](01-system-architecture.md), [Render integration](07-render-integration.md).

**Quan sát:** `MODULE_BE/src/cv` và `MODULE_BE/test/cv-tailor.test.cjs`.

**Task:** harden preview/apply endpoint, validate Agent response, timeout/error mapping, bắt buộc service auth production và atomic OCC update.

```powershell
Set-Location D:\Projects\Render\MODULE_BE
npm test -- --runInBand
```

Nếu script không nhận `--runInBand`, dùng script test được khai báo trong `package.json` mà không thêm flag.

**DoD:** preview không mutation; apply tăng version một lần; conflict/lock/invalid patch trả đúng status.

**Tự hỏi:** vì sao Backend phải kiểm tra lại patch đã qua Agent guard?

## Checkpoint 7 — Review UI

**Đọc trước:** [Render integration](07-render-integration.md).

**Quan sát:** `AiAssistant.tsx`, `cv.service.ts`, editor store.

**Task:** thêm JD form, loading, diff cards, select/reject, apply và conflict state. Tailor request đi qua Backend.

```powershell
Set-Location D:\Projects\Render\MODULE_FE
npm test
```

**DoD:** không auto-apply; chỉ validated + selected patches được gửi; success hydrate version/document mới; 409 yêu cầu tạo lại preview.

**Tự hỏi:** review state nào nên local, state nào vào global editor store?

## Checkpoint 8 — E2E và evaluation

**Đọc trước:** [Evaluation](06-guardrails-and-evaluation.md).

**Task:** tạo golden cases vi/en cho IT Experience, chạy mock E2E mặc định và Gemini smoke test opt-in.

**Scenarios:** happy path, missing evidence, fabricated metric, skill chỉ có trong JD, locked CV, stale version, Agent timeout, empty retrieval.

**DoD:** đạt ngưỡng MVP trong chương 6; không có secret/PII trong fixture/log; kết quả evaluation được lưu dưới dạng aggregate report.

**Tự hỏi:** metric nào thay đổi khi prompt/model/retriever đổi?

## Nhật ký checkpoint mẫu

```markdown
### Checkpoint N — YYYY-MM-DD
- Dự đoán trước khi chạy:
- Kết quả thực tế:
- Root cause của lỗi:
- Thay đổi nhỏ đã thực hiện:
- Test chứng minh:
- Điều tôi hiểu thêm:
- Việc còn lại:
```

## Checklist hoàn thành toàn milestone

- [ ] Test chạy ổn định trên Python 3.12.
- [ ] Không còn hard-coded fixture path.
- [ ] Contract TypeScript/Python nhất quán.
- [ ] Agent không tạo unsupported fact.
- [ ] Static RAG có evaluation và citation.
- [ ] Preview không mutation.
- [ ] Apply có OCC/hash và atomicity.
- [ ] Review UI không tự động ghi CV.
- [ ] E2E và golden evaluation đạt ngưỡng.

