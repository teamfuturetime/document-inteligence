# ADR-0001 — Monorepo và backend modular

**Status:** Applied for scaffold; PROVISIONAL cho sản phẩm cuối. **Links:** ENG-01/02.

**Context:** repo gần trống, cần thành viên chạy hai app và giữ contract đồng nhất. **Options:** nhiều repo cần đồng bộ release/contracts; monorepo dễ chạy CI/cross-change; plugin/DI framework thêm chi phí không cần. **Decision:** monorepo backend/frontend/contracts/data/docs; backend API/services/domain/adapters/evaluation. **Consequences:** PR có thể thay cả schema và UI; evaluator tái dùng offline, chỉ OCR/extraction có Protocol; storage thêm khi dùng. **Revisit conditions:** ranh giới nhóm/release khác hoặc package có người dùng độc lập cần tách.
