# S3.3.2b — Preflight model/runtime

Ngày kiểm tra: 21/10/2026, Asia/Saigon. Chỉ thực hiện Giai đoạn 0–1.
**Chưa tải weights/runtime, cài dependency, tạo OCR snapshot mới hoặc chạy VLM.**
Các lệnh tải/chạy bên dưới là đề xuất, chưa thực hiện; cần người dùng xác nhận.

## Repository và kiểm tra thực tế

- Repo `E:\HUS\subject\Code\SE\PROJECT\document-inteligence`, branch `tuannguyen`.
- HEAD `7a28be309eb3da380795a46d7c738105351dafbf`; origin fetch/push
  `https://github.com/teamfuturetime/document-inteligence.git`.
- Trước lượt này: 3 file tracked sửa (README, roadmap, testing), 14 file untracked
  thuộc khảo sát S3.3.1/benchmark S3.3.2a. Index rỗng. Giữ nguyên tất cả.
- Refs local báo ahead 2; không fetch, chưa xác nhận trạng thái GitHub mới nhất.
- Đã đọc Master Prompt, survey, benchmark offline, OCR docs, roadmap, architecture,
  diff hiện có và contract/runner benchmark, OCR contract. Prompt hiện tại yêu cầu
  dừng trước tải/cài; không áp dụng quy tắc tự commit trong Master Prompt.
- Runner hiện tại cố ý chỉ nhận provider fake và ghi fixture_simulation. Sau phê
  duyệt phải bổ sung nhánh real có metadata/timing riêng, giữ nguyên fixture mode,
  tái sử dụng parser/metrics; không chỉ bỏ guard rồi gắn nhãn inference thành công.

Lệnh đã chạy trong lượt preflight:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short --branch
git remote -v
git diff --stat
git diff --cached --stat
git diff -- README.md docs/roadmap.md docs/testing.md
git ls-files --others --exclude-standard
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
git diff --check
git diff --cached --check
```

Kết quả suite mới chạy: **531 passed in 3.67s**. Diff checks đạt, không có thay đổi
code trong lượt này. Không dùng số đo fixture làm bằng chứng inference.

## Phần cứng và môi trường đã kiểm tra lại

Truy vấn CIM trong sandbox bị Access denied; đã đọc lại bằng quyền được cấp,
không cài công cụ/driver và không ghi serial hoặc thông tin tài khoản.

| Thành phần | Snapshot thực tế |
| --- | --- |
| Máy / OS | Lenovo 21LE, Windows 11 Home, 64-bit |
| CPU | Intel Core Ultra 5 125H, 14 cores / 18 logical processors |
| RAM | 33,820,106,752 bytes (~31.50 GiB); FreePhysicalMemory 16,315,032 KiB (~15.56 GiB), thay đổi theo thời điểm |
| GPU | CIM liệt kê Intel Arc Graphics, driver 32.0.101.8243 |
| VRAM / tăng tốc | Chưa xác minh dedicated VRAM/shared budget hoặc SYCL/Vulkan chạy được. AdapterRAM 2,147,479,552 bytes không chứng minh ngân sách inference |
| Ổ E: | Còn 134,299,361,280 bytes (~125.08 GiB) |
| Runtime trên PATH | Không tìm thấy llama-cli, llama-mtmd-cli, llama-server, ollama, nvidia-smi; không khẳng định chúng không tồn tại ngoài PATH |
| Venv | Pillow 13.0.0; không thấy distributions llama-cpp-python, transformers, torch, psutil |

Lệnh: Get-CimInstance với Win32_ComputerSystem, Win32_OperatingSystem,
Win32_Processor, Win32_VideoController, Win32_LogicalDisk; Get-Command cho các binary
trên; importlib.metadata trong venv để đọc package metadata (không import model).

## Model được xác minh từ nguồn chính thức

[Qwen GGUF card tại revision cố định](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/blob/1cd86afb9a95c410a6038ab3b40d8b578c892266/README.md):
`Qwen/Qwen3-VL-4B-Instruct-GGUF`, revision
`1cd86afb9a95c410a6038ab3b40d8b578c892266`. Metadata public, không gated.
Card khai báo Apache-2.0 và cặp LLM/vision encoder GGUF.
[License dự án Qwen3-VL](https://raw.githubusercontent.com/QwenLM/Qwen3-VL/main/LICENSE)
là Apache-2.0. Không thấy file LICENSE riêng trong metadata checkpoint GGUF và
checkpoint gốc được truy vấn; URL LICENSE checkpoint gốc trả Entry not found.
Không coi điều này là bằng chứng có file license trong weights đã tải. Khi tải,
giữ card khai báo license và bản license/notice có nguồn, không đưa weights lên Git.

Nguồn size/hash: [Hugging Face API blobs](https://huggingface.co/api/models/Qwen/Qwen3-VL-4B-Instruct-GGUF?blobs=true),
đối chiếu revision trên. **Đây là SHA-256 được công bố trong LFS metadata, chưa phải
checksum tự tính trên file tải về**. Sau tải phải kiểm tra cả byte size và hash.

| File | Bytes | SHA-256 công bố |
| --- | --- | --- |
| Qwen3VL-4B-Instruct-Q4_K_M.gguf | 2497281664 | 66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a |
| mmproj-Qwen3VL-4B-Instruct-F16.gguf | 836180256 | 256f3a43bd4205ffef48d6b92715e1e70b5b0e9aef06522584967513a9985331 |

Tổng weights: 3,333,461,920 bytes (~3.33 GB / 3.10 GiB). File size không phải RAM
peak. Chưa có kết quả tiếng Việt, JSON adherence, latency hay memory trên máy này.

## Runtime cụ thể và giới hạn xác minh

[llama.cpp v0.7.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0)
chỉ có asset nightly-tag.txt (7 bytes), đã đọc là b11669.
[Release b11669](https://github.com/ggml-org/llama.cpp/releases/tag/b11669)
và [API metadata](https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11669)
trỏ commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`.

| Gói đề xuất | Bytes | SHA-256 công bố bởi GitHub |
| --- | --- | --- |
| llama-b11669-bin-win-cpu-x64.zip | 19537886 | 37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b |

Runtime [MIT](https://raw.githubusercontent.com/ggml-org/llama.cpp/620d2225cc436ab0b001e3200e590e3b286ef9ab/LICENSE);
giữ license runtime và third-party notices đi kèm gói, kiểm tra nội dung sau giải nén.
Chưa tải zip, chưa kiểm tra DLL/CPU instructions/binary --help trên máy.

Đã đối chiếu source tại commit trên:

- [CMake mtmd](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/mtmd/CMakeLists.txt)
  bao gồm models/qwen3vl.cpp; có cả graph vision và src/models/qwen3vl.cpp language.
- [Multimodal docs](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/docs/multimodal.md)
  cho phép -m + --mmproj; CPU cần -ngl 0 và --no-mmproj-offload.
- [mtmd helper](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/mtmd/mtmd-helper.cpp)
  giải mã ảnh qua stbi_load_from_memory thành RGB. Không mặc định tương đương
  preprocessing/EXIF của Pillow S3.2: provider dự kiến chuẩn bị PNG RGB nền trắng,
  EXIF-transposed, lưu hash/kích thước, giữ hệ tọa độ OCR; không sửa adapter S3.2.
- [CLI docs](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/cli/README.md)
  và common/arg.cpp có --image, --offline, --single-turn, --simple-io,
  --no-display-prompt, --image-max-tokens, --json-schema-file. Đây là khả năng ở
  source; kết hợp vision/grammar và framing stdout vẫn cần smoke test binary.

## GO/NO-GO trước tải

**GO có điều kiện cho thử CPU batch 1 sau khi người dùng xác nhận tải/runtime**:
model và vision graph được hỗ trợ ở source; dung lượng đĩa hiện đủ cho các file.
RAM hiện tại cho phép đề xuất thử có guard, chưa chứng minh peak RAM đủ hoặc tốc độ
chấp nhận được. **NO-GO cho khẳng định GPU acceleration, SLA hoặc chất lượng model**.

Đề xuất cấu hình thử cố định: CPU 8 threads, context 4096 tổng prompt/image/output,
image-max-tokens 1024, max output 768, temp 0, seed 42. Token cap ảnh thay đổi
preprocessing nên phải ghi metadata; nếu thiếu context không cắt prompt/OCR âm thầm.
Đây là cấu hình thử, khác sampling gợi ý của card; không coi là cấu hình tối ưu.
Guard dự kiến: 120 giây tổng mỗi tiến trình/run, peak working-set process 12 GiB;
thiếu RAM trống khi kiểm tra lại thì dừng. Chưa có guard code/measurement thực tế.
Memory sampling không bảo đảm thấy đỉnh tuyệt đối; chưa có số đo GPU memory.

Tác động đề xuất: tải tổng 3,352,999,806 bytes (~3.35 GB / 3.12 GiB) gồm zip;
dự trù 6 GiB đĩa cho zip/giải nén/weights/records (budget, chưa đo). Lưu trong
`.venv/vlm-s332b/` đã được .gitignore loại, không đổi PATH/registry/driver hoặc
pip dependencies, không dùng installer hệ thống/API trả phí. CPU có thể bận/nóng
và chiếm RAM trong smoke/9 run; chưa biết latency hoặc chi phí điện.

## Lệnh dự kiến — CHƯA CHẠY, chỉ sau xác nhận

Chạy từ repo root; từ chối thư mục đích đã tồn tại để tránh ghi đè. Chỉ tải hai
weights cụ thể và một zip, không dùng -hf tự chọn main hoặc tải toàn checkpoint.

```powershell
$ErrorActionPreference = 'Stop'
$vlmStage = Join-Path (Get-Location).Path '.venv/vlm-s332b'
if (Test-Path -LiteralPath $vlmStage) { throw 'Destination exists; inspect before continuing' }
New-Item -ItemType Directory -Path $vlmStage | Out-Null
$modelBase = 'https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/resolve/1cd86afb9a95c410a6038ab3b40d8b578c892266'
$downloads = @(
    @{name='Qwen3VL-4B-Instruct-Q4_K_M.gguf'; url="$modelBase/Qwen3VL-4B-Instruct-Q4_K_M.gguf"; bytes=2497281664; sha='66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a'},
    @{name='mmproj-Qwen3VL-4B-Instruct-F16.gguf'; url="$modelBase/mmproj-Qwen3VL-4B-Instruct-F16.gguf"; bytes=836180256; sha='256f3a43bd4205ffef48d6b92715e1e70b5b0e9aef06522584967513a9985331'},
    @{name='llama-b11669-bin-win-cpu-x64.zip'; url='https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip'; bytes=19537886; sha='37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b'}
)
foreach ($asset in $downloads) {
    $target = Join-Path $vlmStage $asset.name
    Invoke-WebRequest -UseBasicParsing -Uri $asset.url -OutFile $target
    if ((Get-Item -LiteralPath $target).Length -ne $asset.bytes) { throw 'Size mismatch; stop' }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset.sha) { throw 'Checksum mismatch; stop' }
}
Expand-Archive -LiteralPath (Join-Path $vlmStage 'llama-b11669-bin-win-cpu-x64.zip') -DestinationPath (Join-Path $vlmStage 'runtime')
```

Sau giải nén: kiểm tra license/notices, binary --version/--help và dependency thực tế
trước inference. Nếu thiếu DLL/runtime hệ thống thì báo lỗi và xin phép riêng, không
tự cài thêm. Cần ghi đường dẫn executable tìm được; không giả định layout zip.
Smoke dự kiến qua subprocess argv, shell=False, timeout/resource monitor; tham số:

```text
llama-cli.exe -m <Q4_K_M.gguf> --mmproj <F16.gguf> --image <processed.png>
  -c 4096 -n 768 -t 8 -ngl 0 --no-mmproj-offload --image-max-tokens 1024
  --temp 0 --seed 42 --offline --single-turn --simple-io --no-display-prompt
  --color off -f <versioned-prompt.txt>
```

Đây là argv minh họa, không phải lệnh đã chạy hoặc script PowerShell nhiều dòng.
Lấy stdout làm response, stderr giữ diagnostic riêng. Nếu có banner/prose/EOS marker
không phù hợp parser thì ghi lỗi framing để xử lý transport có test; không sửa
giá trị hoặc tìm/cắt JSON tùy tiện để tăng điểm. Grammar là tùy chọn cần kiểm tra
trong smoke; không hứa JSON hợp lệ chỉ vì runtime có flag.

## Tiếp tục sau khi được phép

1. Kiểm tra lại Git, RAM/đĩa; tải đúng file, kiểm hash/license/binary, không overwrite.
2. Tạo OCR snapshot thật bằng Tesseract S3.2, giữ nguyên raw text/TSV, word boxes,
   native scores, engine/model/config và input/processed-image hashes. Map offsets
   theo nguồn có kiểm tra; không thay text tổng hợp hiện có bằng OCR rồi giữ nhãn fixture.
3. Giữ labels evaluator-only; kiểm canonical model/hash, không sửa để khớp dự đoán.
   Ba file hiện tại chỉ là PNG/JPEG cùng một invoice và một blank.
4. Thêm provider real với provenance weights/mmproj/runtime/prompt/preprocessing/
   decoding versions/hashes, timeout/cancellation và memory guard; tái dùng parser,
   evidence lookup, metrics. Không đổi sales_invoice 1.0.0 hoặc hành vi S3.1–S3.2.
5. Một image smoke hợp lệ rồi 9 run/3 mode hoặc ghi lỗi thực tế và dừng đúng yêu cầu.
   Image-only thiếu evidence định vị thì giữ unavailable/accepted null; không chế box.
   Confidence null; OCR/model scores riêng; không fallback fixture khi inference lỗi.
6. Đo cold load/OCR/inference/parse riêng khi khả thi, báo giới hạn phép đo; chạy
   offline provider tests/full suite/diff check, review Git. Không tự stage/commit/push.

S3.3.2b **chưa hoàn thành**. Bước tiếp theo duy nhất là người dùng xác nhận phương án
tải/runtime CPU và ngân sách trên; chưa bắt đầu Giai đoạn 2–4.
