# ADR-0002 — Stack và dependency management

**Status:** Applied for scaffold; PROVISIONAL cho sản phẩm cuối. **Links:** ENG-01/03, MVP-05.

**Context:** Python 3.14.5/uv 0.12.22 và Node 24.16.0/npm 11.13.0 có sẵn native Windows; chưa có code để kế thừa. **Options:** React/Vue đều phù hợp; FastAPI cho typed contracts; pip requirements vs uv project; server DB vs SQLite local. **Decision:** FastAPI/Pydantic + React/TS/Vite, uv/npm lockfiles thật, Ruff/ESLint/Prettier, pytest/Vitest/Testing Library; SQLite dự kiến khi persistence bắt đầu. **Consequences:** runtime/dependencies exact pin; không cần GPU/key, không DB server scaffold; Dockerfiles/Compose có cấu hình nhưng cần chạy xác minh trên máy có Docker. OCR stack có thể cần Python khác, phải spike trước đổi runtime.

**Revisit conditions:** OCR selected engine không hỗ trợ runtime, nhóm có môi trường khác, hoặc nhu cầu persistence nhiều người. Khi đó ADR mới và regenerate locks/checks. Nguồn tương thích đã kiểm tra: [Vite guide](https://vite.dev/guide/), [uv projects](https://docs.astral.sh/uv/guides/projects/), [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/), [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/); versions thực tế nằm manifests/locks, không dùng nhãn latest để tái lập.
