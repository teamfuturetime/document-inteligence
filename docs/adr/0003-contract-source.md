# ADR-0003 — Models là nguồn chuẩn

**Status:** Applied for scaffold; FOUNDATION_REQUIRED. **Links:** MVP-02/05/06, ENG-03.

**Context:** hai schema/API bằng tay dễ drift; draft khác final. **Options:** JSON Schema viết tay + binding; models backend sinh schemas/API và frontend types. **Decision:** Pydantic strict domain models, FastAPI OpenAPI, openapi-typescript; check drift fail CI; business rules ngoài regex có tests. **Consequences:** export version độc lập app; breaking update fixtures/types/docs/versions; không sửa generated files bằng tay. **Revisit conditions:** có nhiều consumer ngoài Python hoặc schema hóa đơn cần interoperability khác; vẫn giữ một nguồn chuẩn.
