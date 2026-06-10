# Quality report — Lab Day 10

**run_id:** `sprint123-qwen-final`  
**Ngày:** 2026-06-10  
**Embedding:** Ollama local `qwen3-embedding:0.6b`

## 1. Tóm tắt số liệu

| Chỉ số | Trước baseline | Inject bad | Sau fix | Ghi chú |
|--------|----------------|------------|---------|---------|
| raw_records | 247 | 247 | 247 | Cùng raw CSV |
| cleaned_records | 40 | 29 | 29 | Sau fix loại stale/ambiguous chặt hơn và thêm access control |
| quarantine_records | 207 | 218 | 218 | Quarantine tăng do rule canonical date/content |
| Expectation halt? | Có | Có nhưng bỏ qua bằng `--skip-validate` | Không | Inject fail `refund_no_stale_14d_window` |

## 2. Before / after retrieval

Artifact:

- Bad: `artifacts/eval/after_inject_bad.csv`
- Good: `artifacts/eval/after_fix_eval.csv`
- Grading: `artifacts/eval/grading_run.jsonl`

**Câu hỏi then chốt:** `q_refund_window`

**Trước/inject:** top1 `policy_refund_v4`, `contains_expected=yes`, `hits_forbidden=yes`; preview chứa "14 ngày làm việc".

**Sau:** top1 `policy_refund_v4`, `contains_expected=yes`, `hits_forbidden=no`; preview chứa "7 ngày làm việc".

**HR version:** `q_hr_annual_leave_under3` pass sau fix: top1 `hr_leave_policy`, `contains_expected=yes`, `hits_forbidden=no`, preview chứa "12 ngày phép năm".

**Access control:** `q_access_level4` pass sau allowlist: top1 `access_control_sop`, preview chứa "IT Manager và CISO".

## 3. Freshness & monitor

`manifest_sprint123-qwen-final.json` ghi `latest_exported_at=2026-04-11T00:00:00`. Với SLA 24 giờ, freshness trả `FAIL` vì dataset cũ hơn SLA nhiều ngày. Đây không chặn Sprint 1-3 nhưng cần được xử lý ở Sprint 4 bằng refresh upstream export hoặc điều chỉnh SLA cho dữ liệu lab tĩnh.

## 4. Corruption inject

Inject dùng:

```bash
python etl_pipeline.py run --run-id inject-bad-qwen --no-refund-fix --skip-validate
```

Mục tiêu là bỏ rule sửa refund window 14 ngày sang 7 ngày và vẫn publish snapshot xấu. Expectation `refund_no_stale_14d_window` fail với `violations=1`, sau đó eval phát hiện `q_refund_window` có `hits_forbidden=yes`.

## 5. Hạn chế & việc chưa làm

- Chưa hoàn tất Sprint 4 runbook/monitoring narrative.
- OpenRouter agent đã smoke test, nhưng chưa có bộ eval LLM-judge tự động.
- Chroma collection `day10_kb_qwen3` phụ thuộc Ollama local đang chạy.
