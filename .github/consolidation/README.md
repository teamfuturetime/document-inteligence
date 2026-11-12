# Gói GitHub chờ duyệt — chưa thực thi

Các file dưới đây là nội dung reviewable, không phải setting/issue đã tồn tại. Snapshot read-only: docs/evidence/github-snapshot.json. Remote main vẫn 94c5101, 0 Issues/milestones, PR #1 mở, #2 đã merged vào minhthao.

| File | Thao tác dự kiến |
|---|---|
| pull-request.md | Body PR chore/repository-consolidation→main; title: `chore(repo): consolidate the local invoice OCR product` |
| labels.json | Tạo 8 labels nếu chưa tồn tại; không sửa/xóa labels cũ |
| milestones.json | Tạo 3 milestones theo điều kiện hoàn thành, không due date/assignee |
| issues.json | Tạo 9 Issues CONS-01..09 sau dedup, dùng title/body/labels/milestone đã chuẩn bị |
| main-protection.json | PUT protection main sau khi gate Product checks đã quan sát; 1 review, strict checks, cấm force-push/delete, không ép linear history |

## Thứ tự sau khi có một lần duyệt cụ thể

1. Kiểm lại remote refs/PR/rulesets trước ghi. Nếu main hoặc nền thay đổi so snapshot, dừng phần ảnh hưởng và cập nhật/review kế hoạch; không force.
2. Push **chỉ** nhánh chore/repository-consolidation, không push --all, main hoặc nhánh mutant/bài tập.
3. Tạo PR với body file; ghi link PR #1 như nguồn nền, không tự merge hoặc đóng nó.
4. Đọc run/check-runs đúng head SHA; nếu gate thất bại phải sửa/commit bình thường và chạy lại, không hạ ngưỡng/skip.
5. Tạo labels/milestones/issues từ JSON sau khi đối chiếu trùng. Không gán người hoặc deadline giả. Có thể link issue thật vào PR sau khi có số thực.
6. Chỉ sau khi `Product checks` tồn tại trên workflow/run của PR, áp main-protection.json. Xác minh GET trả settings đúng payload. Không đổi default branch/quyền thành viên.
7. Merge PR và xử lý đóng PR #1 là bước sau review, **không nằm trong ủy quyền push/tạo backlog/protection**. Đọc lại #1 sau merge; nếu auto-delivered do ancestry thì không đóng giả hoặc đổi lịch sử.

Không có danh sách nhánh xóa trong gói này. Các candidate trong branch-inventory chỉ là xem xét sau, submission refs luôn giữ. Không thực thi lệnh ghi chỉ vì file này có ví dụ.

## Lệnh minh họa, không tự chạy

```sh
git push -u origin chore/repository-consolidation
gh pr create --repo teamfuturetime/document-inteligence --base main --head chore/repository-consolidation --title 'chore(repo): consolidate the local invoice OCR product' --body-file .github/consolidation/pull-request.md
gh api --method PUT repos/teamfuturetime/document-inteligence/branches/main/protection --input .github/consolidation/main-protection.json
```

Tạo issues/labels/milestones qua API dùng từng object JSON, không shell nội suy multiline. Kiểm tra duplicate và lưu các ID/URL trả về; không giả số issue trước khi tạo. Approval phải chỉ rõ có cho phép tất cả những thao tác nào trong các bước 2/3/5/6.
