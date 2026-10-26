# Glossary — Từ điển thuật ngữ CV AI Agent

Các định nghĩa dưới đây ưu tiên nghĩa đang dùng trong project, không cố bao quát mọi nghĩa học thuật.

## Agent

Hệ thống dùng model kết hợp workflow/công cụ để tạo kết quả. CV Agent hiện là fixed workflow agent, không phải agent tự lập kế hoạch vô hạn.

## Orchestrator

Thành phần điều phối thứ tự các bước và truyền dữ liệu giữa chúng. Ví dụ: validate → evidence → JD → retrieve → write → guard → patch.

## LLM

Large Language Model, mô hình sinh ngôn ngữ bằng cách dự đoán token. Gemini là LLM provider đầu tiên của project. LLM không phải nguồn sự thật cho CV.

## Prompt

Tập instruction và context gửi cho LLM. Prompt tốt nêu vai trò, input, giới hạn factuality và output schema.

## Token

Đơn vị text model xử lý, không hoàn toàn tương đương từ. CV/JD dài làm tăng token, latency và chi phí.

## Structured output

Output bị ràng buộc theo cấu trúc, thường là JSON Schema/Pydantic model. Nó bảo đảm hình dạng tốt hơn, không bảo đảm nội dung đúng sự thật.

## Schema

Định nghĩa cấu trúc và constraint của dữ liệu. Project dùng Zod, JSON Schema và Pydantic cho các runtime khác nhau.

## DTO

Data Transfer Object, object dùng để truyền dữ liệu qua API/layer boundary. Ví dụ `CanonicalTailorRequest`.

## Canonical document

Biểu diễn CV chuẩn được mọi thành phần chấp nhận. Nó gồm các stable section/entry IDs và dữ liệu cần cho render.

## Stable ID

Định danh không đổi khi UI reorder phần tử. Patch dùng `sectionId`/`entryId` thay vì chỉ dựa vào array index.

## Evidence

Dữ kiện lấy từ CV ứng viên như company, date, metric, technology hoặc bullet. Evidence có ID và source path.

## Grounding

Ràng buộc claim do AI tạo với evidence hoặc nguồn đã biết. Một proposal “grounded” phải trỏ tới evidence hỗ trợ nó.

## Hallucination

Output nghe hợp lý nhưng không có nguồn hỗ trợ. Trong CV, thêm `70%`, Kubernetes hoặc chức danh không có trong hồ sơ là hallucination.

## Guardrail

Luật/cơ chế kiểm tra hoặc chặn output rủi ro. Project dùng deterministic guard cho metric, skill, date, company, title và certificate.

## Semantic patch

Mô tả thay đổi theo ý nghĩa domain thay vì thay toàn document. Ví dụ thay bullet số 0 của Experience entry có stable ID cụ thể.

## Hash

Dấu vân tay một chiều của dữ liệu. `beforeHash` dùng SHA-256 của bullet cũ để phát hiện nội dung đã đổi trước apply.

## Optimistic Concurrency Control (OCC)

Cơ chế chỉ update nếu version vẫn giống lúc đọc. Nếu CV đã đổi, Backend trả `409 Conflict` thay vì ghi đè.

## Idempotency

Tính chất gửi lại cùng thao tác không tạo hậu quả lặp ngoài ý muốn. OCC ngăn nhiều request apply cũ cùng thành công; API lớn hơn có thể thêm idempotency key.

## Atomicity

Tất cả thay đổi cùng thành công hoặc cùng thất bại. Apply nhiều patches không được lưu một nửa.

## RAG

Retrieval-Augmented Generation: tìm knowledge chunks liên quan và đưa vào context LLM trước khi generate.

## Knowledge base

Kho kiến thức dùng chung, ví dụ hướng dẫn viết CV IT. Nó không chứa candidate facts riêng tư trong thiết kế MVP.

## Chunk

Đơn vị knowledge nhỏ được index/retrieve. Một chunk nên có nội dung tập trung và metadata rõ ràng.

## Metadata

Thông tin mô tả chunk: language, industry, section, status, source, version. Metadata filter giúp giảm kết quả sai trước scoring.

## Embedding

Vector số biểu diễn text trong không gian ngữ nghĩa. Text gần nghĩa thường có vector gần nhau, nhưng độ gần không chứng minh factual correctness.

## Vector database

Database/index tối ưu lưu embedding và tìm nearest neighbors. pgvector mở rộng PostgreSQL để làm việc này.

## Lexical search

Tìm kiếm dựa trên token/từ khóa trùng khớp. `StaticKnowledgeRetriever` hiện dùng cách gần với lexical scoring.

## Vector search

Tìm kiếm dựa trên khoảng cách/similarity giữa embeddings, hữu ích khi query và tài liệu khác từ nhưng gần nghĩa.

## Hybrid search

Kết hợp lexical và vector results, thường kèm metadata filter và reranking.

## Reranking

Sắp xếp lại một nhóm candidates bằng scorer tốt hơn sau retrieval ban đầu. Nó tăng chất lượng nhưng thêm latency/chi phí.

## `top_k`

Số chunks đầu được trả về. Quá ít dễ bỏ sót; quá nhiều làm prompt nhiễu.

## Citation

Tham chiếu tới knowledge chunk đã dùng, ví dụ `knowledgeChunkIds`. Citation hỗ trợ audit nhưng không thay candidate evidence.

## Provenance

Thông tin nguồn gốc knowledge: nguồn, version, trạng thái duyệt và thời điểm cập nhật.

## SSE

Server-Sent Events, kết nối HTTP stream một chiều từ server tới client. Phù hợp hiển thị tiến độ nhưng không thay authentication hoặc job persistence.

## Sync API

Client chờ một response hoàn chỉnh trong cùng request. Đơn giản cho MVP nếu thời gian xử lý nằm trong timeout.

## Background job

Tác vụ được đưa vào queue/worker và trả job ID. Phù hợp cho xử lý lâu, retry hoặc cần persistence.

## Dependency injection

Truyền dependency từ bên ngoài thay vì tự tạo cứng trong class. Pipeline có thể nhận mock/Gemini provider và null/static retriever.

## Provider abstraction

Interface chung che giấu chi tiết Gemini hoặc provider khác. Business pipeline gọi một contract ổn định.

## Deterministic step

Bước cho cùng input cùng output, ví dụ hash và schema validation.

## Probabilistic step

Bước có thể cho output khác nhau, ví dụ LLM rewrite dù input giống nhau.

## Fallback

Hành vi thay thế khi component chính lỗi. JD Analyzer có thể dùng rule-based analysis; invalid canonical input thì không được fallback thành success.

## Golden dataset

Tập input và expected behavior do con người duyệt dùng cho evaluation/regression.

## Regression test

Test ngăn một lỗi đã sửa xuất hiện lại. Mỗi bug factuality nên có fixture tối giản.

## Precision

Trong các kết quả được hệ thống chọn/bắt, bao nhiêu là đúng. Guard precision thấp nghĩa là reject nhiều câu thật.

## Recall

Trong toàn bộ kết quả đúng cần tìm/bắt, hệ thống tìm/bắt được bao nhiêu. Guard recall thấp nghĩa là bỏ sót hallucination.

## Recall@K

Tỷ lệ expected chunks xuất hiện trong K kết quả retrieval đầu tiên. Dùng để đánh giá retriever.

## False positive

Hệ thống báo lỗi khi thực tế không lỗi. Ví dụ guard reject technology hợp lệ.

## False negative

Hệ thống bỏ qua lỗi thực tế. Ví dụ metric giả không bị guard phát hiện.

## P50/P95 latency

P50 là latency trung vị; P95 là mức mà 95% request nhanh hơn hoặc bằng. P95 phản ánh trải nghiệm các request chậm tốt hơn average.

## PII

Personally Identifiable Information: tên, email, số điện thoại và dữ liệu có thể nhận diện cá nhân. Không log raw CV/JD trong production.

## Prompt injection

Nội dung input cố khiến model bỏ qua luật hệ thống. JD và CV đều phải được coi là untrusted data, không phải instruction ưu tiên cao.

## Service bearer token

Secret Render Backend dùng để chứng minh quyền gọi CV Agent. Nó khác user session/JWT và không được gửi tới browser.

## Preview

Kết quả đề xuất chưa lưu. Preview endpoint không được mutation CV hoặc tăng version.

## Review

Bước người dùng xem old/new diff và chọn patch. System validation không thay thế review.

## Apply

Bước Render Backend kiểm tra lại patch, OCC/hash rồi lưu atomically và tăng CV version.

