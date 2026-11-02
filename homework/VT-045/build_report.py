"""Build the standalone VT-045 submission: 8 main pages + log/AI appendices."""

from datetime import datetime
from html import escape
import hashlib
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
E = HERE / "evidence"
OUT = ROOT / "output/pdf/BT3_23001948_VT-045.pdf"
FONT_DIR = Path("C:/Windows/Fonts")
BRANCH = "https://github.com/teamfuturetime/document-inteligence/tree/hw3/23001948-vt045-config-contract"
BASELINE = "52067697c1e4505eb36042e5fbe525ed984d2637"
RED = "6e96e302f3e8c97920e8da660e166357f1ec94fa"
PATCH = "178cd3abac8af94be089ae45ca15a911d782a5f0"

for name, file in [("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"), ("Arial-Italic", "ariali.ttf"), ("Mono", "consola.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold")
INK = colors.HexColor("#172D43")
BLUE = colors.HexColor("#185D80")
GRAY = colors.HexColor("#566575")
STYLES = {
    "body": ParagraphStyle("body", fontName="Arial", fontSize=10, leading=14, spaceAfter=7, textColor=INK),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8.4, leading=11.2, spaceAfter=5, textColor=INK),
    "title": ParagraphStyle("title", fontName="Arial-Bold", fontSize=21, leading=26, spaceAfter=13, textColor=INK),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=12.5, leading=17, spaceBefore=7, spaceAfter=7, textColor=BLUE),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8, leading=10.5, spaceAfter=0, wordWrap="LTR", textColor=INK),
    "head": ParagraphStyle("head", fontName="Arial-Bold", fontSize=8, leading=10.5, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.1, leading=9.2, spaceAfter=8, textColor=INK),
}
story = []
def p(text, style="body"):
    story.append(Paragraph(text, STYLES[style]))
def h(text):
    p(text, "h2")
def code(text):
    story.append(Preformatted(text, STYLES["code"]))
def table(headers, rows, widths):
    content = [[Paragraph(escape(str(x)), STYLES["head"]) for x in headers]]
    content += [[Paragraph(escape(str(x)), STYLES["cell"]) for x in row] for row in rows]
    t = Table(content, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LINEBELOW", (0,1), (-1,-1), .35, colors.HexColor("#D5DEE5")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F6F8")]),
    ]))
    story.append(t)
    story.append(Spacer(1,8))
def page(title):
    if story:
        story.append(PageBreak())
    p(title, "title")
def link(label, url):
    return f'<link href="{escape(url, quote=True)}" color="#185D80">{escape(label)}</link>'

load = json.loads((E / "load.json").read_text(encoding="utf-8"))
mutation = json.loads((E / "mutation.json").read_text(encoding="utf-8"))
coverage = json.loads((E / "coverage.json").read_text(encoding="utf-8"))
reflection = (HERE / "reflection.txt").read_text(encoding="utf-8").strip()
word_count = len(reflection.split())
assert 250 <= word_count <= 350, word_count
assert mutation["killed"] and load["all_rounds_meet_target"]
assert "561 passed" in (E / "green.txt").read_text(encoding="utf-8")

page("BT cá nhân 3 · AI-02 · VT-045")
p("Cấu hình nghiệp vụ và bằng chứng contract testing", "h2")
table(["Thông tin", "Giá trị"], [
    ["Sinh viên / MSSV", "Nguyễn Ngọc Tuấn / 23001948"],
    ["Nhóm / vai trò / đề tài", "SE2026-T11 / Thành viên / AI-02 - Document Intelligence cho biểu mẫu tiếng Việt"],
    ["Repository", "https://github.com/teamfuturetime/document-inteligence.git"],
    ["Baseline commit", BASELINE],
    ["Commit test-first / patch", RED[:12] + " / " + PATCH[:12]],
], [133, 378])
p(link("GitHub branch chứa code, test, README và evidence", BRANCH), "small")
p('<b>Cam kết:</b> “Tôi chịu trách nhiệm về toàn bộ code, test và nội dung bài làm; tôi đã khai báo việc sử dụng AI.”', "small")
h("Problem statement và phạm vi")
p("Đưa ngưỡng tổng tiền hóa đơn được chấp nhận vào một file JSON để thay chính sách mà không sửa Python ở nhiều nơi. Đây là policy bổ sung cho bài VT-045 trên R05, không phải giới hạn kế toán đã được stakeholder xác nhận. Mặc định giữ nguyên mọi giá trị hợp lệ của sales_invoice 1.0.0.")
h("Acceptance criteria")
for text in [
    "<b>AC1.</b> JSON có policy_version cố định và max_total_amount là integer từ 0 đến 9007199254740991; mặc định bằng giới hạn schema.",
    "<b>AC2.</b> Cùng process, chỉ đổi JSON từ 200000 xuống 100000 làm hóa đơn 125000 chuyển từ hợp lệ sang không hợp lệ; không restart.",
    "<b>AC3.</b> Amount ≤ ngưỡng được giữ; vượt ngưỡng trả valid=false, amount=null và lỗi business.amount_exceeds_policy đúng field, không sửa input/trường khác.",
    "<b>AC4.</b> Config thiếu, hỏng, trùng key, sai kiểu/phiên bản hoặc không đọc được phải báo InvoicePolicyError; không trả dữ liệu mặc định. Harness trả 503 chỉ chứa error.",
    "<b>AC5.</b> Giữ contract năm field, envelope ValidationResult, VND-only, lỗi cũ và ranh giới giữa extraction thành công với business validity.",
]: p(text, "small")
h("Non-functional constraints")
p("NFC1: offline, dữ liệu tổng hợp, không thêm dependency production; snapshot bất biến mỗi call. NFC2: 100 tác vụ đồng thời, p95 ≤3,0 giây trong harness; kiểm tra mọi outcome. NFC3: lỗi config không lộ path/nội dung; triển khai bằng atomic replacement.", "small")

page("2. Contract và plan trước code")
h("Contract / invariants đã giải thích trước khi sửa")
p("Consumer là pipeline hiện có hoặc harness HTTP; provider là chuỗi normalization + validation. Với amount canonical a và ngưỡng M, policy chấp nhận khi a ≤ M. Policy chỉ thu hẹp acceptance, không nới giới hạn an toàn JSON. Lỗi dữ liệu cũ luôn chặn valid; valid phải khớp đủ field và không có errors.")
p("Vượt ngưỡng là kết quả nghiệp vụ có cấu trúc. Không đọc được config là lỗi hệ thống, không được thay bằng hóa đơn rỗng hoặc policy mặc định. HTTP 200 hay extraction succeeded không tự chứng minh hóa đơn hợp lệ.")
h("Plan v1 và review bằng repository thật")
table(["Đề xuất / assumption ban đầu", "Evidence và quyết định trước patch"], [
    ["Đưa ngưỡng policy vào Pydantic Amount", "Bác bỏ. docs/requirements.md, bảng total_amount và đoạn ngay sau: safe integer là giới hạn kỹ thuật, không phải nghiệp vụ. schemas/invoice.py dùng Amount chung cho hai model. Giữ schema; thêm policy ở service."],
    ["Thêm production /validate để test E2E", "Bác bỏ. app/main.py chỉ có GET /health; requirements R05 và architecture ghi validation API chưa có. Dùng executable harness riêng theo phương án đề cho phép."],
    ["Suy ra độ trễ VLM từ fake/validation", "Bác bỏ. README và architecture tách fake extraction, OCR và VLM. Chỉ kết luận về HTTP loopback validation."],
], [165, 346])
h("Plan đã sửa và phạm vi file")
p("Lưu baseline/v1/review; viết contract test red; thêm JSON + strict loader; áp policy sau canonical checks; chạy regression và coverage; mutation trong commit tạm; kiểm tra flaky/load; lưu traceability và xuất PDF.")
table(["File production", "Thay đổi"], [
    ["backend/config/invoice-policy.json", "Một nguồn cấu hình; default giữ tương thích."],
    ["services/invoice_policy.py", "Strict/frozen model, đọc JSON mới mỗi call, từ chối duplicate key, lỗi được sanitize."],
    ["services/validation.py", "Thêm policy_path tùy chọn; giữ API positional và envelope; thêm field issue khi quá ngưỡng."],
], [208, 303])
p("Đường dẫn services/ ở bảng là backend/app/services/. Test ở backend/tests/test_invoice_policy.py; harness, runner, plan và log ở homework/VT-045/. Không sửa main.py, schema hoặc frontend. docs/testing.md có sửa sẵn của người dùng, được giữ ngoài commit bài tập.", "small")
p("AI đã thực hiện repository review và kiểm tra diff; chưa có human peer review hay xác nhận stakeholder. Plan v1 và review nguyên văn được lưu trong branch; không giả lập một cuộc review của sinh viên.", "small")

page("3. Test strategy và test cases")
p("Risk chính: test chỉ xác minh status và bỏ sót business outcome. Contract tests dùng oracle literal từ requirements và AC, kiểm tra giá trị canonical, valid, field/code lỗi, nulling, input bất biến và error-only payload. Đây là contract service nội bộ + HTTP adapter; không tuyên bố dùng Pact hay phân tán nhiều dịch vụ.")
table(["Level", "Mục đích / lựa chọn"], [
    ["Unit", "Kiểu/version/range policy, biên inclusive, snapshot bất biến; feedback nhanh."],
    ["Integration / API", "File thật tạm -> loader -> normalization -> validation -> JSON. Consumer pipeline và TestClient đối chiếu đầy đủ contract."],
    ["Executable E2E harness", "Client HTTP thật -> Uvicorn -> service -> JSON file -> response. Kiểm chứng tải và outcome; chưa phải browser/product E2E."],
], [105,406])
p("Không cần thêm browser upload/review/export E2E vì chưa có chức năng tương ứng; không đo VLM trong lát cắt này. Test OCR cũ chỉ là regression. Không mock toàn bộ dependency hoặc thêm framework mới để có số lượng test.", "small")
h("Dữ liệu được chọn")
p("Invoice tổng hợp: ID 0000123, ngày 03/04/2026 với locale vi-VN, seller Cửa hàng Mây Việt, tiền 125.000 ₫. Expected canonical: ngày 2026-04-03, tiền125000, currency VND. Dữ liệu biên integer khai báo VND tường minh. Chọn partitions config hợp lệ/sai kiểu/sai version/missing/duplicate/unreadable và amount 0, M−1, M, M+1, safe limit, limit+1.", "small")
headers=["ID / AC", "Risk / level", "Precondition / input", "Expected result", "Ưu tiên"]
rows=[
 ["TC01 AC1,5", "Tương thích / integration", "Default; amount=safe limit", "valid=true; amount giữ nguyên; đúng 4 key envelope", "P0"],
 ["TC02 AC2", "Stale config / integration", "JSON 200000 -> 100000; amount=125000", "Pass -> invalid; amount null; đúng field/code lỗi", "P0"],
 ["TC03 AC3", "Off-by-one / unit+int.", "M=100000; 0, 99999, 100000, 100001", "Ba giá trị đầu hợp lệ; cuối bị từ chối; input/trường khác nguyên vẹn", "P0"],
 ["TC04 AC1,4", "Unsafe config / negative", "11 dạng JSON/type/version/key sai", "InvoicePolicyError; tuyệt đối không default", "P0"],
 ["TC05 AC4", "Nuốt lỗi / failure path", "Missing file; PermissionError", "Exception với message cố định, không invoice thành công", "P0"],
 ["TC06 AC5", "Lỗi cũ / negative", "USD;125,000;−1;safe limit+1", "Mã lỗi cũ đúng field; giá trị sai=null", "P0"],
 ["TC07 AC3,5", "Aliasing / contract", "Reject; JSON round-trip; đổi seller output", "Envelope round-trip đúng; input/next result không bị đổi", "P1"],
]
table(headers,rows,[60,97,127,190,37])

page("4. Test cases và traceability")
table(headers,[
 ["TC08 AC1,2", "Snapshot / unit", "Load M=0; assign; thay JSON", "Snapshot frozen; call mới đọc ngưỡng mới", "P1"],
 ["TC09 AC3,4", "Status-only / API", "Reject -> accept -> corrupt JSON", "200+invalid đầy đủ;200+values đúng;503+error-only", "P0"],
 ["TC10 NFC1", "Shared state / integration", "100 call xen kẽ 2 file;20 threads; đảo thứ tự", "Mỗi kết quả theo đúng policy riêng; không nhiễm state", "P1"],
 ["TC11 NFC1", "Time/CWD / unit+int.", "Cấm clock/sleep/random/network; đổi CWD", "Hai kết quả serialize giống nhau, không phụ thuộc CWD", "P1"],
 ["TC12 AC3", "Nhiều lỗi / integration", "M=0; amount=0 rồi amount=1 + USD", "0 hợp lệ; trường hợp sau đủ hai lỗi và null hai field", "P1"],
 ["TC13 AC3,5", "Consumer / pipeline", "Fake 125000; M=100000", "Extraction succeeded nhưng validation invalid; lỗi policy", "P0"],
 ["PERF01 NFC2", "Latency/outcome / E2E harness", "3 lượt x100 HTTP tasks;50 dưới+50 trên M", "Mọi outcome đúng; từng p95≤3s; không bỏ request lỗi", "P0"],
],[60,97,127,190,37])
p("TC01-TC13 được parameterize thành 30 pytest cases. PERF01 là experiment riêng, không cộng vào tổng 561 pytest. Có nhiều hơn 2 negative tests và failure-path gắn trực tiếp mutation/risk của VT-045.", "small")
h("Acceptance criterion / Risk → Test → File → Commit → Kết quả")
table(["AC / Risk", "Test cases", "File / commit / evidence"], [
 ["AC1 config hợp lệ", "TC01,04,08", "T; red 6e96e30 -> patch 178cd3a; green.txt,coverage.json"],
 ["AC2 reload JSON", "TC02,08", "T; red 6e96e30 -> patch 178cd3a; red.txt -> green.txt"],
 ["AC3 business outcome", "TC03,07,09,12,13", "T; patch 178cd3a; green.txt"],
 ["AC4 không nuốt lỗi", "TC04,05,09", "T; patch 178cd3a; mutation.json/.patch/.txt"],
 ["AC5 regression", "TC01,06,07,13 +531 cũ", "T và backend/tests; baseline 5206769 -> patch 178cd3a; baseline.txt,green.txt"],
 ["NFC1,3 flaky/safety", "TC05,07,08,10,11", "T; patch 178cd3a; repeat.json,repeat-1..5.txt"],
 ["NFC2 tải/p95", "PERF01", "experiments.py +harness.py; patch 178cd3a; load.json"],
],[102,111,298])
p("T = backend/tests/test_invoice_policy.py; test functions bắt đầu test_tcNN_. Evidence nằm trong homework/VT-045/evidence/. Tên hàm, dữ liệu, lệnh chạy và hash đầy đủ có trong branch và log. Link branch ở trang 1; test-strategy.md là bảng chi tiết có thể tra cứu.", "small")

page("5. Test-first: fail → patch → pass")
h("Baseline và test red đúng nguyên nhân")
p("Baseline 5206769: 531 test pass. Commit 6e96e30 lưu test/plan và log red trước production patch. Test TC02 gọi API service cũ, không phụ thuộc import module mới hay keyword chưa có: monkeypatch đường dẫn policy dự kiến, rồi thay JSON giữa hai lần gọi.")
code("# evidence/red.txt (trích)\nassert result.valid is False\nAssertionError: JSON-only policy change must reject\n125000 above 100000\nE assert True is False\n1 failed in 0.21s")
h("Patch nhỏ và diff review")
p("Commit 178cd3a thêm JSON/loader và 18 dòng thay đổi tại service validation. Loader strict, extra=forbid, frozen, từ chối key lặp; không cache. Canonical model kiểm tra trước; nếu amount hợp lệ về schema nhưng vượt policy thì thêm lỗi riêng rồi cơ chế cũ null field. Không thay schema hoặc default currency.")
code('policy = load_invoice_policy(path)\n# Canonical errors are collected first.\nif amount_is_canonical and amount > policy.max_total_amount:\n    errors.append(FieldIssue(\n        field="total_amount",\n        code="business.amount_exceeds_policy", ...))\n    failed.add("total_amount")')
p("Trích trên rút gọn điều kiện để giải thích; code thực thi chính xác nằm trong services/validation.py. Diff review kiểm tra scope, schema bounds, lỗi nhiều field, aliasing và nguyên tắc không tạo dữ liệu thành công khi config lỗi.", "small")
h("Một sai sót AI thực sự đã được sửa")
p("Lần chạy patch đầu có 4 fail và 556 pass: boundary fixture đổi amount từ chuỗi có hậu tố sang integer nhưng để currency=null. Requirements không cho tự đoán VND. Đã sửa fixture khai báo VND tường minh, giữ nguyên implementation normalization và assertion business outcome. Log first-patch-review.txt được giữ lại.")
h("Green và cách chạy lại")
code("# .venv Python, chạy tại root repository\npython -m pytest -c backend/pytest.ini backend/tests -q\n# evidence/green.txt\n561 passed in 4.98s\n# 531 existing + 30 VT-045 cases")
p("Không lấy lời khẳng định của AI làm evidence: log lưu command, exit code và stdout/stderr. TestClient không phải bằng chứng browser; kết quả tải HTTP riêng được báo ở trang 7.", "small")

page("6. Who tests the tests?")
h("Mutation đúng biến thể: nuốt exception, trả default")
p("Từ patch 178cd3a, tạo detached worktree và commit tạm " + mutation["temporary_commit"][:12] + ". Chỉ đổi exception handler của policy loader; không sửa test. Mutant trả policy mặc định có ceiling=safe integer thay vì báo lỗi. Source có deliberate bug không nằm trên nhánh nộp.")
code('except (OSError, ValueError, ValidationError) as exc:\n    # GOOD: raise InvoicePolicyError(...) from exc\n    # MUTANT:\n    return InvoicePolicy(policy_version="invoice-policy-1",\n                         max_total_amount=MAX_SAFE_INTEGER)')
table(["Test / oracle", "Kết quả dưới mutation"], [
 ["TC05 missing config phải raise", "FAILED: DID NOT RAISE InvoicePolicyError"],
 ["TC09 corrupt JSON phải503 và error-only", "FAILED: assert 200 == 503"],
], [254,257])
p("Mutation bị bắt bởi 2 assertion thực sự; đây là 1 mutation thủ công được chỉ định, không phải mutation score toàn diện. Worktree được xóa, giữ mutation.patch, hash và log. Một lần chạy đầu bị PermissionError ở pytest temp; runner không tính lỗi hạ tầng đó là kill. Đã dùng basetemp riêng và chạy lại đúng.", "small")
h("Line / branch coverage và risk coverage")
table(["Phạm vi", "Line", "Branch"], [
 ["Policy loader", "24/24 =100%", "4/4 =100%"],
 ["Validation service", "47/48 =97,92%", "23/24 =95,83%"],
 ["Toàn backend/app", "921/1003 =91,82%", "248/274 =90,51%"],
], [255,128,128])
p("Coverage lấy từ coverage.py 7.17.0 với --branch trên đủ 561 test. Dòng chưa chạy ở validation.py là nhánh schema.invalid_length; các CLI/nhánh khác của backend cũng chưa phủ hết. Không thêm test chỉ để đạt 100% hoặc suy ra correctness từ tỷ lệ.")
p("Risk coverage: AC1-AC5 đều có outcome oracle và traceability. AC4 có missing/permission/malformed config và mutation; AC3 có biên, nhiều lỗi, pipeline consumer và API. Các bằng chứng này vẫn chia sẻ tác giả AI, nên chưa thay thế review độc lập về domain.")
p("Sau mutation, nguyên bản policy loader vẫn raise InvoicePolicyError; source không chứa default fallback. Kết quả repeat trên nhánh tốt và diff review được lưu cùng evidence.", "small")

page("7. Flaky review và kiểm chứng tải")
h("Kiểm tra ít nhất hai nguy cơ flaky")
table(["Nguy cơ", "Kiểm tra / kết quả / giới hạn"], [
 ["Order và shared state", "TC07 output detached;TC08 frozen snapshot;TC10 100 call xen kẽ hai policy, 20 threads và đảo thứ tự. Không sửa chung config global ngoài monkeypatch được restore."],
 ["Time, random và network", "TC11 chặn clock/sleep/random/network, đổi CWD; outcome giữ nguyên. 5 lượt suite với hash seed 1/17/2026 đều 30 pass. TZ env thay đổi trên Windows không đủ chứng minh đổi timezone."],
 ["Concurrency", "Policy đọc một snapshot riêng, không cache mutable. 100 client tasks dùng start barrier trong load; chưa test atomic replacement đồng thời hoặc network filesystem."],
],[118,393])
h("Thiết kế phép đo")
p("Windows 11, CPython 3.13.7, HTTPX2 2.15.1, máy báo 18 logical CPUs; một Uvicorn process loopback. Route sync dùng ASGI threadpool mặc định. Mỗi lượt tạo 100 client tasks chờ cùng barrier, connection limit 100; 50 invoice 99999 và 50 invoice 100001 với M=100000. Không đồng nghĩa 100 worker xử lý cùng một thời điểm.", "small")
p("Đo từ trước client.post đến nhận đủ HTTP response, gồm connection/queueing; chỉ loại readiness check trước đo. p95 nearest-rank là mẫu thứ 95/100. Lưu đủ mọi latency, timeout/error và oracle; không lọc request thất bại. Oracle so sánh toàn bộ normalized_values, valid, errors, warnings và status.", "small")
table(["Lượt", "Tasks / đúng outcome", "p50 (s)", "p95 (s)", "Max (s)", "Đạt≤3s"], [
 [str(i), f"100 / {r['correct_outcomes']}", f"{r['p50_seconds']:.4f}", f"{r['p95_seconds']:.4f}", f"{r['max_seconds']:.4f}", "Có" if r["meets_target"] else "Không"]
 for i,r in enumerate(load["rounds"],1)
],[41,130,85,85,85,85])
p("Cả 300 request có outcome đúng; ba p95 đều nhỏ hơn 3,0 giây. Đây là workload tổng hợp qua HTTP thật local, không phải giả lập latency bằng sleep và không phải phép đo OCR/VLM.")
h("Giới hạn kết luận")
p("Chưa chứng minh 100 người dùng production, tải kéo dài, WAN, nhiều process, browser, xác thực, OCR/VLM inference hay SLO của toàn hệ thống. Benchmark chỉ hỗ trợ NFC2 trong phạm vi executable validation harness mà đề cho phép. Cần đo lại trên môi trường mục tiêu và workload thực trước khi suy rộng.")
code("./.venv/Scripts/python.exe homework/VT-045/experiments.py load\n# evidence/load.json: 3x100 requests, per-request latency+oracle")

page("8. Reflection và phần còn mở")
p(f"Reflection ({word_count} từ theo tách khoảng trắng). Bản nháp do AI hỗ trợ, khai báo trong phụ lục; sinh viên cần rà soát, sửa hoặc chấp nhận nội dung trước nộp. Không trình bày đây là lời kể trải nghiệm cá nhân chưa được xác nhận.", "small")
for para in reflection.split("\n\n"):
    p(escape(para))
h("Hai đầu ra AI chưa thể tin ngay")
p("(1) Plan đưa ngưỡng business vào schema có vẻ gọn nhưng nhầm giới hạn kỹ thuật với policy; đã bác bỏ bằng requirements. (2) Fixture boundary có vẻ hợp lệ nhưng thiếu currency evidence; đã sửa theo bốn failure thực tế. Cùng AI tạo code và tests vẫn có nguy cơ chia sẻ assumption sai.", "small")
h("Trạng thái và quyết định bàn giao")
p("Đã có executable slice, log fail/pass, mutation, coverage, repeat và tải. Ngưỡng nghiệp vụ thực tế vẫn cần nhóm xác nhận; shipped default bảo toàn baseline. R12 chưa tích hợp hash policy vào run_metadata: cùng run_id cũ có thể cho validation khác sau đổi JSON; không dùng metadata cũ làm audit đầy đủ cho policy mới.", "small")
p("Nhánh bài tập dùng để review; chưa merge. Chưa có human review hoặc nộp Google Classroom. Deadline và chính sách nộp lại theo Assignment. Chỉ dùng invoice tổng hợp; không tải model hoặc gọi dịch vụ AI ngoài để thực hiện patch.", "small")
p("Tài liệu nguồn: Lecture06 (27 slide và notes), Lecture07 (28 slide và notes), hw3.txt VT-045; requirements/architecture/code tại baseline nêu ở trang 1. Bài áp dụng Spec → Test → AI-assisted Change → Verify → Review. Phụ lục sau đây chỉ chứa AI Usage Log và evidence thực thi, không mở rộng nội dung chính.", "small")

page("Phụ lục A · AI Usage Log")
p("Công cụ AI: Codex agent trong IDE; exact serving model không được expose. Ngày 02/11/2026, Asia/Saigon. Python/pytest/coverage, Git, HTTPX2/Uvicorn và ReportLab là công cụ thực thi. Không có agent thứ hai hoặc reviewer AI độc lập.")
table(["Prompt thực tế", "Output được dùng"], [
 ["Đọc kỹ hai tài liệu Lecture06/07", "Đọc 55 slide và speaker notes; nguyên tắc engineering loop, ownership, risk-based testing, mutation."],
 ["đọc qua yêu cầu của bài tập sau (hw3.txt)", "Tóm tắt đúng VT-045, kỹ thuật/mutation/tải và định dạng nộp."],
 ["hãy thực hiện yêu cầu. lưu ý kỹ đầu ra", "Đối chiếu repo, giải thích contract/invariants trước code; plan, tests, patch, experiments, report. Không bịa prompt bổ sung của sinh viên."],
],[226,285])
h("Review / thay đổi / bác bỏ")
table(["Output của AI", "Quyết định và evidence"], [
 ["Policy ceiling trong schema", "Bác bỏ trước code; requirements total_amount phân biệt technical safety với business rule."],
 ["Production validation route", "Bác bỏ; baseline main.py chỉ health, R05 chưa có API. Harness riêng theo phương án đề cho phép."],
 ["Fixture integer + currency=null", "Sửa sau 4 failures; không tự default VND. Log first-patch-review.txt."],
 ["Bất kỳ mutation run exit1 đều là kill", "Bác bỏ; lần đầu lỗi pytest temp không hợp lệ. Require 2 failed assertions, dùng basetemp riêng."],
 ["Coverage100% hoặc load pass đủ kết luận", "Bác bỏ; giữ outcome oracle, prescribed mutation và giới hạn OCR/VLM/production."],
],[226,285])
h("Khai báo ownership")
p("Cùng một AI hỗ trợ code, test, repository review và bản nháp reflection. Sinh viên phải tự hiểu code, kiểm tra assumptions, rà soát diff và chịu trách nhiệm nội dung. Chưa có human peer review; không tuyên bố đã có xác nhận stakeholder, merge hay nộp bài. Không dùng lời AI nói đúng thay evidence.")
p("Log đầy đủ: homework/VT-045/AI_USAGE_LOG.md. Plan gốc: plan-v1.md; review: spec-and-plan-review.md. Không sao chép test plan/data/prompt/reflection của thành viên khác; dữ liệu test được tạo riêng cho biến thể này.", "small")

page("Phụ lục B · Log thực thi")
h("Baseline, red, lần sửa fixture và green")
code("# Baseline: tests excluding the new test file\n531 passed in 5.25s\n\n# Red: TC02 before production patch (commit6e96e30)\nassert result.valid is False\nE assert True is False\n1 failed in 0.21s\n\n# First patch review: preserved, not hidden\nFAILED test_tc03_boundary_contract[0-True]\nFAILED test_tc03_boundary_contract[99999-True]\nFAILED test_tc03_boundary_contract[100000-True]\nFAILED test_tc03_boundary_contract[100001-False]\n4 failed, 556 passed in 5.27s\n# Cause: integer fixture had currency=None, no suffix evidence.\n\n# Corrected fixture; full regression, branch coverage\n561 passed in 4.98s\n# .venv: pip check\nNo broken requirements found.")
h("Mutation có assertion fail, không tính lỗi hạ tầng")
code("# Detached temporary commit:\n" + mutation["temporary_commit"] + "\n# TC05\nE Failed: DID NOT RAISE InvoicePolicyError\n# TC09\n> assert failure.status_code == 503\nE assert 200 == 503\n2 failed in 0.51s\n# mutation.json\n\"killed\": true\n# Source on submission branch remains GOOD.")
h("Repeat và môi trường")
repeats = json.loads((E / "repeat.json").read_text(encoding="utf-8"))
for r in repeats["runs"]:
    p(f"Lượt{r['iteration']}: hash seed={r['hash_seed']}; TZ={r['TZ']}; exit={r['exit']}; 30 test pass.", "small")
p("Full commands, stdout/stderr và test line numbers nằm trong evidence/*.txt. Mutation patch và commit hash được giữ kể cả khi worktree tạm đã dọn. Việc thay đổi runner để dùng basetemp không thay production patch hoặc test oracle.", "small")

page("Phụ lục C · Log tải và dấu kiểm")
h("Trích load.json")
brief={k:load[k] for k in ["utc","platform","python","cpu_count","httpx2","concurrency","target_p95_seconds","policy_sha256","all_rounds_meet_target"]}
code(json.dumps(brief, indent=2, ensure_ascii=False).replace(load["python"], "3.13.7 (Windows AMD64)"))
for i,r in enumerate(load["rounds"],1):
    code(json.dumps({"round":i, **{k:r[k] for k in ["tasks","p95_seconds","max_seconds","correct_outcomes","meets_target"]}},indent=2))
h("Dấu kiểm SHA-256 của log gốc")
manifest=[]
for filename in ["baseline.txt","red.txt","green.txt","coverage.json","mutation.patch","mutation.txt","mutation.json","load.json","repeat.json"]:
    digest=hashlib.sha256((E/filename).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    manifest.append([filename,digest])
table(["Evidence file", "SHA-256"],manifest,[104,407])
p("Hash tính trên UTF-8 sau chuẩn hóa newline CRLF thành LF để đối chiếu qua Git; không là chữ ký tác giả. Đủ 300 bản ghi request nằm trong load.json; server warning/error log rỗng. Giá trị báo cáo lấy trực tiếp từ JSON này.","small")

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5DEE5"))
    canvas.line(42,39,A4[0]-42,39)
    canvas.setFont("Arial",8)
    canvas.setFillColor(GRAY)
    canvas.drawString(42,26,"23001948 · VT-045 · AI-02 · 02/11/2026")
    canvas.drawRightString(A4[0]-42,26, f"Nội dung chính {doc.page}/8" if doc.page<=8 else f"Phụ lục {doc.page-8}")
    canvas.restoreState()

OUT.parent.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=51,
                      title="BT3_23001948_VT-045",author="Nguyễn Ngọc Tuấn; AI assistance disclosed",pageCompression=1)
doc.build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(OUT)
expected=["BT cá nhân 3","2. Contract","3. Test strategy","4. Test cases","5. Test-first","6. Who tests","7. Flaky","8. Reflection","Phụ lục A","Phụ lục B","Phụ lục C"]
actual=[]
for i,page_obj in enumerate(reader.pages):
    text=page_obj.extract_text()
    actual.append(text.splitlines()[0])
    if i < len(expected) and expected[i] not in text:
        raise AssertionError(f"Unexpected pagination on page{i+1}: {text[:150]}")
assert len(reader.pages)==11,(len(reader.pages),actual)
print(json.dumps({"path":str(OUT),"pages":len(reader.pages),"main_pages":8,"appendix_pages":3,"reflection_words":word_count,"page_titles":actual},ensure_ascii=False,indent=2))
