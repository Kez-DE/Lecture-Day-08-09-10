# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Run chính:** `sprint123-qwen-final`  
**Collection:** `day10_kb_qwen3`  
**Embedding:** Ollama local `qwen3-embedding:0.6b`  
**Agent:** `rag_agent.py` dùng OpenRouter qua `OPENROUTER_API_KEY` / `OPENROUTER_MODEL`

## 1. Pipeline tổng quan

Pipeline đọc `data/raw/policy_export_dirty.csv`, clean theo contract, validate bằng expectation suite, publish snapshot vào Chroma, ghi manifest và log theo `run_id`. Raw export có 247 record từ nhiều `doc_id`; grading cần 5 source canonical: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`. Baseline thiếu `access_control_sop` trong allowlist và còn stale HR 2025, nên pipeline halt.

**Một lệnh chạy chuẩn:**

```bash
python etl_pipeline.py run --run-id sprint123-qwen-final
```

Artifact chính: `artifacts/manifests/manifest_sprint123-qwen-final.json`, `artifacts/cleaned/cleaned_sprint123-qwen-final.csv`, `artifacts/quarantine/quarantine_sprint123-qwen-final.csv`.

## 2. Cleaning & expectation

Pipeline đã thêm allowlist `access_control_sop`, rule canonical effective date theo từng doc, normalize `exported_at`, loại marker `Nội dung không rõ ràng`, loại HR stale theo nội dung, normalize text nhiễu (`!!!`, lặp "làm việc"), và giữ idempotent upsert/prune bằng `chunk_id`.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước | Sau / khi inject | Chứng cứ |
|------------------------|-------|------------------|----------|
| allowlist `access_control_sop` | cleaned không có `access_control_sop`; grading `gq_d10_10` không thể top-1 đúng | cleaned final có 5 chunk `access_control_sop`; grading top1 pass | `cleaned_sprint123-qwen-final.csv`, `grading_run.jsonl` |
| `stale_effective_date_for_doc` | baseline cleaned 40 record, nhiều bản cũ theo doc vẫn vào index | final quarantine thêm 55 record stale theo canonical date | `quarantine_sprint123-qwen-final.csv` |
| `stale_hr_policy_content` | baseline expectation fail: `hr_leave_no_stale_10d_annual violations=2` | final expectation OK; quarantine 8 record HR stale content | log `run_sprint123-qwen-final.log` |
| `ambiguous_chunk_text` / `no_ambiguous_chunk_marker` | baseline cleaned có marker `Nội dung không rõ ràng` | final quarantine 1 record ambiguous, expectation OK | quarantine + expectation log |
| `refund_no_stale_14d_window` inject | final OK, no forbidden 14 ngày | inject `--no-refund-fix --skip-validate` fail 1 violation; eval `q_refund_window` hits forbidden | `manifest_inject-bad-qwen.json`, `after_inject_bad.csv` |
| `required_doc_ids_present` | baseline không có `access_control_sop` | final expectation OK, missing list rỗng | log `run_sprint123-qwen-final.log` |
| `exported_at_iso_datetime` | raw có `2026/04/...` | final all cleaned exported_at ISO | expectation log |

Final run: `raw_records=247`, `cleaned_records=29`, `quarantine_records=218`. Cleaned distribution: refund 7, SLA 5, FAQ 6, HR 6, access control 5.

## 3. Before / after retrieval hoặc agent

Sprint 3 inject:

```bash
python etl_pipeline.py run --run-id inject-bad-qwen --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
python etl_pipeline.py run --run-id sprint123-qwen-final
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

Kết quả xấu: `q_refund_window` vẫn top-1 đúng doc nhưng `hits_forbidden=yes` vì context chứa "14 ngày làm việc". Kết quả sau fix: `q_refund_window` trả context "7 ngày làm việc", `hits_forbidden=no`. Toàn bộ 21 câu eval sau fix: không có `contains_expected=no`, không có `hits_forbidden=yes`, không có `top1_doc_expected=no`. Grading chính thức 10 câu cũng pass toàn bộ.

Agent smoke test:

```bash
python rag_agent.py "Theo chính sách hoàn tiền hiện hành, khách hàng có tối đa bao nhiêu ngày làm việc để gửi yêu cầu hoàn tiền?" --show-context
```

Agent trả lời 7 ngày làm việc, context top-k đều từ `policy_refund_v4`.

## 4. Freshness & monitoring

Freshness hiện `FAIL` vì `latest_exported_at=2026-04-11T00:00:00`, trong khi ngày chạy là 2026-06-10 và SLA là 24 giờ. Đây là expected trong lab: pipeline data quality pass nhưng monitoring cảnh báo data export đã quá cũ. Runbook Sprint 4 cần hướng dẫn refresh upstream export hoặc nới SLA nếu đây là dataset tĩnh.

## 5. Liên hệ Day 09

Collection `day10_kb_qwen3` có thể cấp context cho agent CS/IT Helpdesk. `rag_agent.py` đã chứng minh flow này: query được embed bằng Ollama local, retrieve từ Chroma, sau đó OpenRouter model sinh câu trả lời dựa trên context sạch.

## 6. Rủi ro còn lại & việc chưa làm

- `OPENROUTER_MODEL` phụ thuộc quota/key thật trong `.env`.
- Freshness đang FAIL do raw export cũ theo SLA 24 giờ.
- Chưa có LLM-judge tự động; hiện eval/grading dùng retrieval + keyword check.

## 7. Peer review

1. Khi inject `--no-refund-fix --skip-validate`, expectation nào fail và eval nào chứng minh context xấu vẫn lọt vào retrieval?
   - `refund_no_stale_14d_window` fail 1 violation; `after_inject_bad.csv` có `q_refund_window hits_forbidden=yes`.
2. Vì sao phải thêm `access_control_sop` vào allowlist?
   - Grading `gq_d10_10` yêu cầu top-1 doc là `access_control_sop`; nếu source này bị quarantine nhầm thì grading không thể pass.
3. Freshness FAIL có nghĩa pipeline clean sai không?
   - Không. Clean/eval/grading đều pass; freshness FAIL vì export mới nhất `2026-04-11T00:00:00` đã quá SLA 24 giờ so với ngày chạy 2026-06-10.
