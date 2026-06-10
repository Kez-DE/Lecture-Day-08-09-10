# Runbook — Lab Day 10

## Symptom

Agent hoặc retrieval trả lời sai version, ví dụ refund window là "14 ngày" thay vì chính sách hiện hành "7 ngày", HR trả "10 ngày phép năm" thay vì "12 ngày", hoặc câu hỏi Level 4 Admin Access không retrieve được `access_control_sop`.

## Detection

- Expectation halt trong log: `refund_no_stale_14d_window`, `hr_leave_no_stale_10d_annual`, `required_doc_ids_present`.
- Eval CSV có `hits_forbidden=yes`, `contains_expected=no`, hoặc `top1_doc_expected=no`.
- Grading JSONL có `contains_expected=false`, `hits_forbidden=true`, hoặc `top1_doc_matches=false`.
- Freshness command báo `WARN` hoặc `FAIL`.

## Freshness PASS / WARN / FAIL

Lệnh kiểm tra:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint123-qwen-final.json
```

Ý nghĩa:

| Status | Ý nghĩa | Hành động |
|--------|---------|-----------|
| PASS | `latest_exported_at` còn trong SLA | Có thể phục vụ agent bình thường |
| WARN | Manifest thiếu hoặc dữ liệu gần vượt SLA tùy logic monitor | Kiểm tra nguồn export, chuẩn bị refresh |
| FAIL | Export cũ hơn `FRESHNESS_SLA_HOURS` hoặc manifest lỗi | Không publish cho production; refresh upstream hoặc điều chỉnh SLA có phê duyệt |

Run hiện tại trả `FAIL` vì `latest_exported_at=2026-04-11T00:00:00`, ngày chạy là 2026-06-10 và SLA là 24 giờ. Đây là cảnh báo freshness, không phải lỗi cleaning/retrieval.

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở `artifacts/logs/run_<run_id>.log` | Thấy `raw_records`, `cleaned_records`, `quarantine_records`, expectations và `PIPELINE_OK` hoặc `PIPELINE_HALT` |
| 2 | Mở `artifacts/manifests/manifest_<run_id>.json` | Xác nhận collection, model embedding, latest export, skip validate có bật không |
| 3 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` | Đếm reason như `stale_effective_date_for_doc`, `stale_hr_policy_content`, `unknown_doc_id` |
| 4 | Chạy `python eval_retrieval.py --out artifacts/eval/debug_eval.csv` | Không có `hits_forbidden=yes`, `contains_expected=no`, `top1_doc_expected=no` |
| 5 | Chạy `python grading_run.py --out artifacts/eval/grading_run.jsonl` | 10 câu grading pass toàn bộ |

## Mitigation

1. Nếu expectation halt, không dùng `--skip-validate` trừ khi đang làm Sprint 3 inject.
2. Sửa cleaning rule hoặc data contract, sau đó chạy lại:

```bash
python etl_pipeline.py run --run-id sprint123-qwen-final
```

3. Nếu collection đã bị inject bad, chạy lại pipeline chuẩn. Embed sẽ prune id thừa và upsert snapshot sạch.
4. Nếu freshness FAIL, yêu cầu upstream tạo export mới. Nếu dataset lab tĩnh, ghi rõ ngoại lệ trong report và chỉ dùng cho demo.
5. Nếu agent OpenRouter lỗi, kiểm tra `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, network, và chạy retrieval-only eval để tách lỗi data với lỗi LLM.

## Prevention

- Giữ `required_doc_ids_present` để không bỏ sót source grading như `access_control_sop`.
- Mỗi source mới phải cập nhật `contracts/data_contract.yaml`, `ALLOWED_DOC_IDS` và doc min effective date.
- Không dùng chung collection cho embedding model khác dimension; Qwen dùng `day10_kb_qwen3`.
- Lưu artifact before/after khi inject corruption để chứng minh expectation và eval bắt lỗi.
