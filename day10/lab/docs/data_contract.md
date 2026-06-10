# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| policy_refund_v4 | CSV export từ policy system / CS knowledge base | stale refund window 14 ngày, duplicate chunk, effective_date trước canonical 2026-02-01 | `refund_no_stale_14d_window`, `stale_effective_date_for_doc`, `duplicate_chunk_text` |
| hr_leave_policy | CSV export từ HR policy system | bản HR 2025 còn 10 ngày phép năm, effective_date thiếu/sai, marker nội dung mơ hồ | `hr_leave_no_stale_10d_annual`, `stale_hr_policy_content`, `ambiguous_chunk_text` |
| access_control_sop | CSV export từ IAM/SOP catalog | source hợp lệ bị thiếu khỏi allowlist, duplicate chunk, ngày DD/MM/YYYY | `required_doc_ids_present`, `effective_date_iso_yyyy_mm_dd`, `duplicate_chunk_text` |
| sla_p1_2026 | CSV export từ incident/SLA docs | bản cũ trước 2026-01-15, chunk thiếu text, duplicate escalation | `stale_effective_date_for_doc`, `missing_chunk_text`, `chunk_id_unique_non_empty` |
| it_helpdesk_faq | CSV export từ IT Helpdesk FAQ | stale FAQ trước 2026-01-20, text mơ hồ, duplicate VPN/password rows | `stale_effective_date_for_doc`, `no_ambiguous_chunk_marker`, `duplicate_chunk_text` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | Nằm trong allowlist canonical gồm 5 source grading |
| chunk_text | string | Có | Đã bỏ marker mơ hồ, stale HR 2025, refund 14 ngày được fix về 7 ngày |
| effective_date | date | Có | Chuẩn ISO `YYYY-MM-DD` |
| exported_at | datetime | Có | Chuẩn ISO `YYYY-MM-DDTHH:MM:SS` |

---

## 3. Quy tắc quarantine vs drop

Record lỗi schema/source/version đi vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm `reason`. Data owner của từng source kiểm tra reason, sửa upstream hoặc cập nhật allowlist/contract nếu source hợp lệ. Record không được merge lại thủ công vào cleaned CSV; phải chạy lại pipeline để giữ manifest và run_id nhất quán.

---

## 4. Phiên bản & canonical

Source of truth cho refund là `policy_refund_v4`, canonical từ `2026-02-01`, cửa sổ hiện hành là 7 ngày làm việc. HR source of truth là `hr_leave_policy` canonical từ `2026-01-01`; mọi chunk chứa `bản HR 2025` hoặc `10 ngày phép năm` bị quarantine.
