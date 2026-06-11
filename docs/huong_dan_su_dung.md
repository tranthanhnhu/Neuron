# Hướng dẫn sử dụng `snn_mc` (tiếng Việt)

Tài liệu này mô tả cách **chạy pipeline** và **đọc kết quả** cho package `snn_mc` trong thư mục `NewStructure/`.

Đặc tả DSL đầy đủ (cú pháp, ngữ nghĩa, expressiveness): [dsl_spec.md](dsl_spec.md).

---

## 1. Chuẩn bị

1. **Python 3.10+** đã cài.
2. **NuSMV** có trên PATH (lệnh `NuSMV` hoặc `nusmv` chạy được trong terminal).
3. Mở terminal tại thư mục **`NewStructure`** (hoặc set `PYTHONPATH` trỏ vào đó).

**PowerShell (Windows):**

```powershell
cd D:\Duong\Maria\internship\NewStructure
$env:PYTHONPATH = (Get-Location).Path
```

**Bash (Linux/macOS):**

```bash
cd /đường/dẫn/tới/NewStructure
export PYTHONPATH="$(pwd)"
```

---

## 2. Lệnh chạy (thường dùng)

### Demo chính (Simple Series + Negative Loop)

```bash
python -m snn_mc run examples/series_negloop.dsl --out runs/demo
```

### Chỉ sinh file, không chạy NuSMV (khi chưa cài NuSMV hoặc đang debug parser)

```bash
python -m snn_mc run examples/series_negloop.dsl --out runs/demo --skip-verify
```

### Đổi độ dài chuỗi N mà không sửa file DSL

```bash
python -m snn_mc run examples/series_negloop.dsl --out runs/N6 --override N=6
```

> Lưu ý: nếu đổi `N` trong `simple_series`, cần sửa DSL cho khớp — ví dụ `block negative_loop input=c6 ...` khi `N=6`, không còn `input=c4`.

### Các ví dụ khác

```bash
python -m snn_mc run examples/series_only.dsl --out runs/series
python -m snn_mc run examples/negloop_only.dsl --out runs/negloop
python -m snn_mc run examples/parallel_only.dsl --out runs/parallel
```

### Các flag hữu ích

| Flag | Ý nghĩa |
|------|---------|
| `--out <thư_mục>` | Thư mục ghi toàn bộ kết quả (mặc định: `runs/demo`) |
| `--skip-verify` | Bỏ bước chạy NuSMV (vẫn sinh 6 file step + file `.smv`) |
| `--skip-sim` | Không ghi `sim_stub.txt` sau khi verify thành công |
| `--override N=10` | Ghi đè mọi `N=` trong các dòng `block` thành 10 |
| `--emit-mode lif` | Neuron LIF đầy đủ (mặc định) |
| `--emit-mode simple_boolean` | Neuron boolean đơn giản (`bool_thr`) |
| `--nusmv "đường_dẫn/NuSMV.exe"` | Chỉ định NuSMV nếu không có trên PATH |

---

## 3. Mã thoát (exit code)

| Mã | Ý nghĩa |
|----|---------|
| **0** | Chạy xong; không có spec nào **false** (hoặc đã dùng `--skip-verify`) |
| **1** | Có ít nhất một thuộc tính **false** — xem `step6_results.txt` |
| **2** | Không tìm thấy file `.dsl` |
| **3** | Không tìm thấy NuSMV trên PATH |
| **4** | Log NuSMV không parse được dòng `is true` (thường do lỗi cú pháp trong `combined.smv`) |

---

## 4. File nào đọc theo thứ tự (6 bước cho giáo sư)

Sau khi chạy, mở thư mục `--out` (ví dụ `runs/demo/`):

| File | Bước | Đọc gì |
|------|------|--------|
| **`step1_diagram.md`** | 1 – Sơ đồ | Mermaid + ASCII: neuron, input, cạnh exc/inh |
| **`step2_input.dsl`** | 2 – DSL | File DSL bạn đã viết (bản copy) |
| **`step3_ir.json`** | 3 – IR | JSON: `neurons`, `edges`, `archetypes`, `schedules`, `params` |
| **`step4_composition.txt`** | 4 – Ghép mạng | Danh sách archetype và composition |
| **`step5_properties.smv`** | 5 – Thuộc tính | CTLSPEC/LTLSPEC NuSMV sẽ kiểm tra |
| **`step6_results.txt`** | 6 – Kết quả | Số spec **true/false**, counterexample nếu có |

Terminal cũng in các section `=== Step N: ... ===` tương ứng (có thể bị cắt bớt nếu output dài).

---

## 5. File kỹ thuật (ngoài 6 bước)

| File | Dùng khi nào |
|------|----------------|
| **`combined.smv`** | File NuSMV chạy thật (model + properties + module LIF) |
| `model.smv` | Chỉ phần `MODULE main` + neuron modules |
| `properties.smv` | Chỉ phần spec (CTL/LTL) |
| **`nusmv.log`** | Log đầy đủ từ NuSMV — đọc khi lỗi hoặc exit code 4 |
| `counterexample_snippet.txt` | Có khi có spec **false** — trace ngắn minh họa |
| `sim_stub.txt` | Tóm tắt wiring sau verify thành công (không phải mô phỏng LIF đầy đủ) |

---

## 6. Cách đọc `step6_results.txt`

Ví dụ:

```text
NuSMV exit code     : 0
Specifications true : 20
Specifications false: 2
```

- **exit 0** + **false = 0** → mọi spec NuSMV báo đúng.
- **false > 0** → có thuộc tính sai; đọc phần `First false specs` và file `counterexample_snippet.txt`.

Với demo `examples/series_negloop.dsl`, thường **2 spec false** là các dòng **“Oscillation candidates”** (dao động) trong archetype `negative_loop`. Trong code đã ghi chú *có thể fail nếu chưa tune schedule hoặc tham số LIF* — đây là hành vi mong đợi, không phải lỗi pipeline.

Khi dùng `--skip-verify`, step 6 sẽ ghi rõ verification đã bỏ qua.

---

## 7. Đọc nhanh `step3_ir.json`

| Trường | Ý nghĩa |
|--------|---------|
| `neurons` | Tên các neuron (`c1`…`c4`, `a`, `b`, …) |
| `inputs` | Input boolean (`stim`, …) |
| `edges` | Cạnh: `src`, `dst`, `weight` (dương = kích thích, âm = ức chế) |
| `params` | Bộ tham số LIF (`tau`, `w_exc`, `w_inh`, …) gồm cả 3 loại built-in `quick`/`intermediate`/`slow` |
| `neuron_params` | Neuron nào dùng loại nào (`default`, `quick`, `intermediate`, `slow`, …) |
| `archetypes` | Các `block` đã khai báo: `kind`, `nodes`, `inputs` |
| `schedules` | Lịch `TRUE/FALSE` cho từng input theo bước thời gian |
| `compositions` | Chuỗi `sequential` hoặc `parallel` (nếu có) |

---

## 8. Đọc `step4_composition.txt`

Liệt kê:

- **Compositions**: chuỗi neuron nối tuần tự hoặc song song.
- **Archetype instances**: từng `block` (ví dụ `simple_series`, `negative_loop`), neuron tham gia, input (`stim`, `c4`, …), và ghi chú explicit hay graph-detected.

Dùng file này khi trình bày “mạng được ghép từ những archetype nào”.

---

## 9. Đọc `step5_properties.smv`

Chứa các dòng `CTLSPEC` / `LTLSPEC` mà NuSMV kiểm tra, kèm comment:

- Baseline (membrane `P`, v.v. — chế độ LIF).
- Composition (lan truyền theo chuỗi).
- Archetype (từng kind, ví dụ `simple_series`, `negative_loop`).
- User specs (nếu bạn viết `spec ...` trong DSL).

---

## 10. Luồng pipeline (tóm tắt)

```text
.dsl  →  Parser  →  NetworkIR  →  Composer  →  SMV (model + properties + combined)
                                                      ↓
                                                 NuSMV (verify)
                                                      ↓
                                            step6 + nusmv.log + sim_stub
```

Sơ đồ chi tiết hơn: xem [pipeline.md](pipeline.md).

Cách tham số hóa `N`: xem [parameterize_N.md](parameterize_N.md).

---

## 10b. Ba loại neuron và output tự động

**Ba loại neuron built-in** (luôn có sẵn, không cần khai báo `neuron_params`). Một "loại" = cặp
**(ngưỡng `tau`, leak factor `R/S`)**; leak nay **cố định** (`r_num` luôn = `R`). Chọn bằng
`params=<loại>` trên block:

| Loại | `tau` | leak `R/S` | `w_exc` | Ý nghĩa |
|------|-------|-----------|---------|---------|
| `quick` | 2 | 0.75 | 3 | ngưỡng thấp + leak cao → spike sớm |
| `intermediate` | 4 | 0.50 | 3 | cân bằng (giống `default`) |
| `slow` | 6 | 0.25 | 5 | ngưỡng cao + leak thấp → spike muộn |

> `slow` dùng `w_exc` lớn hơn để neuron ngưỡng-cao/leak-thấp vẫn đạt được ngưỡng
> (`P_ss = w_exc/(1 - R/S)` phải `>= tau`).

**Output tự động**: mỗi archetype tự quyết định neuron nào là output — **không cần** khai báo
`output=` hay `network_output`. Ví dụ: `simple_series` → neuron cuối; `negative_loop` → tất cả
neuron trong vòng lặp; `parallel_composition` → tất cả nhánh. Xem bảng đầy đủ trong
[dsl_spec.md](dsl_spec.md).

---

## 11. DSL demo `series_negloop.dsl` (tham khảo)

```text
include neuron_base.dsl
input stim
schedule stim values TRUE TRUE FALSE TRUE TRUE FALSE

block simple_series  input=stim N=4 prefix=c params=intermediate
block negative_loop  input=c4   A=a B=b      params=quick
```

Output tự động: `c4` (neuron cuối của chuỗi) và `a`, `b` (toàn bộ vòng lặp).

Topology (N=4):

```text
stim → c1 → c2 → c3 → c4 → a → b
                              ↑    |
                              └────┘  (ức chế b → a)
```

---

## 12. Chạy test (tùy chọn)

Cần `pytest`:

```bash
pip install pytest
python -m pytest tests/test_pipeline_smoke.py -v
```

Test chạy `series_negloop.dsl` với `--skip-verify` và kiểm tra 6 file step + IR.

---

## 13. Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [../README.md](../README.md) | Tổng quan package (tiếng Anh) |
| **[luong_chay_du_an.md](luong_chay_du_an.md)** | **Luồng chạy chi tiết: file/hàm Python, sơ đồ, map step1–6 (cho người mới)** |
| [project_flow.md](project_flow.md) | Same content in English |
| [pipeline.md](pipeline.md) | 6 bước + sơ đồ Mermaid |
| [parameterize_N.md](parameterize_N.md) | Tham số `N` trong DSL và CLI |
| [../examples/](../examples/) | File `.dsl` mẫu |
