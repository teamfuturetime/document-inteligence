# ADR-0004 — Fixture mode explicit

**Status:** Applied for scaffold; FOUNDATION_REQUIRED. **Links:** ENG-04, DATA-01, EVD-02.

**Context:** chưa có engine OCR, cần UI/contracts test mà không giả AI thật. **Options:** tự fallback mock (gây hiểu lầm); route placeholder success (không có evidence); fixture explicit tách inference. **Decision:** default unconfigured, env explicit fixture; catalogue `/fixtures`, metadata provenance và banner; adapter từ chối khi chưa enabled, không đọc gold. **Consequences:** demo không hoạt động nếu quên env nhưng báo 503 rõ; fixture report evaluator_contract_check, không model quality gate. **Revisit conditions:** thêm provider thật dùng chế độ model riêng; provider error vẫn fail/unavailable, không fallback.
