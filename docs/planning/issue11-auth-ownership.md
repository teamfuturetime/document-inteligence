# Issue #11 — kế hoạch mốc triển khai

Yêu cầu người dùng: 50 commit bổ sung cho task này. Mỗi mốc dưới có thay đổi thực và kiểm tra phù hợp, không commit rỗng, backdate hoặc sửa lịch sử PR #16/#18. Nhánh `feat/11-auth-ownership`, base main@921541d. Chỉ công việc issue #11, không push/merge main.

1. Quyết định identity/session/ownership/migration (ADR0010) và kế hoạch.
2. Matrix quyền document/source/review/history/export và owner boundary.
3. Triage storage portability ở nguồn Minh Thảo.
4. Password hashing có salt và work factor đã pin.
5. Password verification và malformed-hash handling.
6. Opaque tokens/digests và privacy tests.
7. DTO identity/session/credentials strict.
8. Migration SQL ownership và auth tables.
9. Backup/upgrade SQLite transaction và rollback checks.
10. Bootstrap schema2, upload insert tương thích schema mới.
11. Guard schema conflict/legacy populated DB và cô lập test runtime.
12. User persistence và session repository.
13. CLI migration với backup/offline lock.
14. Opaque storage và symlink/portable path tests.
15. Owner-bound service và idempotency partition.
16. Owner-scoped list/detail.
17. Owner-scoped review/confirm/export.
18. Owner-scoped reprocess.
19. Owner-scoped history/source.
20. Owner-scoped insights/aggregates.
21. Worker hệ thống xử lý queue nhiều owner.
22. Auth/cookie/origin configuration bounds.
23. Session issuance và authentication service.
24. Expiry/disabled identity checks.
25. Login KDF/rate admission budget.
26. Logout/password-reset/session rotation.
27. Bounded auth body và deadline.
28. Atomic protected API integration: login/session/logout và product identity/CSRF gates.
29. Cookie/CSRF endpoint boundary tests.
30. CORS credentials và origin tests.
31. CLI user lifecycle administration.
32. Explicit backed-up legacy ownership adoption.
33. Hai-user authorization matrix.
34. Owner-specific idempotency regression.
35. Forged run/revision/history/export tests.
36. Anonymous protected endpoint matrix.
37. Cross-site request/login/logout tests.
38. Session expiry/revocation/throttle tests.
39. Backup/migrate/restore và immutable document roundtrip.
40. Frontend session/CSRF request client.
41. API version và generated contracts/types đồng bộ.
42. UI login/logout gate.
43. UI session expiry/account-change isolation tests.
44. Browser E2E hai user với native pipeline.
45. Native authenticated workflow verification.
46. CI auth/browser/native integration.
47. Source lineage và onboarding/runbook.
48. Migration/backup/rollback operations.
49. Kiểm chứng toàn bộ và source fingerprints.
50. Báo cáo acceptance và bàn giao, ghi rõ pending.

Các mốc cần đi cùng nhau để app an toàn được giữ chung (đặc biệt API gates); không bật session mode trên endpoint chưa kiểm owner. Kế hoạch có thể điều chỉnh theo phát hiện thực tế, vẫn giữ phạm vi và ghi kết quả trung thực.
