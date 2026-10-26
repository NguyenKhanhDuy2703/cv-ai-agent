# Runbook cho Agent: thực thi PLAN tuần tự, test đến khi xong

| | |
|---|---|
| **Phiên bản** | 0.1 (Draft) |
| **Ngày** | 2026-10-12 |
| **Đọc kèm** | `PROPOSAL.md` (đặc tả), `PLAN.md` (task chi tiết, mã E*-*) |
| **Dành cho** | Một coding agent chạy tự động (vd Claude Code) trong repo `cvtailor/` |

Tài liệu này không thay `PLAN.md`. `PLAN.md` nói **làm gì**, runbook này nói **làm theo thứ tự nào, kiểm tra bằng gì, khi nào được đi tiếp, khi nào phải dừng**.

---

## 1. Chuẩn bị (người làm một lần)

1. Tạo repo `cvtailor/`, chép 3 file vào `docs/`: `PROPOSAL.md`, `PLAN.md`, `AGENT_RUNBOOK.md`.
2. Tạo `.env.example` (không đặt khóa thật vào repo). Khóa LLM thật **không bắt buộc** để chạy hết phần build, xem mục 7.
3. Đưa agent **prompt khởi động** ở mục 10.

---

## 2. Quy tắc vận hành (agent bắt buộc tuân thủ)

**Thứ tự và phạm vi**
1. Chỉ làm **một bước (Sxx) tại một thời điểm**, theo đúng thứ tự ở mục 5. Không nhảy cóc, không làm trước.
2. Không thêm tính năng ngoài `PLAN.md`. Thấy cần thêm thì ghi vào `PROGRESS.md` mục `ĐỀ XUẤT`, không tự làm.
3. Quyết định chưa chốt (D1-D8 trong `PLAN.md`): dùng **mặc định đã ghi**, ghi lại vào `PROGRESS.md`, không dừng chờ.

**Test là cổng, không phải thủ tục**
4. **Viết test trước, chạy thấy nó đỏ, rồi mới viết code.** Ghi lại một dòng "đỏ vì ..." trong sổ tiến độ.
5. Một bước chỉ được đánh dấu xong khi **cả 3 lệnh xanh**: `pnpm lint && pnpm typecheck && pnpm test`.
6. **Cấm làm test xanh bằng cách yếu đi:** không `.skip`, `.only`, `it.todo`, không nới `expect`, không xóa test, không sửa file trong `tests/golden/` để khớp kết quả sai. Test sai thật thì sửa kèm ghi lý do vào sổ tiến độ (`TEST_FIX: ...`).
7. **Cấm viết code lách test:** không nhúng đáp án của fixture vào `src/`, không rẽ nhánh theo tên file test.
8. Test đơn vị và e2e **chỉ dùng mock provider.** Không gọi LLM thật trong `pnpm test`.

**Sửa lỗi có giới hạn**
9. Test đỏ: sửa tối đa **3 lần cho cùng một lỗi.** Lần 3 vẫn đỏ thì **dừng bước**, ghi `BLOCKED`, theo mục 8.
10. Mỗi lần sửa phải dựa trên nguyên nhân đọc được từ lỗi, không đoán ngẫu nhiên. Ghi nguyên nhân gốc vào sổ.

**An toàn**
11. Không ghi khóa/bí mật vào repo hoặc log. Không log nội dung CV (PII).
12. Không thêm phụ thuộc mới ngoài danh sách ở `PROPOSAL.md` mục 11.2 mà không ghi lý do vào sổ.
13. Một bước = một commit nhỏ, thông điệp dạng `Sxx: <tóm tắt> (E*-*)`.

---

## 3. Vòng lặp mỗi bước

```
1. Đọc PROGRESS.md → xác định bước kế tiếp (Sxx).
2. Đọc các task E*-* của bước đó trong PLAN.md (mô tả + "Tiêu chí hoàn thành").
3. Viết test (theo cột "Test phải viết trước" ở mục 5). Chạy → phải ĐỎ.
4. Viết code tối thiểu để qua test. Chạy lại.
5. Đỏ → sửa (tối đa 3 lần/lỗi). Xanh → bước 6.
6. Chạy bộ kiểm chung: pnpm lint && pnpm typecheck && pnpm test
7. Tự rà theo checklist mục 4.
8. Cập nhật PROGRESS.md (mẫu ở mục 9). Commit.
9. Nếu bước vừa xong là GATE → chạy quy trình cổng (mục 6). Qua cổng mới đi tiếp.
10. Quay lại bước 1.
```

Dừng vòng lặp chỉ khi: hết bước, hoặc gặp điều kiện dừng ở mục 8.

---

## 4. Checklist tự rà (cuối mỗi bước)

- [ ] Test của bước đã từng đỏ trước khi code, và giờ xanh.
- [ ] Không có `.skip/.only/it.todo`, không còn `TODO`/`console.log` thừa.
- [ ] Mỗi tiêu chí "Hoàn thành" của task trong `PLAN.md` có ít nhất một test chứng minh.
- [ ] Lỗi trả ra có mã + path + gợi ý (theo E1-8), không ném lỗi trần.
- [ ] Không log nội dung CV; không có khóa trong diff.
- [ ] Phần mới có thể chạy lại nhiều lần cho kết quả giống nhau (không phụ thuộc thứ tự/thời gian/ngẫu nhiên).
- [ ] Sổ tiến độ ghi đúng kết quả thật của 3 lệnh, không ghi "chắc là xanh".

---

## 5. Hàng đợi bước tuần tự

Quy ước lệnh (tạo ở S00): `pnpm lint`, `pnpm typecheck`, `pnpm test` (unit + golden, dùng mock), `pnpm test:e2e` (CLI trên fixture, dùng mock), `pnpm eval` (LLM thật, **chỉ chạy tay**, cần khóa).

### Mốc 1: khung offline

| Bước | Task | Test phải viết trước | Qua khi |
|---|---|---|---|
| S00 | E0-1…E0-6 | Test khởi động: `pnpm test` chạy được 1 test mẫu; test cấu hình env thiếu biến thì lỗi rõ | 3 lệnh xanh; có CI; script `lint/typecheck/test/test:e2e/eval` tồn tại |
| S01 | E1-1, E1-2, E1-8 | `Control` parse `{}` ra mặc định; `Core` giữ key lạ; lỗi có dạng `{code, path, hint}` | Test xanh |
| S02 | E1-3…E1-7 | `attach_to` sai path báo lỗi; vượt giới hạn trả `INPUT_TOO_LARGE`; `schema.json` được sinh | Test xanh; file `schema.json` sinh bằng script |
| S03 | E2-1…E2-4 | Lỗi YAML có dòng/cột; section lạ có `highlights` vẫn nhận; path ổn định giữa các lần chạy; `locked` loại đúng nhánh | Test xanh |
| S04 | E2-5…E2-7 | Patch 1 lá chỉ đổi 1 dòng diff; comment/thứ tự key còn nguyên; đầu ra không còn `control`/`bonus`; đầu ra tự parse lại hợp lệ | Test xanh |
| S05 | E2-8 | 10 fixture YAML (key lạ, comment, tiếng Việt có dấu, Unicode): vào = ra, chạy 3 lần liên tiếp bất biến | **GATE M1** |

### Mốc 2: MVP viết lại (CLI)

| Bước | Task | Test phải viết trước | Qua khi |
|---|---|---|---|
| S06 | E3-1, E3-5 | Mock provider trả đầu ra định sẵn đúng schema; interface không lộ kiểu provider | Test xanh |
| S07 | E3-9 | Nạp prompt `.md` theo version; dữ liệu người dùng luôn nằm trong khối có ranh giới; thiếu biến thì lỗi | Test xanh |
| S08 | E3-6, E3-7, E3-8 | Mock mô phỏng: lỗi mạng→retry đủ N lần; timeout; JSON sai schema→thử lại 1 lần rồi thất bại có kiểm soát; vượt ngân sách→dừng + cờ | Test xanh |
| S09 | E3-2, E3-3, E3-4 | Provider thật kiểm bằng **HTTP giả** (không mạng): đúng request, đúng parse, đổi provider bằng env. Thêm smoke test sống, **tự bỏ qua khi không có khóa** | Test xanh; smoke sống ghi `LIVE_PENDING` nếu không có khóa (không chặn) |
| S10 | E4-1 | Một lần chạy báo hết mọi lỗi đầu vào; không gọi LLM khi đầu vào sai | Test xanh |
| S11 | E4-2, E4-3, E4-7 | Ghi chú 3 ý ra 3 mảnh id ổn định; `attach_to` gắn đúng mục; `references` không bị fetch | Test xanh |
| S12 | E4-4, E4-5 | "Không nhắc công ty Y" ra `ban_terms:[Y]` (mock); chỉ dẫn lạ vào `unparsed_directives` | Test xanh |
| S13 | E5-1, E5-6, E5-7 | Kho chứng cứ không chứa JD/chỉ dẫn; chuẩn hóa hoa-thường/bỏ dấu; câu rỗng, sai ngôn ngữ, không `source_ids` bị từ chối | Test xanh |
| S14 | E5-2 | Số/%/tiền/m²/năm không có trong kho bị từ chối; có trong kho thì qua | Test xanh |
| S15 | E5-3 | Tên công ty/trường/phần mềm lạ bị từ chối; có trong kho hoặc danh sách trắng thì qua; ca tiếng Việt có dấu | Test xanh |
| S16 | E5-4, E5-8 | Từ cấm bị từ chối; lý do từ chối cụ thể, đọc được | Test xanh |
| S17 | E5-9 | **Test đột biến:** ≥ 50 ca bịa có chủ đích (số, tên, từ cấm) | Guard bắt **≥ 95%**; còn lại ghi ca lọt vào sổ |
| S18 | E10-1…E10-3 | Hook mặc định trả rỗng; nạp dữ liệu giả thì whitelist/ghi chú đổi hành vi mà không sửa lõi | Test xanh |
| S19 | E6-1, E6-2 | Chia đúng đơn vị (entry + mảnh gắn vào); prompt v1 + schema `{path,text,source_ids}` | Test xanh |
| S20 | E6-3, E6-4, E6-7, E6-9 | Song song có giới hạn; 1 đơn vị lỗi không kéo cả mẻ; số bullet vào = ra; path `locked` không đổi dù mock trả về | Test xanh |
| S21 | E6-5, E6-6, E6-8 | Câu bị từ chối được viết lại với lý do, tối đa 2 vòng; vẫn hỏng thì giữ câu gốc; không JD vẫn chạy | Test xanh |
| S22 | E9-1, E9-2, E9-3, E9-5, E9-6 | Báo cáo đủ `changes`, bonus dùng/không dùng, `flags`; hết ngân sách trả `partial` | Test xanh |
| S23 | E9-7 (CLI) | E2E: `cvtailor run fixture.yaml -o out/` ra `cv.yaml` + `report.yaml` hợp lệ; chạy 2 lần cùng mock cho cùng kết quả | `pnpm test:e2e` xanh |
| S24 | E12-1…E12-3 | 10 CV + 10 JD tổng hợp (không dữ liệu cá nhân thật); script đo; golden test từng bước | **GATE M2** |

### Mốc 3: bám theo JD

| Bước | Task | Test phải viết trước | Qua khi |
|---|---|---|---|
| S25 | E7-1, E7-2 | JD → `JDProfile` đúng schema (mock); "Revit/revit/REVIT" gộp một | Test xanh |
| S26 | E7-3, E7-4, E7-5 | Mảnh không liên quan **không** lên CV; cùng CV + 2 JD khác nhau cho 2 kết quả khác nhau | Test xanh |
| S27 | E7-6, E7-7, E5-5 | `matched/missing` tính từ đầu ra thật; từ khóa chỉ có ở JD bị Guard chặn; điểm tái lập được | Test xanh |
| S28 | E8-1…E8-4, E4-6, E9-4 | "3 năm" vs "2 năm" bị bắt, Core thắng, mảnh xung đột không dùng; ghi chú chung được gắn hoặc `unplaced`; báo cáo đầy đủ | **GATE M3** |

### Mốc 4: dịch vụ công khai

| Bước | Task | Test phải viết trước | Qua khi |
|---|---|---|---|
| S29 | E11-1, E11-2, E11-9, E11-10 | `POST /v1/tailor` trả `cv`+`report`; body quá lớn bị từ chối trước khi parse; mọi lỗi cùng một dạng; có `schemaVersion` | Test xanh |
| S30 | E11-3, E11-4 | Không khóa → 401; vượt hạn mức → 429 kèm thời điểm thử lại | Test xanh |
| S31 | E11-5, E11-6 | Dòng sự kiện SSE đúng thứ tự (`stage_started/stage_done/warning/result/error`); client ngắt thì hủy call LLM; timeout tổng | Test xanh |
| S32 | E11-7, E12-5 | **Bộ tấn công:** Bonus/JD chứa "bỏ qua chỉ dẫn trước", lệnh ẩn, đòi bịa số; agent không làm theo, báo cáo ghi nhận | Mọi ca tấn công thất bại; test xanh |
| S33 | E11-8 | Quét log mẫu: không có nội dung CV, email/điện thoại bị che; mặc định không lưu sau khi trả | **GATE M4** |

### Mốc 5: chất lượng và vận hành

| Bước | Task | Test phải viết trước | Qua khi |
|---|---|---|---|
| S34 | E12-4 | Script đánh giá có LLM thật, có so sánh với lần chạy trước | Có script + `LIVE_PENDING` nếu không có khóa |
| S35 | E13-1…E13-3 | Container chạy bằng một lệnh; không có khóa trong repo (quét); log có cấu trúc, không PII | Test xanh; `docker build` thành công nếu có Docker, không thì `LIVE_PENDING` |
| S36 | E13-4, E13-5, E14-1…E14-4 | Cảnh báo kích hoạt được trong test; tài liệu có ví dụ chạy được (kiểm bằng test chạy thử ví dụ) | **GATE M5 (cuối)** |

---

## 6. Quy trình cổng (GATE)

Cổng là chỗ agent **không được tự chấm bài mình.** Tại mỗi GATE:

1. Chạy đầy đủ: `pnpm lint && pnpm typecheck && pnpm test && pnpm test:e2e`.
2. Quét tự động: không `.skip/.only/it.todo`; không file nào trong `tests/golden/` đổi mà thiếu dòng `GOLDEN_CHANGE` trong sổ; không khóa/bí mật trong diff.
3. Kiểm độ phủ: `src/guard` và `src/yaml` (lớp YAML) **≥ 90% dòng**.
4. **Khởi chạy một agent rà soát riêng (reviewer)** chưa từng thấy quá trình làm. Giao cho nó: danh sách tiêu chí cổng bên dưới + quyền chạy lệnh + chỉ đọc mã. Reviewer báo cáo đạt/không đạt từng mục, kèm bằng chứng (lệnh đã chạy, đầu ra).
5. Mọi mục không đạt → quay lại sửa, rồi chạy lại cổng từ bước 1 (tính vào giới hạn 3 lần).

**Tiêu chí cổng:**

| Cổng | Phải đúng |
|---|---|
| **M1** | Round trip bất biến trên cả 10 fixture; sửa 1 bullet chỉ đổi 1 dòng; đầu ra luôn qua Zod |
| **M2** | E2E bằng mock chạy được từ đầu đến cuối; đầu ra có `cv.yaml` + `report.yaml`; Guard bắt ≥ 95% ca đột biến; **không có ca nào lọt qua số liệu bịa trên bộ mẫu**; bullet thất bại giữ nguyên câu gốc; số bullet vào = ra |
| **M3** | 2 JD khác nhau cho 2 kết quả khác nhau; từ khóa JD không bằng chứng không xuất hiện trong CV mà nằm ở `missing`; xung đột được gắn cờ, Core thắng |
| **M4** | Không khóa → 401, vượt hạn mức → 429; SSE đúng thứ tự; ngắt kết nối hủy được call; toàn bộ ca tấn công thất bại; log không có PII |
| **M5** | Tài liệu đủ; container/CI chạy; script đánh giá tồn tại; toàn bộ `LIVE_PENDING` được liệt kê rõ cho người làm tiếp |

---

## 7. Xử lý khóa LLM thật

- **Không có khóa thì vẫn build được hết**, vì mọi test dùng mock. Phần cần khóa thật (smoke test sống S09, `pnpm eval` S34) ghi `LIVE_PENDING` và **không chặn** tiến độ.
- Có khóa: smoke test sống chỉ chạy khi đặt `RUN_LIVE=1`; mỗi lần chạy sống giới hạn **số call và token tối đa** (đặt trong env, mặc định thấp). Không bao giờ chạy sống trong `pnpm test`.
- Cuối dự án, người làm chạy `pnpm eval` bằng tay để biết chất lượng thật (mock chỉ chứng minh pipeline đúng, **không chứng minh chất lượng viết lại tốt**).

---

## 8. Điều kiện dừng và leo thang

Agent dừng, ghi `BLOCKED` vào sổ, và báo cho người khi:

| Tình huống | Hành động |
|---|---|
| Cùng một lỗi test đỏ sau 3 lần sửa | Dừng bước, ghi nguyên nhân đã thử + giả thuyết còn lại |
| Test mâu thuẫn với `PLAN.md`/`PROPOSAL.md` | Dừng, nêu rõ chỗ mâu thuẫn, **không tự chọn bên nào** |
| Cần quyết định ngoài D1-D8 và ảnh hưởng thiết kế | Dừng và hỏi |
| Phát hiện lỗ hổng bảo mật hoặc rò PII | Dừng ngay, mô tả, không đi tiếp |
| Cần thêm phụ thuộc lớn/trả phí ngoài kế hoạch | Dừng và hỏi |
| Tests flaky (lúc xanh lúc đỏ không đổi mã) | Dừng, tìm nguyên nhân (thường là thứ tự/thời gian/ngẫu nhiên), không "chạy lại cho xanh" |
| Guard bắt dưới 95% ca đột biến sau 3 lần chỉnh | Dừng, nộp danh sách ca lọt qua để người xem luật |

Khi dừng: **không đi tiếp sang bước sau**, không xóa thứ đang dở, để kho mã ở trạng thái build được.

---

## 9. Mẫu `PROGRESS.md` (agent tạo và cập nhật mỗi bước)

```markdown
# PROGRESS

## Trạng thái hiện tại
- Bước đang làm: S07
- Mốc gần nhất qua cổng: M1 (2026-10-14)

## Nhật ký
### S06 ✅ — E3-1, E3-5 — commit abc123
- Test đỏ trước khi code: "mock provider chưa tồn tại" ✔
- lint ✅ typecheck ✅ test ✅ (42 passed, 0 skipped)
- Quyết định mặc định đã dùng: D6 = Gemini
- Ghi chú: ...

### S05 ✅ — E2-8 — GATE M1
- Reviewer: đạt 3/3 tiêu chí (bằng chứng: <lệnh>, <kết quả>)

## BLOCKED
(trống)

## LIVE_PENDING
- S09: smoke test sống (thiếu khóa)

## TEST_FIX / GOLDEN_CHANGE
(trống)

## ĐỀ XUẤT (ngoài phạm vi, chưa làm)
- ...
```

---

## 10. Prompt khởi động (dán cho agent)

```
Bạn đang làm việc trong repo cvtailor/. Đọc theo thứ tự:
docs/PROPOSAL.md, docs/PLAN.md, docs/AGENT_RUNBOOK.md.

Thực thi hàng đợi bước ở mục 5 của AGENT_RUNBOOK.md, tuần tự từ S00, theo đúng
quy tắc mục 2 và vòng lặp mục 3. Mỗi bước: viết test trước và xác nhận nó đỏ,
rồi code, rồi chạy `pnpm lint && pnpm typecheck && pnpm test`. Chỉ đi tiếp khi xanh.
Cập nhật PROGRESS.md và commit sau mỗi bước. Tại các bước GATE, chạy quy trình
mục 6 và dùng một agent rà soát riêng chưa thấy quá trình làm.

Không tự chấm bài mình, không làm yếu test, không làm ngoài kế hoạch.
Gặp điều kiện ở mục 8 thì dừng và báo cáo. Bắt đầu từ S00 nếu PROGRESS.md chưa có.
Khi hoàn thành S36 và qua GATE M5, tóm tắt kết quả và danh sách LIVE_PENDING.
```

---

## 11. Giới hạn cần biết

- **Mock chứng minh pipeline đúng, không chứng minh chất lượng văn bản.** Chất lượng viết lại chỉ đo được ở bước chạy LLM thật (S34 và sau đó). Đừng coi "tất cả xanh" là "CV tốt".
- Ngưỡng 95% bắt ca đột biến và 90% độ phủ là **giả định ban đầu**; có thể chỉnh sau khi xem kết quả đầu tiên.
- Ước lượng thời gian của `PLAN.md` là cho người; agent chạy tự động thường nhanh hơn ở phần code nhưng vẫn cần người xem tại các GATE.
