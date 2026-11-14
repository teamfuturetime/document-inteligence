# Kế hoạch kiểm thử

Kế hoạch nền FOUNDATION dưới đây giữ bối cảnh lúc viết. Nghiệm thu sản phẩm hiện hành dùng [ma trận tích hợp](integration-acceptance.md), phân biệt tests có sẵn, native workflow và ca PDF/autosave/notification còn chờ. README là nguồn runtime/commands; không lấy mô tả CI foundation bên dưới thay workflow hiện tại.

| Yêu cầu | Kiểm tra foundation | Kiểm tra khi MVP thực sự triển khai |
| --- | --- | --- |
| MVP-02/05/06 | Schemas/examples, strict types/extra, draft missing/invalid, ID giữ 0, NFC/dấu Việt, ngày tồn tại/liên trường, final confirmed/required | Schema mới/rules/domain regression, persisted export gate |
| MVP-01/02, ENG-04 | Fixture explicit, unconfigured503/ocr false, inference không đọc gold, span references/bounds | Provider readiness/failure/timeout/no fallback, OCR và mapping trên sample |
| EVD-01 | Manifest paths/IDs/checksums/duplicate files/parent overlap và unreadable null | Review labels độc lập, template/near-duplicate leakage, version audit |
| EVD-02 | TP/FP/FN, missing/extra/absent/unreadable/zero, test50/48/45, model/fixture provenance | Batch model benchmark chốt config/split, buckets/support/latency |
| MVP-04, ENG-04 | UI banner, read-only/disabled, loading/error/empty/retry và evidence highlight | Keyboard/focus, edit/clear/save/retry/stale revision/re-OCR/confirm |
| ENG-03 | Ruff/ESLint/Prettier/types/tests/build, contracts drift, docs links/YAML/config parse | Playwright E2E thật upload→review→confirm→export, persistence/recovery |

pytest/Vitest là tests nền, không mock AI rồi gọi end-to-end model. Không dựng Playwright suite hình thức cho luồng chưa có. Browser smoke thật của trang foundation chỉ kiểm tra UI/runtime, không AI. Khi persistence/review/export có thì E2E/chống stale/xóa null/mất mạng bắt buộc. Không thêm coverage threshold tùy ý.

CI backend-checks/frontend-checks trên PR/push main, không key/GPU/model download; frozen installs và permission contents read. Model benchmark manual workflow sau BL-009, không coi skipped là passed quality. [Báo cáo](../reports/foundation-verification.md) phân checks local/remote/blocked, không che exit code.
