# GitHub setup

Remote đã tồn tại `https://github.com/teamfuturetime/document-inteligence.git`, default main được đọc bằng git ls-remote. Chưa push thay đổi, chưa tạo issue/PR/mời người, chưa bật required checks/ruleset/Actions qua tài khoản hay kiểm tra settings. Có file workflow/templates **cục bộ**, không chứng minh remote CI chạy.

- [ ] Người có quyền xác nhận owner/repo name/visibility hiện tại, quyền nhóm và chính sách công khai.
- [ ] Thêm thành viên/quyền phù hợp khi được ủy quyền, handles thật TBD.
- [ ] Xác nhận Actions được phép, push PR chạy workflow, ghi run URL/kết quả thật.
- [ ] Dùng required checks ổn định `backend-checks`, `frontend-checks` sau khi chúng xuất hiện; check names trong giao diện phải xác minh.
- [ ] Ruleset/branch protection main: review của người khác khi có reviewer, cấm force-push/delete theo gói/quyền.
- [ ] Nếu cần CODEOWNERS, tạo từ `.github/CODEOWNERS.example` với accounts có quyền thật; file này không tự bật mandatory review.
- [ ] Labels/milestones/project board tùy nhóm, tránh tạo hàng loạt không ủy quyền; forms nền không phụ thuộc labels.
- [ ] Secrets chỉ thêm khi tính năng thật cần; không key/GPU cho CI foundation, không privileged pull_request_target chạy code không tin.
- [ ] Thiết lập kênh báo bảo mật riêng, license/nguồn assets và deadline/owners khi biết.

Workflow permission contents read, Actions pinned bằng SHA được đọc từ refs tags chính thức; không fake SHA. [CODEOWNERS docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners), [Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use). Checklist là việc cần người có quyền thực hiện, chưa là setting đã bật.
