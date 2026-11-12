# Dữ liệu

Chỉ synthetic/sample hợp lệ theo DATA-01. `fixtures/images` chứa 6 ảnh tự render; `annotations` chỉ evaluator/tests; `ocr.json`/`predictions.json` **viết sẵn**, không output engine. `manifests/fixtures.json` có contract_fixture, nguồn/font/seed/checksum/parent/split/version.

Sinh lại: `uv run --project backend --locked python scripts/generate_fixtures.py`, tùy chọn `--font` font có dấu Việt và quyền phù hợp; sau đó `generate_examples.py`, `check_data.py`, tests/evaluator. Không tải/phân phối font; khác font cần kiểm tra ảnh/gold/version. Upload/DB dùng `runtime/` ngoài Git khi BL-005.

[Dataset card](../docs/data/dataset-card.md), [annotation](../docs/data/annotation-guide.md), [split](../docs/data/split-policy.md). Seed không là evidence model quality hay golden dataset hoàn chỉnh.
