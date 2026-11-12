# Bài tập cá nhân và evidence lịch sử

Chỉ mục này bảo toàn nguồn gốc; không copy toàn report/runtime vào nền sản phẩm. Các submission refs phải giữ để link đã nộp tiếp tục dùng được. Đọc README tại **commit cố định** vì môi trường/contract khác nhau; không chạy chung harness như tính năng production.

| Bài | Nhánh / commit cố định | Source/evidence | Trạng thái so với nền chính |
|---|---|---|---|
| VT-042 / 23001920 | [codex/bt3-vt042-async-retry @9d38ae7](https://github.com/teamfuturetime/document-inteligence/tree/9d38ae7b88fb14774caa2ab3d4e59882ee0f757f) | homework/VT-042; backend/tests/test_async_retry_vt042.py | Production retry behavior cùng hai file nền; test port có chọn lọc, report giữ ở nguồn |
| VT-043 / xem tác giả tại nguồn | [bt3-vt043-autosave @55e9c74](https://github.com/teamfuturetime/document-inteligence/tree/55e9c74daed487af675a15c276bf6830448e6cea) | evidence/bt3-vt043; tests/integration/test_document_review.py | PR #2 đã vào minhthao; chưa port autosave sang docintel |
| VT-044 / 23001945 | [bt3/23001945-vt044 @3809193](https://github.com/teamfuturetime/document-inteligence/tree/3809193) | individual/VT044 | Contract/delete harness riêng, không là auth/delete API chính |
| VT-045 / 23001948 | [hw3/23001948-vt045-config-contract @69106d4](https://github.com/teamfuturetime/document-inteligence/tree/69106d4) | homework/VT-045, output/pdf/BT3_23001948_VT-045.pdf | Config policy khác contract, giữ tham chiếu |
| VT-046 / 23001950 | [feat/vt046-validation-notification @31a18bb](https://github.com/teamfuturetime/document-inteligence/tree/31a18bb13f04ff8fe8259cabde542c49993a2327) | backend/tests/test_notifications.py; backend/experiments/README.md | Stateless validation notification chưa port sang persisted workflow; PDF/evidence của Tùng local output/, không commit theo yêu cầu |

Không công bố lại bài của thành viên dưới tên người khác; không sửa baseline, mutation results hoặc ground truth lịch sử. Nhánh mutant local dbef11a (VT-046) không thuộc nhánh nộp/sản phẩm và không push.
