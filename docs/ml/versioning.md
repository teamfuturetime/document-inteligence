# Model/config/run versioning

`configs/foundation.json` parse được, fixture only, không secrets; evaluator/generator dùng, không bật app fixture ngầm. RunManifest nguồn chuẩn domain/versioning; [run fixture thật](../../evaluation/reports/fixture-contract-run.json). git_dirty=true là thay đổi local chưa commit, commit nền trước scaffold; không bịa commit mới.

Benchmark cần run ID/time/status; git commit/dirty; dataset version/manifest hash/split; OCR package + model/checkpoint revision/hash riêng; extraction provider/model/snapshot; prompt/rules version/hash; schema/normalization/validation/confidence/evaluation/config versions/hashes; resolved preprocessing/inference đã loại secrets; runtime/locks/hardware/seed; prediction/report artifacts. Contract có ComponentVersion, versions/hashes/config/runtime/hardware, thêm inference metadata cụ thể khi engine có thật.

Scaffold OCR package/model null, fixture predictions hash, versions chính sách riêng, evaluation/normalization code hashes, lock/manifest hashes, hardware/runtime thực. Seed chỉ generator, không bảo đảm AI tái lập. Không dùng một v1 cho mọi thứ. API không pin snapshot báo hạn chế; seed/temperature không bảo đảm bit-identical.

Allowlist resolved config, không key/signed URL/credential/full text. Config proposed sau này tách file example, không app tải nhầm. Đổi data/model/rules/schema cập nhật version/evidence; report cũ truy vết được. Model quality chưa đo, không thay null bằng 0%/100%.
