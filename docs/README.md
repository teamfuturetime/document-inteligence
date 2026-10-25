# Tài liệu AI-02

Sản phẩm nhatquang 0.2.0 ngày 24/10: [kiến trúc thực](product/architecture.md), [runbook/demo/backup](product/runbook.md), [handoff](product/integration-handoff.md), [nguồn kế thừa](ml/source-lineage.md), [báo cáo kiểm chứng](reports/product-verification-2026-10-24.md). Tài liệu foundation là snapshot lịch sử.

Kế hoạch mới cho nhóm 5 người: [phân công và lịch 20/10 đến 28/12/2026](planning/team-delivery-plan-2026-10-20.md), kèm [khảo sát các nhánh thực tế](reports/branch-audit-2026-10-20.md). Kế hoạch mô tả bước phát triển PRODUCT_MVP tiếp theo; không đổi trạng thái implementation của foundation bằng việc có tài liệu mới.

Điểm vào: [README](../README.md), [onboarding](team/onboarding.md), [báo cáo bàn giao](reports/foundation-verification.md).

| Chủ đề | Tài liệu |
| --- | --- |
| Yêu cầu | [Scope](requirements/scope.md), [SRS](requirements/srs.md), [use cases](requirements/use-cases.md), [traceability](requirements/traceability.md) |
| Kiến trúc | [Overview](architecture/overview.md), [data contracts](architecture/data-contracts.md), [API](architecture/api.md) |
| Quyết định | [ADR index và decision log](adr/README.md) |
| Dữ liệu | [Dataset card](data/dataset-card.md), [annotation](data/annotation-guide.md), [split](data/split-policy.md) |
| AI/evidence | [Extraction](ml/extraction-strategy.md), [confidence](ml/confidence-policy.md), [evaluation](ml/evaluation-protocol.md), [taxonomy](ml/error-taxonomy.md), [versioning](ml/versioning.md) |
| Tests | [Test plan](testing/test-plan.md) |
| Nhóm | [Workflow](team/workflow.md), [roles](team/roles.md), [onboarding](team/onboarding.md) |
| Kế hoạch | [Backlog](planning/backlog.md), [milestones](planning/milestones.md), [risks](planning/risks.md) |
| Vận hành | [Local development](operations/local-development.md), [troubleshooting](operations/troubleshooting.md) |
| Quản trị | [GitHub setup](governance/github-setup.md), [licensing](governance/licensing.md) |

Giữ cấu trúc đích của yêu cầu, không gộp các tài liệu bắt buộc. Nội dung chi tiết có một nguồn chính; tài liệu khác dùng liên kết để tránh hai bản khác nhau.
