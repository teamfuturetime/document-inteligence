# Tài liệu hiện hành

Bắt đầu tại [README root](../README.md). Nền sản phẩm docintel/SQLite/pipeline đã có trên `main`; tạo nhánh task từ main mới nhất. Foundation reports, snapshot consolidation và các nhánh cá nhân là lịch sử có nguồn gốc.

| Cần làm gì | Nguồn chuẩn |
|---|---|
| Cài, cấu hình, chạy, check | [README root](../README.md), scripts/dev.py |
| Phát triển/PR/review | [CONTRIBUTING](../CONTRIBUTING.md), [GitHub approval package](governance/github-setup.md) |
| Nhận việc và phối hợp môn học trên GitHub | [Hướng dẫn thành viên](team/github-collaboration.md), [quy ước agent](../AGENTS.md) |
| Kiến trúc sản phẩm | [product/architecture](product/architecture.md), [contracts](../contracts/README.md) |
| OCR/evidence/metrics | [source lineage](ml/source-lineage.md), [protocol](ml/evaluation-protocol.md), [dataset](../data/product/README.md) |
| Demo/backup | [runbook](product/runbook.md) |
| Quyết định nền và port | [ADR0008](decisions/0008-primary-invoice-platform.md), [audit](repository-audit.md), [inventory](branch-inventory.md), [migration](consolidation-plan.md) |
| Kết quả thực tế | [consolidation verification](consolidation-verification.md), [GitHub publication](github-publication.md) |
| Bản đồ code | [STACK](codebase/STACK.md), [STRUCTURE](codebase/STRUCTURE.md), [ARCHITECTURE](codebase/ARCHITECTURE.md), [CONVENTIONS](codebase/CONVENTIONS.md), [INTEGRATIONS](codebase/INTEGRATIONS.md), [TESTING](codebase/TESTING.md), [CONCERNS](codebase/CONCERNS.md) |
| Bài tập cá nhân | [Chỉ mục bảo toàn](../homework/README.md) |

## Lịch sử, không dùng như hướng dẫn chạy chính

`reports/`, `planning/team-delivery-plan-2026-10-20.*`, ADR0001..0007 và các tài liệu FOUNDATION/contract_fixture giữ context tại thời điểm tạo. [Product verification 24/10](reports/product-verification-2026-10-24.md) là evidence cũ có model/runtime riêng; [foundation verification](reports/foundation-verification.md) không còn mô tả toàn bộ sản phẩm. Requirements/traceability giữ IDs; scope/product-traceability được đọc cùng ADR0008, không suy những BL cũ chưa có tính năng từ văn bản lịch sử.
