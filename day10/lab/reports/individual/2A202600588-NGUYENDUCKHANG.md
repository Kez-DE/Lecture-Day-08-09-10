# Báo cáo cá nhân — Lab Day 10

**Tên:** Nguyễn Đức Khang -2A202600588
**Vai trò:** Data pipeline implementation, quality, embed/eval, monitoring docs

## Đóng góp

- Phân tích raw CSV: 247 record, phát hiện source hợp lệ `access_control_sop` bị thiếu khỏi allowlist.
- Mở rộng `transform/cleaning_rules.py` với rule canonical source/date/content, quarantine HR stale và chunk ambiguous.
- Mở rộng `quality/expectations.py` với coverage 5 source, unique `chunk_id`, ISO `exported_at`, no ambiguous marker.
- Chuyển embedding sang Ollama local `qwen3-embedding:0.6b`, collection `day10_kb_qwen3`.
- Thêm `rag_agent.py` dùng OpenRouter để trả lời từ context retrieved.
- Tạo evidence Sprint 3: `after_inject_bad.csv` và `after_fix_eval.csv`.
- Hoàn thành Sprint 4 docs: architecture, data contract, runbook, quality/group reports.

## Evidence

- Final run: `sprint123-qwen-final`
- Manifest: `artifacts/manifests/manifest_sprint123-qwen-final.json`
- Grading: `artifacts/eval/grading_run.jsonl`
- Instructor quick check: 10/10 OK, manifest OK

## Reflection

Lỗi chính không nằm ở model mà ở dữ liệu publish: source hợp lệ bị quarantine nhầm, stale HR 2025 còn lọt vào cleaned, và refund 14 ngày có thể xuất hiện nếu bỏ fix. Expectation halt và eval forbidden keyword giúp phát hiện những lỗi này trước khi agent trả lời sai.
