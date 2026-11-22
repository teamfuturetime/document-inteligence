# Docker Compose integration — Issue #52 / PR #68 — 2026-11-22

Thực hiện bởi `tuanqtb123-creator`, Codex hỗ trợ. **Local acceptance PASS**, còn chờ Product CI trên commit bàn giao và final review của `canhtungdz`; không tự merge/đóng #52.

## Baseline, commits và provenance

Old PR head `5a31bebfde993951097b392dcab634f0abdc7afa`, base cũ4191dfe. Đã fetch và merge bằng merge commits, không rewrite hai commits4a35ca7/5a31beb:

- `c769819fd3e56a9d801631db678b6fc2949197f7`: merge main`cc07ee0df087b21cd912f6c7f34d18b333604ce3` (verifier #56, doctor #69, docs/tooling và stable ordering #60).
- `9e2c022b0e5f6b97ff88eedb0a1784e9d562a1ae`: mở rộng smoke/regressions cho verifier và restored sessions, không sửa production domain/schema/prediction.
- `942c59520cd4ce663bf6d79edaa063e7a18fad02`: merge main mới **`b16036f062ccacdf77d790ce43a94d8109c4f2de`**, vừa tích hợp frontend error guidance #63 trong lúc kiểm thử. Không conflict. Full check và hai Docker runs4/5 chạy lại trên source này.
- Commit chứa report/evidence tạo sau thực thi: SHA cuối cùng và CI đúng SHA được công bố trên [PR #68 commits/checks](https://github.com/teamfuturetime/document-inteligence/pull/68/checks) và handoff comment. Không gắn các kết quả trước commit cho SHA được tạo sau đó.

Git main baseline ở trên là ancestor; các commits PR cũ được giữ. Historical evidence/report ngày21/11 giữ nguyên bytes, kiểm SHA256 với bản trước merge. Không dùng source publication #61/staged restore #62 chưa merge.

[Evidence JSON mới](../evidence/docker-smoke-2026-11-22.json) lưu từng run, actual source hashes, document/run/revision/hash, native metadata và inventory. Run1 trên dirty tree; sau đó chỉ format probe trước implementation commit. Runs2/3 trên9e2c022; runs4/5 trên clean942c595 và source hashes khớp source commit. Container `git_commit`/`git_dirty` vẫn null vì `.git` không nằm trong image; không bịa provenance container.

## Môi trường

Windows11 Home25H2 **26200.9974**, Docker Desktop **4.99.0.245822**, Client/Engine **29.9.3**, Compose **5.7.0**. WSL **2.7.3.0**, kernel **6.6.114.1-1**; container Linux x86_64/kernel`6.6.114.1-microsoft-standard-WSL2`. Docker18 CPUs, khoảng15.37GiB RAM. Chỉ khởi động Desktop đã cài, không đổi settings/cài hệ thống/prune.

Host Python3.14.5, uv0.12.22, Node24.16.0/npm11.13.0, Git2.52.0.windows.1. Host Tesseract **5.5.0.20241111**; container native **5.5.0**, UID **10001**. Hai model files đọc được bởi non-root và hash thực khớp revision`87416418657359cb625c412a48b6e1d6d41c29bd`:

- vie: `79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1`
- eng: `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`

## Lệnh và các lượt chạy thật

```powershell
uv sync --project backend --locked
python scripts/dev.py doctor --json --runtime runtime/issue52-integration-20261122/doctor-runtime
uv run --project backend --locked python scripts/check_docker_smoke.py --output runtime/issue52-integration-20261122/smoke-4.json
uv run --project backend --locked python scripts/check_docker_smoke.py --output runtime/issue52-integration-20261122/smoke-5.json
uv run --project backend --locked pytest backend/tests/test_docker_smoke.py -q --basetemp runtime/issue52-integration-20261122/pytest-helper-final
python scripts/dev.py check
git diff --check
```

Các runs1/2/3 dùng cùng CLI với file output tương ứng; tổng **5/5 full smoke PASS**, trong đó hai lượt trên cây tích hợp cuối chạy song song, project/volumes/cổng riêng. Không có smoke FAIL trong phiên cập nhật này. Lint ban đầu bắt lambda loop binding và formatting, đã sửa trước code milestone; không thay assertions để qua test. Host helper test ban đầu6PASS với cache warning; invocation cuối6PASS không warning, tắt cacheprovider local chỉ để tránh cache cũ bị khóa.

| Run | Start Asia/Saigon | Actual Git head | Result | Project inventory after |
|---|---|---|---|---|
| 1 | 2026-11-22T23:35:30+07:00 | `c769819` dirty | PASS | Empty: containers/volumes/networks/images |
| 2 | 2026-11-22T23:38:35+07:00 | `9e2c022` clean | PASS | Empty: containers/volumes/networks/images |
| 3 | 2026-11-22T23:38:34+07:00 | `9e2c022` clean | PASS | Empty: containers/volumes/networks/images |
| 4 | 2026-11-22T23:43:59+07:00 | `942c595` clean | PASS | Empty: containers/volumes/networks/images |
| 5 | 2026-11-22T23:43:59+07:00 | `942c595` clean | PASS | Empty: containers/volumes/networks/images |

## Kết quả nghiệm thu

| Nhóm | Kết quả thực tế |
|---|---|
| Backend/frontend build | PASS pinned base tags/uv/npm locks/model lock; giữ cache exclusions, frontend contracts copy và model readability fixes của PR |
| Health/readiness/Nginx proxy | PASS health + readiness200/OCR ready và frontend200; backend không publish host port, frontend chỉ127.0.0.1 động; đọc lại port sau mỗi restart/recreate |
| PNG/JPEG native | PASS actual Tesseract/models; immutable prediction/evidence spans, inputSHA đúng upload; ba documents / bốn native runs (PNG+JPEG confirmed, một current null draft), PNG có thêm native reprocess/confirmed historical run |
| Review/null/confirm/export | PASS null persisted/confirm422, draft export409; latest confirmed export khớp toàn bộ artifact trừ exported_at. Sau reprocess old run đọc được và export409 theo latest-run CAS |
| Restart local | PASS same volume, detail/prediction/review/history/preview hashes và current null nguyên; export canonical hash bằng bản persisted |
| Windows host doctor #67/#69 | PASS exit0/ready, observed đầy đủ5.5.0.20241111; tool/model pins giữ nguyên. Chỉ chuẩn bị DB2 synthetic riêng trước command, doctor không init/migrate/sửa bytes |
| Backup verifier #56 | PASS format1, schema1/2/extra columns/queued-failed positive; năm rehashed malformed probes reject đúng, không mkdir restore |
| DB1→DB2 | PASS schema1 tạo từ shipped SQL + native synthetic records; backup schema1 được verifier chấp nhận không auto-upgrade; explicit migration sang2 giữ rows/source/preview, legacy owner local kể cả sau tạo user |
| Backup/restore/private | PASS manifest hashes, toàn bộ document/run/revision/event/user/session rows và assets exact, DB0600/snapshot0700 trong Linux; source runtime không đổi sau backup/probes |
| Restored local HTTP | PASS readiness, detail/history/current null/preview/export, old runs. Raw source files được đối chiếu filesystem/manifest; API chỉ phục vụ preview `/image` |
| Restored session HTTP | PASS separate explicitly adopted owned snapshot, login/CSRF, anonymous401, owner reads/detail/history/preview/export, foreign owner read/export/write404; persisted login và history tồn tại sau restart |
| Guards | PASS existing/dangling symlink destinations và corrupted backup refused; Windows symlink/junction regressions thuộc full test suite; không coi Linux symlink là NTFS junction |
| Cleanup | PASS project-labelled containers/volumes/networks và project image tags rỗng trước/sau; chỉ down đúng UUID, không prune. Shared build cache và ignored host test evidence retained có chủ đích |
| Full repository check cuối | PASS exit0, **484 backend/pipeline + 64 frontend tests**, Ruff/format118files,29contracts/data6+150, repository links/YAML, frontend typecheck/lint/format/build, frozen replay30 và fixture6 |
| Focused helper tests | PASS6; hai schema versions kiểm orchestration real SQLite/CLI, export oracle giữ identity/revision; mocks chỉ cho readiness unit tests |
| Browser in Docker | NOT RUN; Compose nghiệm thu HTTP/API thật qua Nginx. Browser CI độc lập không thay local Compose evidence |
| CI trên report commit | Xem current-head run/receipt trong PR #68/handoff sau push; Product CI không chạy Compose |

## Verifier integration negatives

Mỗi case là snapshot copy riêng trong QA-state volume, SQL mutation, rehash manifest bằng DB bytes thật, SQLite integrity/FK vẫn sạch; helper verifier và CLI từ chối, restore chưa tạo destination, malformed snapshot và source bytes không đổi. Không coi hash mismatch là bằng chứng schema/reference validation.

| Case | Expected/actual code | CLI exit | Destination absent | Snapshot unchanged |
|---|---|---|---|---|
| missing_filename | `SNAPSHOT_UNREADABLE` | 2 | Yes | Yes |
| missing_result | `SNAPSHOT_UNREADABLE` | 2 | Yes | Yes |
| missing_revisions | `DATABASE_REFERENCES` | 2 | Yes | Yes |
| missing_event_revision | `DATABASE_REFERENCES` | 2 | Yes | Yes |
| cross_document_event | `DATABASE_REFERENCES` | 2 | Yes | Yes |

Thêm positive controls extra columns, queued/failed no-revision; actual source chứa valid old run, draft/confirmed revisions/current null. Schema1 được verify đúng1 trước explicit migration, schema2 đúng2; local legacy không tự thành session owner. Owned copy được explicit adoption có pre-adoption backup rồi snapshot/restore khác, không sửa ownership runtime local nguồn.

## Cleanup, bảo toàn và giới hạn

Mỗi project có document-runtime + qa-state volumes và loopback ports riêng. UID0 chỉ chown empty owned QA volume; backend/OCR/probe chạy10001. Credentials synthetic random chỉ ở private temporary volume và memory của host HTTP client; không ghi vào report/log/argv, đã xóa cùng volume. `.env`, models, DB/user uploads thật không chỉnh sửa. Không đụng review evidence #56/#59/#61/#64.

HTTP export tạo legitimate history event, nên helper so sánh history trước download, freeze history tại snapshot boundary và kiểm nguyên rows khi offline. Không đòi history không đổi sau một export mới; restart không sinh duplicate revisions/events. Session cookiesSecure=false chỉ trong ephemeral loopback override; default auth/cookie config giữ nguyên.

Không native OCR mocks, không đọc gold để inference, không sửa gold/splits/fingerprints. Đây là QA synthetic workflow, không đo accuracy thực tế hoặc production performance/power-loss safety. CI head cũ44869826633 không được dùng cho bản cập nhật này. Source verifier/doctor lấy từ merged main, không phát sinh production integration regression cần sửa subsystem ngoài #52.

## Source hashes thực chạy ở final runs4/5

| Source | SHA256 |
|---|---|
| `.dockerignore` | `f07168a5a8bc919c3e8f68a1da5ecfb2b6bc7a3d9b3a072163424b491deab574` |
| `backend/Dockerfile` | `6f4f808082ce93b25712d3fc08c865cc7381d0ebdc9248ce664b477cb36b8827` |
| `frontend/Dockerfile` | `bfc65a254b7c2cf6fdf81023706cf8d6d41aba254b377fa748c92f6607170882` |
| `compose.yaml` | `e1889be2a90266084acd9161f628714933273f810ee04ff348d300b06e19dc01` |
| `scripts/check_docker_smoke.py` | `5a16dd87bf944c2af9d7df684cefc78b7231447133366b01bdefd18caea1aa00` |
| `scripts/docker_volume_probe.py` | `fc35d086afc0702a2df8e656f33c92db1f3806b454cbcbf44191fa1872e6473c` |
| `scripts/backup_runtime.py` | `44f8241bd828b844bdee7e6438b98e62951d334d0105faf04943d5f39d047ae6` |
| `scripts/manage_auth.py` | `a78bf8a063dc72e9b5736c920ccd8017bc06591e1d9f0e012806a7a305cff82e` |
| `backend/src/docintel/storage/backup.py` | `0d959a86d7bdbde81adf9101bec60201d0dba798aea7c6963302c077af8bb1a5` |
| `backend/src/docintel/doctor.py` | `8627a73cf8f61b5b5c0366c237340a76f9a159c288533b94ece1ebe0bd6e9863` |
| `backend/uv.lock` | `a8f1acdcb3cd9c91e9ab3f65129154b11d42f8f864e3cc7ebce610d832cf68f1` |
| `frontend/package-lock.json` | `19647a05eeb0d93cad4b2ec6c0bac759335b83a5e22cc63401bbfc7b40f60501` |
| `pipeline/src/document_pipeline/resources/tessdata-lock.json` | `a4a8629541144155d387688c0c2e968f9e473c6d647f0d573fd90c4848faa796` |

Raw logs/receipts giữ ở ignored `runtime/issue52-integration-20261122/`: smoke1–5 JSON/log, doctor-windows.json/doctor-host.log, helper-final.log, dev-check.log/dev-check-final.log, environment/WSL metadata, historical evidence hashes. Final remote SHA, CI run URL, reviewer request và handoff receipt được lưu sau push. Hai reports ngày21/11 không bị sửa thành kết quả mới.
