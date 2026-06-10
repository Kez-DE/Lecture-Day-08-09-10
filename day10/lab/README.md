# Lab Day 10: Data Pipeline and Data Observability

Lab này nối tiếp Day 08 và Day 09. Day 08 làm RAG, Day 09 làm agent orchestration, còn Day 10 tập trung vào phần dữ liệu đứng phía sau: ingest, clean, validate, embed, kiểm tra freshness và giữ bằng chứng trước sau.

Case vẫn là bộ tài liệu nội bộ CS và IT Helpdesk. Điểm khác của ngày này là agent không phải phần khó nhất. Nếu pipeline đưa nhầm version cũ vào vector store, agent sẽ trả lời sai dù prompt có tốt đến đâu.

Slide: [`../lecture-10.html`](../lecture-10.html)

Thông tin lab:

- Môn: AI in Action (AICB-P1)
- Chủ đề: ETL, cleaning, expectation suite, embedding, freshness, before-after evidence
- Thời lượng: 4 sprint, mỗi sprint khoảng 60 phút

## Cách dùng README này

README này giúp người đọc chạy lại pipeline, kiểm tra artifact và hiểu từng sprint của lab. Nếu chỉ muốn verify nhanh, đọc phần "Chạy nhanh từ đầu". Nếu muốn học lại từ baseline, đọc phần "Cách tự làm lại lab từ baseline".

## Trạng thái hiện tại của repo hoàn chỉnh

Run tham chiếu trong repo này dùng run id:

```text
sprint123-qwen-final
```

Kết quả tham chiếu của repo này:

```text
Pipeline:          PIPELINE_OK
Raw records:       247
Cleaned records:   29
Quarantine records:218
Embedding model:   Ollama qwen3-embedding:0.6b
Collection:        day10_kb_qwen3
Self eval:         21/21 pass
Grading eval:      10/10 pass
Freshness:         FAIL, có giải thích trong runbook
```

Freshness `FAIL` không phải lỗi grading. Raw export mới nhất là `2026-04-11T00:00:00`, còn ngày chạy là `2026-06-10`, nên vượt SLA 24 giờ. Khi hướng dẫn hoặc chấm bài, hãy kiểm tra `docs/runbook.md` để xem nhóm có giải thích đúng PASS, WARN và FAIL không.

Artifact chính:

```text
artifacts/logs/run_sprint123-qwen-final.log
artifacts/manifests/manifest_sprint123-qwen-final.json
artifacts/cleaned/cleaned_sprint123-qwen-final.csv
artifacts/quarantine/quarantine_sprint123-qwen-final.csv
artifacts/eval/after_fix_eval.csv
artifacts/eval/after_inject_bad.csv
artifacts/eval/grading_run.jsonl
```

## Chạy nhanh từ đầu

Yêu cầu trước khi chạy:

- Python 3.11+ hoặc version tương thích với `requirements.txt`.
- Ollama đang chạy ở `http://localhost:11434`.
- Model `qwen3-embedding:0.6b` đã được pull.
- OpenRouter key chỉ cần khi chạy agent trả lời đầy đủ. Retrieval-only eval không cần gọi OpenRouter.

Từ thư mục `lab`, chạy:

```bash
cd lab
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Sau đó chỉnh `.env`:

```env
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION=day10_kb_qwen3
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=<openrouter-key-local>
OPENROUTER_MODEL=openrouter/owl-alpha
```

`.env` là cấu hình local cho máy chạy demo, trong đó có thể có OpenRouter key.

Embedding chạy bằng Ollama local. Kiểm tra model trước khi chạy pipeline:

```bash
ollama list
ollama pull qwen3-embedding:0.6b
```

Chạy pipeline cuối:

```bash
python etl_pipeline.py run --run-id sprint123-qwen-final
```

Chạy self eval và grading:

```bash
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_sprint123-qwen-final.json
```

Nếu muốn demo agent bằng web chat:

```bash
python chat_server.py --port 8765
```

Mở `http://127.0.0.1:8765`. UI gọi `rag_agent.py`, retrieve context từ Chroma bằng Ollama embedding, rồi gọi OpenRouter model trong `.env`. Người học có thể bấm `Retrieve` để chỉ xem context hoặc `Gửi` để hỏi agent.

## Vấn đề chính cần hướng dẫn

Raw CSV có export từ nhiều hệ thống nguồn. Dữ liệu cố tình bẩn để buộc pipeline phải xử lý đúng trước khi embed:

- duplicate rows
- dòng thiếu ngày
- `doc_id` lạ
- ngày hiệu lực không theo ISO
- HR policy bị lẫn version cũ, ví dụ 10 ngày phép thay vì 12 ngày
- refund policy bị lẫn cửa sổ xử lý cũ, ví dụ 14 ngày thay vì 7 ngày
- một nguồn hợp lệ chưa có trong allowlist ban đầu

Baseline pipeline chưa đủ. Nếu chỉ chạy embed thẳng từ raw data, vector store có thể chứa chunk stale. Khi đó retrieval nhìn có vẻ đúng vì tìm được policy liên quan, nhưng câu trả lời vẫn sai vì context còn version cũ.

Luồng cần làm đúng thứ tự là:

```text
raw CSV
  -> load_raw_csv()
  -> clean_rows()
  -> write cleaned and quarantine CSV
  -> run_expectations()
  -> embed into Chroma
  -> eval, grading, agent retrieve
```

## Các file nên đọc trước

Đọc theo thứ tự này để hiểu repo nhanh hơn:

1. `data/raw/policy_export_dirty.csv`: dữ liệu đầu vào bẩn.
2. `transform/cleaning_rules.py`: allowlist, rule clean, quarantine, xử lý stale version.
3. `quality/expectations.py`: expectation suite và controlled halt.
4. `etl_pipeline.py`: entry point ingest, clean, validate, embed, manifest, freshness.
5. `data/test_questions.json`: 21 câu self eval.
6. `data/grading_questions.json`: 10 câu grading.
7. `docs/runbook.md`: cách đọc freshness và cách xử lý khi pipeline fail.

Các file còn lại:

```text
embedding_provider.py        tạo embedding function dùng chung
rag_agent.py                 CLI RAG agent: retrieve context rồi gọi OpenRouter
chat_server.py               backend local cho HTML chat UI
static/chat.html             giao diện chat và xem retrieved context
monitoring/freshness_check.py kiểm tra freshness từ manifest
contracts/data_contract.yaml  contract nguồn, schema, quality, freshness
```

Pipeline không hard-code câu hỏi. Self eval đọc từ `data/test_questions.json`; grading đọc từ `data/grading_questions.json`. Nếu có hidden questions cùng format, chấm bằng:

```bash
python grading_run.py --questions path/to/questions.json --out artifacts/eval/custom_grading.jsonl
```

## Hướng dẫn hoàn thành 4 sprint

### Sprint 1: phân tích raw data và ingest

Cần làm:

- Đọc `data/raw/policy_export_dirty.csv`.
- Đếm raw records và số `doc_id` unique.
- So sánh `doc_id` trong raw với `ALLOWED_DOC_IDS`.
- Phát hiện `access_control_sop` là source hợp lệ nhưng bị thiếu khỏi allowlist ban đầu.
- Đối chiếu `data/grading_questions.json` để biết grading cần đủ 5 source canonical.
- Chạy baseline và đọc log halt trước khi sửa code.

Kết quả mong đợi:

- `ALLOWED_DOC_IDS` có đủ 5 source: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`.
- Log có `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`.
- `docs/data_contract.md` và `contracts/data_contract.yaml` có source map, owner, SLA và quality rules.

### Sprint 2: clean, validate, embed

Cần làm:

- Thêm quarantine theo canonical effective date của từng source.
- Loại HR stale theo nội dung, ví dụ `bản HR 2025` và `10 ngày phép năm`.
- Loại marker mơ hồ `Nội dung không rõ ràng`.
- Normalize `exported_at` sang ISO datetime.
- Sửa refund window stale từ `14 ngày làm việc` thành `7 ngày làm việc`.
- Thêm expectations: đủ 5 source, unique `chunk_id`, ISO `exported_at`, không có ambiguous marker.
- Dùng embedding provider nhất quán cho pipeline, eval, grading và agent.

Run tham chiếu:

```text
run_id=sprint123-qwen-final
raw_records=247
cleaned_records=29
quarantine_records=218
embed_upsert count=29 collection=day10_kb_qwen3
PIPELINE_OK
```

### Sprint 3: inject corruption và so sánh before after

Mục tiêu sprint này là chứng minh pipeline thật sự bắt được lỗi, không chỉ pass vì test dễ.

Cần chạy:

```bash
python etl_pipeline.py run --run-id inject-bad-qwen --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
python etl_pipeline.py run --run-id sprint123-qwen-final
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

Kết quả mong đợi:

- Inject bad làm expectation `refund_no_stale_14d_window` fail.
- Eval xấu có `q_refund_window hits_forbidden=yes` vì context còn chunk 14 ngày.
- Sau fix, `q_refund_window hits_forbidden=no` và top 1 vẫn là `policy_refund_v4`.
- Evidence nằm ở `after_inject_bad.csv`, `after_fix_eval.csv` và `run_inject-bad-qwen.log`.

### Sprint 4: monitoring, docs, report

Cần hoàn thành:

- `docs/pipeline_architecture.md`
- `docs/data_contract.md`
- `docs/runbook.md`
- `docs/quality_report_template.md`
- `reports/group_report.md`
- `reports/individual/[ten].md`
- freshness check với giải thích vì sao PASS, WARN hoặc FAIL
- grading cuối và instructor quick check

Lệnh kiểm tra cuối:

```bash
python grading_run.py --out artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_sprint123-qwen-final.json
```

## Cấu trúc thư mục

```text
lab/
├── etl_pipeline.py
├── embedding_provider.py
├── eval_retrieval.py
├── grading_run.py
├── instructor_quick_check.py
├── rag_agent.py
├── chat_server.py
├── static/
│   └── chat.html
│
├── transform/
│   └── cleaning_rules.py
├── quality/
│   └── expectations.py
├── monitoring/
│   └── freshness_check.py
│
├── contracts/
│   └── data_contract.yaml
│
├── data/
│   ├── docs/
│   ├── raw/
│   │   └── policy_export_dirty.csv
│   ├── test_questions.json
│   └── grading_questions.json
│
├── artifacts/
│   ├── cleaned/
│   ├── eval/
│   ├── logs/
│   ├── manifests/
│   └── quarantine/
│
├── docs/
│   ├── pipeline_architecture.md
│   ├── data_contract.md
│   ├── runbook.md
│   └── quality_report_template.md
│
├── reports/
│   ├── group_report.md
│   └── individual/
│       ├── 2A202600588-NGUYENDUCKHANG.md
│       └── template.md
│
├── chroma_db/          local vector DB, ignored
├── .env                local secrets, ignored
├── .env.example
└── requirements.txt
```

## Dataset trong lab

Raw CSV nằm ở:

```text
data/raw/policy_export_dirty.csv
```

Các source canonical mà pipeline cần giữ lại:

```text
policy_refund_v4       policy hoàn tiền, có stale chunk 14 ngày cần sửa
sla_p1_2026            SLA và quy trình P1
it_helpdesk_faq        FAQ IT nội bộ
hr_leave_policy        chính sách nghỉ phép, có version 2025 và 2026
access_control_sop     quy trình cấp quyền truy cập
```

Các source như `invalid_doc_*` hoặc `legacy_*` là export lỗi hoặc dữ liệu cũ. Pipeline phải quarantine, không embed vào vector store final.

## Cách tự làm lại lab từ baseline

Nếu muốn học lại thay vì chỉ chạy bản đã hoàn thiện, làm theo flow này:

1. Chạy pipeline lần đầu.

```bash
python etl_pipeline.py run
```

Pipeline sẽ halt nếu expectation phát hiện dữ liệu chưa sạch. Đọc log trước khi sửa code.

2. Phân tích raw data.

Cần trả lời được:

```text
Có bao nhiêu doc_id unique?
ALLOWED_DOC_IDS đang cho phép những source nào?
Source hợp lệ nào bị quarantine nhầm?
Dữ liệu nào là stale version?
```

3. Đối chiếu grading questions.

Mở `data/grading_questions.json`, xem `expect_top1_doc_id`. Nếu grading cần source mà allowlist chưa có, pipeline sẽ không thể pass bằng cách sửa prompt.

4. Sửa pipeline.

Tối thiểu cần sửa:

```text
transform/cleaning_rules.py
quality/expectations.py
```

Yêu cầu chính:

- cập nhật allowlist cho source hợp lệ
- thêm cleaning rules để loại stale content
- thêm ít nhất 3 rule mới có tác động đo được
- thêm ít nhất 2 expectation mới
- đảm bảo `python etl_pipeline.py run` exit 0

5. Kiểm tra retrieval.

```bash
python eval_retrieval.py --out artifacts/eval/eval_after_fix.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

Trong output, `contains_expected` phải là `true` và `hits_forbidden` phải là `false` cho toàn bộ câu hỏi.

## Eval và grading

Self eval dùng 21 câu trong `data/test_questions.json`:

```bash
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

Grading chính thức dùng 10 câu trong `data/grading_questions.json`:

```bash
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

`hits_forbidden` quét toàn bộ top k chunk ghép lại, không chỉ top 1. Lý do: retrieval có thể lấy đúng tài liệu ở top 1 nhưng vẫn kéo theo chunk stale ở top k. Trường này giúp bắt lỗi kiểu "câu trả lời nhìn đúng nhưng context còn bẩn".

Sau mỗi lần `run`, pipeline upsert theo `chunk_id` và xóa id không còn trong cleaned data. Việc prune này tránh vector cũ nằm lại trong Chroma rồi làm fail grading.

## Inject corruption để kiểm tra pipeline

Dùng lệnh này để embed dữ liệu xấu và bỏ qua validation:

```bash
python etl_pipeline.py run --run-id inject-bad-qwen --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Sau đó chạy lại pipeline chuẩn:

```bash
python etl_pipeline.py run --run-id sprint123-qwen-final
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
```

So sánh hai file eval. Trường hợp quan trọng là refund window: bản xấu còn 14 ngày, bản fix phải trả về 7 ngày và không còn `hits_forbidden`.

## Deliverables

Khi nộp bài, cần có các nhóm file này:

```text
etl_pipeline.py
transform/
quality/
monitoring/
contracts/data_contract.yaml
artifacts/logs/
artifacts/manifests/
artifacts/quarantine/
artifacts/eval/
docs/pipeline_architecture.md
docs/data_contract.md
docs/runbook.md
docs/quality_report_template.md
reports/group_report.md
reports/individual/*.md
artifacts/eval/grading_run.jsonl
```

## Phân vai gợi ý cho nhóm

```text
Ingestion Owner
  raw paths, logging, manifest, phân tích doc_id

Cleaning and Quality Owner
  cleaning_rules.py, expectations.py, quarantine, stale version handling

Embed Owner
  Chroma collection, idempotency, eval, grading verify

Monitoring and Docs Owner
  freshness, runbook, architecture doc, group report
```

## Debug order

Khi kết quả agent sai, đừng sửa prompt trước. Debug theo thứ tự này:

```text
Freshness and version
-> Volume and errors
-> Schema and contract
-> Lineage and run_id
-> Model and prompt
```

Lý do đơn giản: nếu context đã sai hoặc đã stale, model tốt hơn chỉ làm cho câu trả lời sai nghe tự tin hơn.

## Tài nguyên tham khảo

- Slide Day 10: [`../lecture-10.html`](../lecture-10.html)
- Lab Day 09: [`../../day09/lab/README.md`](../../day09/lab/README.md)
- Great Expectations: https://docs.greatexpectations.io/
- ChromaDB: https://docs.trychroma.com/
