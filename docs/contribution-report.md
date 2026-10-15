# Báo cáo đóng góp — Nguyễn Công Trí (23001945)

Nhánh triển khai: `Công-Trí` (Git không cho phép khoảng trắng trong ref nên không
thể dùng tên nguyên văn `Công Trí`). Tổng cộng 40 commit thực chất so với
`origin/main`, theo đúng 8 nhóm trong đề.

| Nhóm | Phạm vi | Kết quả xác minh |
|---|---|---|
| 1 | Setup, architecture, Docker, pipeline, logging | compile + compose config |
| 2 | ERD, SQLAlchemy, migration, repository, search | unit tests |
| 3 | Upload, validation, OpenCV, PDF, deskew | unit tests |
| 4 | Paddle adapter, OCR service, boxes, Unicode, CER/WER | unit tests |
| 5 | Classification, schemas, extraction, orchestration, F1 | unit tests |
| 6 | Document/process/result/review APIs | integration tests |
| 7 | React upload, preview, review, history | TypeScript/Vite build |
| 8 | Integration, E2E, security, performance, docs | 19 tests + build |

Commit hash/message chính xác được lấy bằng:

```bash
git log --oneline origin/main..HEAD
git rev-list --count origin/main..HEAD
```

Các giới hạn chưa thể hoàn thành trung thực: chưa có dataset/ground truth, model
weights và staging 421 users, do đó chưa báo cáo accuracy/benchmark giả định.
