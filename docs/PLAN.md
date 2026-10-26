# Kế hoạch thực hiện: CV Tailor Agent

| | |
|---|---|
| **Phiên bản** | 0.1 (Draft) |
| **Ngày** | 2026-10-12 |
| **Dựa trên** | `PROPOSAL.md` v0.2 (mục 0: quyết định đã chốt) |
| **Giả định** | TypeScript, Zod, `yaml`, API công khai, RAG ngành để rỗng, chạy một lần (không hỏi lại) |
| **Ước lượng** | S = dưới nửa ngày, M = 1-2 ngày, L = 3-5 ngày (1 dev, chưa tính chờ quyết định) |

---

## 1. Tổng quan: 5 mốc, đi từ trong ra ngoài

Nguyên tắc sắp xếp: **làm phần chắc chắn trước, gắn LLM sau, mở ra công khai cuối cùng.** Mỗi mốc chạy được và kiểm tra được độc lập.

```
M1 Khung offline (không LLM)
 │   YAML vào → cây dữ liệu → YAML ra, giống hệt (round trip)
 ▼
M2 MVP viết lại (CLI)
 │   Core + Bonus(ghi chú gắn mục, chỉ dẫn) → viết lại STAR → Guard → cv.yaml + report.yaml
 ▼
M3 Bám theo JD
 │   Phân tích JD, chọn lọc, phát hiện xung đột, ghi chú chung, báo cáo đầy đủ
 ▼
M4 Dịch vụ công khai
 │   API, xác thực, rate limit, SSE, bảo mật PII, chống prompt injection
 ▼
M5 Chất lượng & vận hành
     Bộ đánh giá, theo dõi chi phí, triển khai, tài liệu
```

| Mốc | Kết quả kiểm tra được | Epic | Ước lượng |
|---|---|---|---|
| **M1** | `input.yaml` → `output.yaml` giống nguyên bản; sửa 1 bullet thủ công chỉ làm đổi đúng 1 dòng | E0, E1, E2 | ~4-6 ngày |
| **M2** | Chạy CLI trên CV mẫu: bullet được viết lại, số liệu giả bị Guard chặn, có báo cáo | E3, E4, E5, E6, E9, E10 | ~10-14 ngày |
| **M3** | Cùng CV, 2 JD khác nhau cho 2 kết quả khác nhau; xung đột được gắn cờ | E7, E8 | ~6-8 ngày |
| **M4** | Gọi qua HTTP có xác thực; vượt giới hạn bị từ chối; log không chứa nội dung CV | E11 | ~6-8 ngày |
| **M5** | Điểm đánh giá trên bộ mẫu; deploy được; có tài liệu | E12, E13, E14 | ~5-7 ngày |

Tổng khoảng **31-43 ngày làm việc** cho 1 người. E12 (đánh giá) nên chạy song song từ M2, không đợi M5.

### Sơ đồ phụ thuộc giữa các epic

```
E0 ─► E1 ─► E2 ─┬─► E4 ─┬─► E6 ─► E9 ─► E11 ─► E13
                │       │    ▲                  │
        E3 ─────┴───────┘    │                  ▼
        E5 ──────────────────┘                 E14
        E10 (khe cắm rỗng) ──► E6
        E7, E8 ──► (sau E6)
        E12: chạy song song, bắt đầu khi có E2
```

---

## 2. Hợp đồng dữ liệu (làm trước, mọi epic dựa vào đây)

| Khối | Vai trò | Ghi chú |
|---|---|---|
| `control` | Cách chạy: `jd`, `locale`, `industry`, `locked[]`, `max_bullets_per_entry`, `mode` | Bị gỡ khỏi đầu ra |
| `core` | Khung CV (`cv` + `sections`), schema riêng, **cho phép key lạ** | Là thứ in ra |
| `bonus` | Các ô: `notes[]` (có thể `attach_to`), `directives[]`, `references[]` | Không in ra |
| `Leaf` (nội bộ) | Một đoạn văn bản có thể sửa: `{path, text}` | Path ổn định, vd `cv.sections.experience[0].highlights[1]` |
| `Fragment` (nội bộ) | Một mảnh thông tin 1 ý rút từ Bonus: `{id, text, attach_to?, target?}` | Nguyên liệu viết lại |
| `Constraint` (nội bộ) | Chỉ dẫn đã cấu trúc hóa: `ban_terms`, `emphasize`, `tone` | Dùng cho prompt **và** Guard |
| `RewriteResult` | `{path, text, source_ids[]}` | LLM chỉ trả cái này |
| `report` | Thay đổi, nguồn, Bonus dùng/không dùng, cờ, từ khóa thiếu, điểm | Tách file khỏi CV |

---

## 3. Chi tiết theo Epic

### E0. Khởi tạo & nền tảng (M1)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E0-1 | Khởi tạo repo TypeScript, `pnpm`, tsconfig chặt (`strict`) | `pnpm build` chạy được | — | S |
| E0-2 | Lint + format + pre-commit | Commit lỗi bị chặn | E0-1 | S |
| E0-3 | Cấu trúc thư mục `src/{schemas,pipeline,llm,guard,industry,prompts,api}` | Khớp PROPOSAL mục 11.5 | E0-1 | S |
| E0-4 | Cấu hình bằng biến môi trường, kiểm bằng Zod | Thiếu biến bắt buộc thì dừng ngay khi khởi động, báo rõ biến nào | E0-1 | S |
| E0-5 | Vitest + thư mục `tests/golden` | `pnpm test` chạy 1 test mẫu | E0-1 | S |
| E0-6 | CI (chạy lint, build, test mỗi lần đẩy code) | CI xanh | E0-2, E0-5 | S |

### E1. Hợp đồng dữ liệu (M1)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E1-1 | Zod `Control` (mặc định hợp lý cho mọi trường) | Parse `{}` ra giá trị mặc định | E0 | S |
| E1-2 | Zod `Core`: danh tính bắt buộc, `sections` generic (tên bất kỳ), `passthrough` | Giữ nguyên key lạ qua parse | E0 | M |
| E1-3 | Zod `Bonus` 3 ô, `attach_to` là path hợp lệ tới Core | `attach_to` trỏ vào chỗ không tồn tại thì báo lỗi rõ | E1-2 | M |
| E1-4 | Kiểu nội bộ `Leaf`, `Fragment`, `Constraint`, `RewriteResult` | Có type + schema | E1-2 | S |
| E1-5 | Zod `Report` | Mô tả đủ các mục ở bảng trên | E1-4 | S |
| E1-6 | Giới hạn kích thước đầu vào (số ký tự, số entry, số ghi chú) | Vượt giới hạn trả lỗi có mã `INPUT_TOO_LARGE` | E1-2, E1-3 | S |
| E1-7 | Sinh JSON Schema từ Zod để frontend dùng | File `schema.json` được build tự động | E1-1…E1-5 | S |
| E1-8 | Bộ thông báo lỗi chuẩn (mã lỗi + path + gợi ý sửa) | Mọi lỗi kiểm tra có dạng thống nhất | E1-2 | S |

### E2. Lớp YAML, không LLM (M1)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E2-1 | Parse bằng `parseDocument`, bắt lỗi cú pháp kèm dòng/cột | Lỗi YAML trả vị trí cụ thể | E0 | S |
| E2-2 | Định nghĩa **quy tắc "lá có thể sửa"**: cấu hình được danh sách key (`highlights[]`, `summary`...) | Không hard-code tên section; section lạ có `highlights` vẫn được nhận | E1-2 | M |
| E2-3 | `collectLeaves()` duyệt cây, trả `Leaf[]` với path ổn định | Thứ tự và path lặp lại giống nhau giữa các lần chạy | E2-2 | M |
| E2-4 | Bỏ qua path nằm trong `locked` (hỗ trợ khớp tiền tố) | Khóa `education` thì không lá nào trong đó xuất hiện | E2-3 | S |
| E2-5 | `patch(doc, path, text)` ghi lại vào cây, giữ comment/thứ tự key | Diff chỉ đổi đúng dòng được sửa | E2-3 | M |
| E2-6 | Gỡ `control`, `bonus` khỏi tài liệu đầu ra | Đầu ra không còn 2 khối này | E2-5 | S |
| E2-7 | Serialize + parse lại + kiểm Zod `Core` | Đầu ra luôn hợp lệ trước khi trả | E2-6, E1-2 | S |
| E2-8 | **Test round trip** (10 file YAML mẫu, gồm key lạ, comment, Unicode tiếng Việt) | Vào = ra (không đổi gì), bất biến qua nhiều lần chạy | E2-1…E2-7 | M |

**Cổng M1:** E2-8 xanh. Chưa gọi LLM nào.

### E3. Lớp LLM (M2)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E3-1 | Interface `generateStructured<T>(schema, messages, opts)` | Không lộ kiểu riêng của provider ra ngoài | E1 | S |
| E3-2 | Provider Gemini | Trả JSON đúng schema trên 5 prompt mẫu | E3-1 | M |
| E3-3 | Provider OpenAI | Giống trên | E3-1 | M |
| E3-4 | Chọn provider/model bằng biến môi trường | Đổi biến là đổi provider, không sửa code | E3-2, E3-3, E0-4 | S |
| E3-5 | **Mock provider** trả đầu ra định sẵn | Toàn bộ test pipeline chạy không tốn tiền, không cần mạng | E3-1 | S |
| E3-6 | Retry (lỗi mạng/429), timeout từng call, hủy được | Mô phỏng lỗi thì thử lại tối đa N lần rồi báo lỗi | E3-1 | M |
| E3-7 | Xử lý đầu ra sai schema: thử lại 1 lần kèm thông báo lỗi, sau đó thất bại có kiểm soát | Không bao giờ ném JSON hỏng vào pipeline | E3-1 | M |
| E3-8 | Đếm token/chi phí mỗi call, **ngân sách mỗi yêu cầu** | Vượt ngân sách thì dừng, trả kết quả một phần + cờ | E3-1 | M |
| E3-9 | Nạp prompt từ file `.md` có version, điền biến, bọc dữ liệu người dùng trong khối có ranh giới | `prompts/rewrite.v1.md` được dùng, không nối chuỗi tùy tiện | E0-3 | M |

### E4. Chuẩn hóa đầu vào: bước ① ② ③ (M2, một phần M3)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E4-1 | Bước ①: kiểm tra Core + Bonus + Control, gom **mọi** lỗi một lượt | Một lần chạy báo hết lỗi, không báo từng cái một | E1, E2 | M |
| E4-2 | Tách `notes` thành `Fragment` (mỗi mảnh 1 ý), gắn id ổn định | Ghi chú dài 3 ý ra 3 mảnh | E1-4 | M |
| E4-3 | Ghi chú có `attach_to`: tìm mục Core tương ứng, kiểm tra tồn tại | Mảnh có `target` đã xác minh | E4-2, E2-3 | S |
| E4-4 | `directives` → `Constraint` (LLM cấu trúc hóa: `ban_terms`, `emphasize`, `tone`) | "Không nhắc công ty Y" ra `ban_terms: [Y]` | E3, E4-2 | M |
| E4-5 | Chỉ dẫn không hiểu được: ghi vào báo cáo, **không đoán** | Có trường `unparsed_directives` | E4-4 | S |
| E4-6 | **(M3)** Ghi chú chung (không `attach_to`): LLM đề xuất mục đích | Mảnh có `target` hoặc `unplaced` | E4-2 | M |
| E4-7 | `references`: lưu làm bằng chứng/đường dẫn, **MVP không đọc nội dung link** | Link xuất hiện trong báo cáo, không bị fetch | E1-3 | S |

### E5. Guard chống bịa: bước ⑧ (M2)

Guard là code thuần, không phụ thuộc LLM, test được độc lập.

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E5-1 | Xác định **kho chứng cứ hợp lệ** = văn bản Core + mảnh Bonus (không gồm JD, không gồm chỉ dẫn) | Hàm `buildEvidenceCorpus()`, chuẩn hóa (hoa/thường, bỏ dấu) | E4-2 | M |
| E5-2 | Luật **số liệu**: mọi số, %, tiền, m², năm trong câu mới phải có trong kho | Câu thêm "30%" không có nguồn bị từ chối | E5-1 | M |
| E5-3 | Luật **tên riêng**: công ty, trường, phần mềm, chứng chỉ trong câu mới phải có trong kho (hoặc danh sách trắng chung) | Câu thêm tên công ty lạ bị từ chối | E5-1 | L |
| E5-4 | Luật **`ban_terms`** từ chỉ dẫn | Câu chứa từ cấm bị từ chối | E4-4 | S |
| E5-5 | Luật **từ khóa JD không có bằng chứng**: không được xuất hiện, ghi vào `missing` | Từ khóa chỉ có trong JD bị từ chối | E5-1, E7-1 | M |
| E5-6 | Luật độ dài, rỗng, ngôn ngữ đúng `locale`, không chứa markdown/YAML lạ | Câu vi phạm bị từ chối | E1 | S |
| E5-7 | Luật **nguồn**: mỗi câu mới phải có `source_ids` hợp lệ (id Leaf gốc hoặc Fragment) | Câu không nguồn bị từ chối | E4-2 | S |
| E5-8 | Trả về **lý do từ chối cụ thể** để đưa lại cho vòng viết lại | Lý do dạng "số '30%' không có trong đầu vào" | E5-2…E5-7 | S |
| E5-9 | **Test đột biến**: chèn có chủ đích số/tên bịa vào đầu ra giả, xác nhận Guard bắt được | Tỉ lệ bắt ≥ 95% trên bộ mẫu | E5-2, E5-3, E3-5 | M |
| E5-10 | (Tùy chọn) LLM-judge `same_facts` cho câu có nghi vấn | Chỉ chạy khi luật cứng không kết luận được | E3 | M |

### E6. Viết lại: bước ⑦ + vòng sửa (M2)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E6-1 | Chia **đơn vị viết lại** = 1 entry (công việc/dự án) cùng Fragment gắn vào nó | Danh sách đơn vị, mỗi đơn vị nhỏ vừa call | E2-3, E4-3 | M |
| E6-2 | Prompt viết lại v1 (STAR, giữ số bullet, `locale`, chỉ dùng chứng cứ được đưa, trả `source_ids`) | `rewrite.v1.md` + schema đầu ra | E3-9 | M |
| E6-3 | Gọi song song các đơn vị có giới hạn đồng thời | Không vượt `p-limit`, một đơn vị lỗi không làm hỏng các đơn vị khác | E6-2, E3-6 | M |
| E6-4 | Đưa kết quả qua Guard (E5); câu không đạt gom theo đơn vị | Danh sách câu bị từ chối kèm lý do | E5 | S |
| E6-5 | **Vòng sửa**: viết lại đúng câu bị từ chối kèm lý do, tối đa 2 vòng | Vòng 3 không xảy ra | E6-4 | M |
| E6-6 | **Fallback**: sau 2 vòng vẫn thất bại thì **giữ nguyên câu gốc** + ghi báo cáo | CV không bao giờ xấu đi so với đầu vào | E6-5 | S |
| E6-7 | Giữ đúng số bullet và thứ tự (MVP không gộp/tách) | Số bullet vào = ra | E6-2 | S |
| E6-8 | Chế độ không có JD: chỉ chuẩn hóa văn phong | Chạy được với `control.jd` rỗng | E6-2 | S |
| E6-9 | Tôn trọng `locked` và `mode` | Path bị khóa không đổi dù LLM trả về | E2-4 | S |

### E7. Phân tích JD & chọn lọc: bước ⑤ ⑥ (M3)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E7-1 | Bước ⑤: JD → `{keywords có trọng số, yêu cầu bắt buộc/ưu tiên, seniority}` | Schema + prompt `jd-analyze.v1.md`, test trên 10 JD thật | E3 | M |
| E7-2 | Chuẩn hóa từ khóa (đồng nghĩa, viết tắt, vi/en) | "Revit"/"revit"/"REVIT" gộp một | E7-1 | M |
| E7-3 | Bước ⑥: chấm mức liên quan của từng mục Core và từng Fragment với JD | Điểm có giải thích ngắn | E7-1, E4 | M |
| E7-4 | Quyết định mảnh Bonus nào lên CV (ngưỡng liên quan + chỉ dẫn `emphasize`) | Mảnh không liên quan **không** lên CV | E7-3 | M |
| E7-5 | Truyền từ khóa JD + mảnh đã chọn vào bước viết lại | Cùng CV, 2 JD cho ra 2 bản khác nhau | E7-4, E6 | M |
| E7-6 | Tính `matched` / `missing` từ khóa dựa trên **đầu ra thật** | Số khớp với nội dung CV, không do LLM tự khai | E7-2 | S |
| E7-7 | Điểm khớp (`ats_match`): công thức rõ ràng, tái lập được | Cùng đầu vào cho cùng điểm | E7-6 | M |

### E8. Phát hiện xung đột: bước ④ (M3)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E8-1 | Trích sự kiện kiểm chứng được từ Core và Fragment (thời lượng, số lượng, chức danh, ngày) | Danh sách `claim` có kiểu | E4 | M |
| E8-2 | So sánh cùng chủ thể: khác biệt thì tạo `Conflict {a, b, loại}` | "3 năm" vs "2 năm" bị bắt | E8-1 | L |
| E8-3 | Chính sách: **Core thắng**, mảnh Bonus xung đột bị loại khỏi viết lại, gắn cờ | Không câu nào dựa trên mảnh xung đột | E8-2, E6 | S |
| E8-4 | Ghi cờ + câu hỏi gợi ý vào báo cáo | Người dùng đọc là biết cần xác nhận gì | E8-2 | S |

### E9. Báo cáo & xuất: bước ⑨ (M2 cơ bản, M3 đầy đủ)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E9-1 | Ghi nhận `changes[]`: path, trước, sau, nguồn, trạng thái (`ok` / `kept_original` / `rejected`) | Mọi thay đổi có mặt | E6 | M |
| E9-2 | `bonus_used` / `bonus_unused` kèm lý do | Mỗi mảnh Bonus xuất hiện đúng một nơi | E6, E7-4 | M |
| E9-3 | `flags[]`: xung đột, chỉ dẫn không hiểu, mục chưa xếp, lỗi từng phần | Có mã + mô tả + path | E8, E4-5 | S |
| E9-4 | `keywords.matched/missing`, `ats_match` | Đưa vào báo cáo | E7-6, E7-7 | S |
| E9-5 | Serialize `cv.yaml` + `report.yaml` | Hai file hợp lệ | E2-7, E1-5 | S |
| E9-6 | Chạy từng phần: nếu hết ngân sách/timeout, trả kết quả đã có + cờ `partial` | Không mất công việc đã làm | E3-8 | M |
| E9-7 | CLI `cvtailor run <input.yaml> -o <thư mục>` bọc toàn bộ pipeline (bổ sung, cần cho cổng M2) | Chạy từ đầu đến cuối ra `cv.yaml` + `report.yaml`; mã thoát khác 0 khi lỗi đầu vào | E9-5 | S |

### E10. Khe cắm ngành, RAG để rỗng (M2)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E10-1 | Interface `getIndustryContext(industry, jdProfile?) → {terms[], whitelist[], style_notes[]}` | MVP trả rỗng | E1 | S |
| E10-2 | Gọi hook ở bước chọn lọc và viết lại, và đưa `whitelist` vào Guard (E5-3) | Thêm dữ liệu giả vào thì hành vi đổi, không sửa code lõi | E10-1, E5-3, E6 | S |
| E10-3 | Định dạng file ngành (`industry/<tên>/pack.yaml`), chưa nạp nội dung thật | Có tài liệu định dạng | E10-1 | S |

### E11. Dịch vụ công khai (M4)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E11-1 | Endpoint `POST /v1/tailor` nhận YAML (hoặc JSON tương đương), trả `cv` + `report` | Gọi được bằng `curl` | E9 | M |
| E11-2 | **Giới hạn kích thước** body ở tầng HTTP, trước khi parse | Body quá lớn bị từ chối sớm | E11-1, E1-6 | S |
| E11-3 | Xác thực (API key hoặc đăng nhập) | Không khóa thì 401 | E11-1 | M |
| E11-4 | **Rate limit** theo người dùng + hạn mức chi phí/ngày | Vượt thì 429 kèm thời điểm thử lại | E11-3, E3-8 | M |
| E11-5 | Chế độ **SSE**: sự kiện `stage_started`, `stage_done`, `warning`, `result`, `error` | Frontend/bot hiển thị được tiến trình | E11-1 | M |
| E11-6 | Công việc dài: timeout tổng, hủy khi client ngắt kết nối | Ngắt kết nối thì dừng gọi LLM | E11-5, E3-6 | M |
| E11-7 | **Chống prompt injection**: khối dữ liệu có ranh giới, đầu ra ràng buộc schema, Guard chặn nội dung lạ, không chạy lệnh từ nội dung người dùng | Bộ test tấn công (xem E12-5) đều thất bại | E3-9, E5 | L |
| E11-8 | **Bảo vệ PII**: không log nội dung CV, che email/điện thoại trong log, không lưu sau khi trả (mặc định) | Kiểm tra log mẫu không có dữ liệu cá nhân | E11-1 | M |
| E11-9 | Mã lỗi và thông báo thống nhất, không lộ chi tiết nội bộ | Mọi lỗi theo một dạng | E1-8 | S |
| E11-10 | Endpoint sức khỏe + phiên bản schema (`schemaVersion`) | Client biết phiên bản đang gọi | E11-1 | S |

### E12. Đánh giá & kiểm thử (chạy song song từ M2)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E12-1 | Bộ mẫu: 10 CV ẩn danh + 10 JD (vi/en, các mức kinh nghiệm) | Thư mục `tests/eval/` | — | M |
| E12-2 | Tiêu chí đo: tỉ lệ Guard từ chối, tỉ lệ giữ nguyên, số liệu bịa lọt qua, độ phủ từ khóa, độ dài | Script in bảng tổng hợp | E12-1, E9 | M |
| E12-3 | Golden test cho từng bước, dùng mock provider | Chạy nhanh, không tốn tiền | E3-5 | M |
| E12-4 | Chạy đánh giá với LLM thật mỗi khi đổi prompt/model, so với lần trước | Báo cáo so sánh | E12-2 | M |
| E12-5 | **Bộ test tấn công**: Bonus chứa "bỏ qua mọi chỉ dẫn trước đó", JD chứa lệnh, ghi chú đòi bịa số | Agent không làm theo, báo cáo ghi nhận | E11-7 | M |
| E12-6 | Tiêu chí chấp nhận cho "chất lượng tốt" | **Cần quyết định của bạn** (câu 9 trong PROPOSAL) | — | S |

### E13. Triển khai & vận hành (M5)

| ID | Task | Đầu ra / Tiêu chí hoàn thành | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| E13-1 | Container hóa | Chạy được bằng một lệnh | E11 | S |
| E13-2 | Quản lý bí mật (API key LLM) ngoài mã nguồn | Không có key trong repo | E13-1 | S |
| E13-3 | Log có cấu trúc (không PII), số liệu: độ trễ từng bước, token, chi phí, tỉ lệ lỗi | Bảng theo dõi cơ bản | E3-8, E11-8 | M |
| E13-4 | Cảnh báo: chi phí/ngày vượt ngưỡng, tỉ lệ lỗi LLM tăng | Cảnh báo test được | E13-3 | M |
| E13-5 | Môi trường thử (staging) + quy trình đổi prompt/model có đánh giá trước | Đổi prompt phải qua E12-4 | E12-4 | M |

### E14. Tài liệu (M5)

| ID | Task | Đầu ra | Cỡ |
|---|---|---|---|
| E14-1 | Tài liệu hợp đồng YAML (Core, Bonus, Control) kèm ví dụ | `docs/contract.md` | M |
| E14-2 | Tài liệu API + mã lỗi + sự kiện SSE | `docs/api.md` | M |
| E14-3 | Hướng dẫn viết Industry Pack | `docs/industry-pack.md` | S |
| E14-4 | Hướng dẫn đổi prompt/provider an toàn | `docs/operations.md` | S |

---

## 4. Flow chi tiết từng bước (đầu vào, xử lý, đầu ra, xử lý lỗi)

### Bước ① Kiểm tra đầu vào `[E1, E2, E4-1]`
- **Vào:** YAML thô.
- **Xử lý:** kiểm tra kích thước → parse YAML → Zod `control`, `core`, `bonus` → kiểm `attach_to` có trỏ tới Core thật.
- **Ra:** `Doc` đã parse + danh sách lỗi (nếu có).
- **Lỗi:** gom hết lỗi cùng lúc, trả mã + path + gợi ý sửa; **dừng, không gọi LLM.** Đây là bước duy nhất được phép từ chối cả yêu cầu.

### Bước ② Chuẩn hóa Bonus `[E4-2, E4-4, E4-5, E4-7]`
- **Vào:** `bonus`.
- **Xử lý:** `notes` → `Fragment` (mỗi mảnh 1 ý, id ổn định); `directives` → `Constraint` (LLM cấu trúc hóa); `references` → lưu nguyên.
- **Ra:** `Fragment[]`, `Constraint`.
- **Lỗi:** chỉ dẫn không hiểu → vào `unparsed_directives`, không đoán; LLM hỏng → dùng Bonus nguyên văn làm một mảnh duy nhất, ghi cờ.

### Bước ③ Gắn vào Core `[E4-3, E4-6]`
- **Vào:** `Fragment[]`, cây Core.
- **Xử lý:** `attach_to` rõ → gắn thẳng; không có → (M3) LLM đề xuất mục, MVP để `unplaced`.
- **Ra:** mỗi `Fragment` có `target` hoặc `unplaced`.
- **Lỗi:** không chắc thì `unplaced`, **không gắn bừa.**

### Bước ④ Phát hiện xung đột `[E8]` (M3)
- **Vào:** Core + `Fragment` đã gắn.
- **Xử lý:** trích sự kiện kiểm chứng được → so cùng chủ thể.
- **Ra:** `Conflict[]`; mảnh xung đột bị loại khỏi viết lại.
- **Lỗi:** không so sánh được thì bỏ qua, không đoán. Core luôn thắng.

### Bước ⑤ Phân tích JD `[E7-1, E7-2]` (M3)
- **Vào:** `control.jd`.
- **Ra:** `JDProfile {keywords có trọng số, bắt buộc/ưu tiên, seniority}`.
- **Lỗi:** không có JD → bỏ qua bước ⑤ ⑥, chạy chế độ chuẩn hóa văn phong.

### Bước ⑥ Chọn lọc `[E7-3, E7-4]` (M3)
- **Vào:** `JDProfile`, Core, `Fragment`, `Constraint`.
- **Xử lý:** chấm liên quan; chọn mảnh lên CV; ưu tiên theo thứ tự **chỉ dẫn cấm/khóa > Core > Bonus > JD.**
- **Ra:** kế hoạch viết lại cho từng đơn vị (mảnh nào, từ khóa nào được phép nhấn).
- **Lỗi:** thiếu điểm thì dùng mặc định (giữ hết mục Core, không thêm Bonus).

### Bước ⑦ Viết lại `[E6]`
- **Vào:** đơn vị viết lại (entry + mảnh gắn vào + từ khóa được phép + `Constraint` + `locale`).
- **Xử lý:** gọi LLM theo schema `{path, text, source_ids}`, song song, có giới hạn đồng thời.
- **Ra:** `RewriteResult[]` ứng viên (**chưa** vào cây).
- **Lỗi:** timeout/lỗi một đơn vị → giữ câu gốc đơn vị đó; hết ngân sách → trả kết quả một phần (`partial`).

### Bước ⑧ Guard `[E5]`
- **Vào:** ứng viên + kho chứng cứ (Core + Bonus, **không có JD**).
- **Xử lý:** kiểm số liệu, tên riêng, `ban_terms`, từ khóa không bằng chứng, độ dài/ngôn ngữ, `source_ids`.
- **Ra:** `accepted[]`, `rejected[] + lý do`.
- **Vòng sửa:** `rejected` → quay lại ⑦ **chỉ cho các câu đó**, kèm lý do. Tối đa 2 vòng. Còn thất bại → giữ câu gốc, `status: kept_original`.

### Bước ⑨ Ghép và xuất `[E2, E9]`
- **Xử lý:** `patch` từng câu `accepted` vào cây → gỡ `control`, `bonus` → serialize → **parse lại + kiểm Zod** → dựng `report`.
- **Ra:** `cv.yaml`, `report.yaml`.
- **Lỗi:** kiểm lại thất bại thì **không trả CV hỏng**; trả bản gốc chưa sửa + lỗi `OUTPUT_INVALID` (đây là lỗi nghiêm trọng, cần cảnh báo vận hành).

### Vòng đời một yêu cầu qua API `[E11]`

```
Client ─POST─► [kích thước] → [xác thực] → [rate limit/hạn mức]
                    │
                    ▼
              ① → ② → ③ → ④ → ⑤ → ⑥ → ⑦ ⇄ ⑧ → ⑨
                    │ (mỗi bước phát sự kiện SSE: stage_started / stage_done / warning)
                    ▼
        result {cv, report}  hoặc  error {code, path, hint}
```
Ngắt kết nối → hủy các call LLM đang chạy. Mọi log chỉ ghi id yêu cầu, độ trễ, token; **không ghi nội dung.**

---

## 5. Quyết định cần bạn xác nhận (chặn task nào)

| # | Quyết định | Chặn | Mặc định tôi sẽ dùng nếu chưa trả lời |
|---|---|---|---|
| D1 | Tiêu chí "chất lượng tốt" (điểm ATS, tỉ lệ chấp nhận, tự đánh giá) | E12-6, E7-7 | Tỉ lệ số liệu bịa lọt qua = 0 và độ phủ từ khóa trên bộ mẫu |
| D2 | Có JD trong mọi lần chạy không | Ưu tiên E7 | Không bắt buộc, chế độ không JD vẫn chạy |
| D3 | Người dùng có xem báo cáo không | E9 mức chi tiết | Có, trả cùng CV |
| D4 | Hạn mức chi phí/thời gian mỗi lần chạy | E3-8, E11-4, E11-6 | 60 giây, ngân sách token cố định |
| D5 | Lưu CV sau khi trả kết quả không | E11-8, E13 | Không lưu |
| D6 | Chọn LLM mặc định (Gemini hay OpenAI) | E3-4 | Gemini, đổi được bằng biến môi trường |
| D7 | Framework API (Fastify hay NestJS) | E11 | Fastify |
| D8 | Cho phép tái cấu trúc bullet (gộp/tách) sau MVP | E6 mở rộng | Không, giữ số bullet |

---

## 6. Rủi ro lớn và cách giảm theo task

| Rủi ro | Giảm thiểu bằng |
|---|---|
| LLM bịa số/tên mà Guard bỏ sót | E5-9 (test đột biến), E12-2 (đo số bịa lọt qua) |
| Guard quá chặt, từ chối cả câu đúng (tiếng Việt, bỏ dấu) | E5-1 chuẩn hóa, E5-3 danh sách trắng, đo tỉ lệ từ chối ở E12-2 |
| Prompt injection qua Bonus/JD | E11-7, E12-5 |
| Chi phí vượt kiểm soát khi công khai | E3-8, E11-4, E13-4 |
| Đổi prompt làm chất lượng tụt mà không biết | E12-4, E13-5 |
| Ghi nhầm làm hỏng comment/định dạng YAML | E2-8 |
| Rò dữ liệu cá nhân qua log | E11-8, E13-3 |

---

## 7. Thứ tự làm đề xuất (tuần tự, 1 người)

1. **Tuần 1:** E0, E1, E2 → cổng M1 (round trip xanh).
2. **Tuần 2-3:** E3 (kèm mock), E5 (Guard, test đột biến), E4-1…E4-5.
3. **Tuần 3-4:** E6, E9 cơ bản, E10 → chạy CLI đầu tiên trên CV mẫu (cổng M2). Bắt đầu E12-1 và E12-3.
4. **Tuần 5-6:** E7, E8, E4-6, E9 đầy đủ → cổng M3.
5. **Tuần 6-7:** E11 (API, bảo mật, SSE) → cổng M4.
6. **Tuần 7-8:** E12-4/5, E13, E14 → cổng M5.

Nếu cần có thứ dùng được sớm nhất: dừng sau M2, chỉ cần thêm E11-1…E11-4 là có bản thử công khai giới hạn.
