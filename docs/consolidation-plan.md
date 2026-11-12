# Consolidation plan và trạng thái migration

Baseline: nhatquang a03ea309ada1480e537cb7de8936ad0d52d53698. Nhánh local: chore/repository-consolidation; không sửa nhánh của thành viên. Các mốc là điều kiện hoàn thành, không deadline hứa hẹn.

## Các phần hoàn chỉnh để commit

1. Audit/ADR/inventory: source+ancestry+exact-SHA CI, quyết định local single-user và chỉ mục bài tập. Không nhập nguyên source cạnh tranh.
2. Entry point/docs: root README + một bộ dev/check commands; cập nhật docs còn hiệu lực, dán nhãn historical cho foundation/plans/reports. Không đổi runtime/data paths/contracts.
3. Quality/CI: port test retry có lineage từ VT-042; offline backend/schema/data/evaluator regression, frontend, native workflow và browser E2E. Không path-skip required gate. Kiểm tra input sai/null/revision/restart/history.
4. GitHub approval package: nội dung PR/issues/labels/milestones + protection payload khớp workflow; không thực thi các thao tác ghi. Xử lý PR #1 bằng đường PR dependency minh bạch.
5. Clean checkout và nghiệm thu: cài lockfiles, test/API native thật, browser export JSON, eval frozen regression và native benchmark mới; log đúng SHA/config/runtime. Chỉ kết luận các checks đã thực sự chạy.

## Ma trận chuyển đổi

| Phần / nguồn | Trạng thái / làm gì | Điều kiện trước khi port |
|---|---|---|
| docintel/domain/SQLite/worker/evidence UI từ nhatquang | Giữ nguyên làm nền chính, toàn original commits là ancestors | Baseline + post-change native/revision/conflict/export/restart checks |
| Model pin lineage từ Tùng | Đã có trong nền; giữ attribution docs/ml/source-lineage.md | Không nhận là đóng góp mới; hashes bất biến |
| Retry admission VT-042 | Hai production files đã cùng nội dung; đã port nguyên test regression backend/tests/test_async_retry_vt042.py, không UI/personal report | Chạy test mới với real SQLite/storage, giữ sample doubles là doubles |
| PDF single-page từ core Tùng/congtri | Backlog P1; chưa port | ADR limit byte/page/pixel, geometry transform, timeout; contract regen + native/API/E2E; không claim PNG-only hiện tại có PDF |
| OCR autosave VT-043/minhthao | Backlog P1; manual draft hiện vẫn hoạt động | Map raw OCR correction vs field review, debounce/CAS/ACK ordering, conflict UI; giữ explicit-null và export revision |
| Notification VT-046 | Giữ nộp bài; backlog P2, chưa port | Chọn event sau transaction commit, delivery isolated/deadline; không reuse stateless validate hook như đã là persisted feature |
| Config policy VT-045/tuannguyen | Giữ bài/nhánh; backlog P2 | Map sales_invoice sang hoa_don, config version/response invariants/tests |
| Auth/ownership minhthao | P2, ngoài phạm vi local đã chốt; không loại bỏ source | Identity/CSRF/owner schema, migration/backup, authorization matrix + PostgreSQL real tests |
| CCCD/birth certificate congtri/minhthao | Giữ tại ref nguyên gốc, chưa quảng cáo nền mới hỗ trợ | Schema/evidence/data permission/quality review và contracts version |
| Đơn đề nghị nhatquang | Tiếp tục chạy trong cùng nền; không xóa | Native workflow và fixture tests vẫn chạy cả hai schema |
| Đơn sinh viên/VLM/OCR.space solo | Giữ ref nguyên gốc; chọn từng experiment khi có nhu cầu | API/key/model policy, no secret PRs, live-vs-mock evidence, dataset riêng |
| Bài tập/evidence VT-042..046 | Giữ links/commits; chỉ index trong homework/README.md | Không đổi submission refs, không copy runtime hoặc toàn evidence vào production |

## Main/PR/lịch sử

Giữ main làm default và stable target. PR #1 đang chứa nền nhatquang; không merge bây giờ. Chuẩn bị PR consolidation→main và ghi rõ PR #1 là baseline dependency. Sau review, lựa chọn chính là merge #1 bằng merge commit, cập nhật nhánh consolidation từ main (merge, không rebase/force), chạy checks đúng merge SHA, rồi merge consolidation. Như vậy #1 vẫn có công nhận và phần consolidation tách riêng. Nếu reviewer chọn một PR hợp nhất, phải đóng #1 bằng comment superseded có link, không âm thầm merge hai codebases. Cả hai thao tác đều đợi duyệt riêng trong gói cuối.

PR #2 đã merge vào minhthao theo ancestry; không đóng/mở lại hoặc gọi nó đã vào main. Autosave chuyển thành issue port có nguồn. Không cherry-pick toàn nhánh minhthao vào docintel.

Chỉ dọn nhánh sau khi main chứa phần được giữ hoặc có ref lưu trữ lâu dài và chủ nhánh xác nhận. Không tạo CODEOWNERS khi chưa có owner đồng ý; role trong báo cáo cũ không là ủy quyền ownership.

## Rủi ro và rollback

Không di chuyển/xóa code/data trong nền đã chọn; rollback bằng PR revert của commit consolidation, không reset lịch sử. SQLite/runtime không bị migration; backup trước thay đổi dữ liệu về sau. Không gọi metric Windows5.4 hoặc core Tùng là baseline macOS/Linux mới; evaluator regression trên frozen selected predictions và native run mới được phân biệt. Remote CI của nhánh consolidation chỉ có thể xác minh sau khi người dùng duyệt push.
