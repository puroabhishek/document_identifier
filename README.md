# Document Identifier

Automatically classifies uploaded business and individual documents using a **fully local AI pipeline** — Docling for text extraction and Qwen2.5 via Ollama for classification. Designed for fintech onboarding journeys where users upload multiple documents at once — the system identifies each one and routes it to the correct slot.

**Data sovereignty:** All processing is in-process on the host server. No document bytes are transmitted to any external service. QCB data residency compliant.

---

## Supported Document Types

### Business (11)
| # | Name | class_label |
|---|---|---|
| 1 | Commercial Registration | `commercial_registration` |
| 2 | Trade License | `trade_license` |
| 3 | Establishment Card | `establishment_card` |
| 4 | Article of Association | `article_of_association` |
| 5 | Credit Bureau Report (Business) | `credit_bureau_report_business` |
| 6 | Tax Card | `tax_card` |
| 7 | Payable Ageing Report | `payable_ageing_report` |
| 8 | Receivable Ageing Report | `receivable_ageing_report` |
| 9 | Bank Statement | `bank_statement` |
| 10 | Audited Financial Report | `audited_financial_report` |
| 11 | Statement of Account | `statement_of_account` |

### Individual / Shareholder (4) — `subject_type: individual` in responses
| # | Name | class_label |
|---|---|---|
| 12 | Passport (any country) | `passport` |
| 13 | QID (Qatar ID) | `qid` |
| 14 | National Address | `national_address` |
| 15 | Credit Bureau Report (Individual) | `credit_bureau_report_individual` |

---

## Classification Pipeline

```
Upload file (PDF, XLSX, DOCX, JPG, JPEG, PNG)
    │
    ▼
Validate extension + file size
    │
    ├── XLSX? ──→ XlsxParser → keyword scoring (prompts/rules/*.yaml)
    │
    └── Other ──→ Docling (extract text + tables → markdown)
                        │
                        ▼
              Qwen2.5:14b via Ollama (few-shot classification)
                        │
                        ▼
              Match class_label → DocumentType in DB
                        │
                        ▼
              Save ClassificationLog (audit trail)
                        │
                        ▼
              ClassifyResponse { document_type, subject_type,
                                 confidence, classification_method,
                                 filename, log_id }
```

**Classification methods:**
- `rule_based` — XLSX files scored against keyword rules in `prompts/rules/`
- `local_llm` — PDF/image/DOCX processed by Docling + Qwen2.5 locally
- `unclassified` — No match or confidence below threshold (default 0.6)

**Why this stack:**
- **Docling** (IBM open-source) — best-in-class table extraction from PDFs, critical for bank statements, ageing reports, and financial statements
- **Qwen2.5:14b** — strongest Arabic-English bilingual model available for local deployment; handles Qatar-specific documents (QID, CR, Trade License) reliably

---

## Project Structure

```
document_identifier/
├── app/                        FastAPI backend
│   ├── core/                   Dependency injection layer
│   │   ├── protocols.py        ServiceResult type + ClassificationServiceProtocol
│   │   └── container.py        AppContainer — owns all shared services
│   ├── classification/         Engine + rule-based scorer
│   ├── db/                     SQLAlchemy base, session, seed loader
│   ├── models/                 DocumentType, TrainingDocument, ClassificationLog
│   ├── parsers/                XlsxParser, DoclingParser, MIME factory
│   ├── routers/                classify, document_types, training, health
│   ├── schemas/                Pydantic request/response models
│   ├── services/               LocalLLMService + PromptBuilder
│   ├── config.py               Pydantic-settings (reads .env)
│   ├── exceptions.py           Custom exceptions + FastAPI handlers
│   └── main.py                 App factory + lifespan (Ollama health check, seed, prompt load)
│
├── prompts/                    AI artifacts — versioned like code
│   ├── rules/                  XLSX keyword rules (edit to add keywords, no deploy needed)
│   │   ├── payable_ageing.yaml
│   │   └── receivable_ageing.yaml
│   └── document_types/
│       └── seed_data.yaml      All 15 document type definitions
│
├── data/                       Test inputs and eval fixtures
│   ├── raw/                    Sample files per doc type — create manually, gitignored
│   ├── training/               Labeled training docs uploaded via API — gitignored
│   └── fixtures/               JSON fixture definitions for evals
│
├── agents/                     AI configuration — versioned like code
│   └── local_llm/
│       └── config.yaml         Non-secret LLM config (model, thresholds, data sovereignty note)
│
├── evals/                      End-to-end accuracy measurement
│   ├── test_cases/             Input + expected output per document type
│   ├── scorecards/             Output from eval runs — created on first run, gitignored
│   └── run_evals.py            Eval runner script
│
├── alembic/                    DB migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_local_storage.py   Rename gcs_uri→storage_uri, add extracted_text
└── tests/                      Unit + integration tests (50 tests)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running

### 2. Install Ollama and pull the model

```bash
# Install Ollama from https://ollama.com, then:
ollama serve                    # start Ollama server (keep running)
ollama pull qwen2.5:14b         # ~8.9 GB download — do this once
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Note: `docling` pulls PyTorch and layout models on first install (~2–4 GB). Subsequent installs are cached.

### 4. Configure environment

```bash
cp .env.example .env
# Defaults work out of the box — no edits required for local setup
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

On startup the server:
- Seeds all 15 document types into the database
- Pings Ollama — **fails fast** if Ollama is unreachable (run `ollama serve` first)
- Loads any existing training examples into the prompt builder

Open `http://localhost:8000/docs` for the interactive API.

---

## API Endpoints

### Classification
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/classify` | Upload a file → get classification result |

### Document Type Registry
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/document-types` | List all document types |
| `POST` | `/api/v1/document-types` | Register a new type |
| `PUT` | `/api/v1/document-types/{id}` | Update type metadata |
| `DELETE` | `/api/v1/document-types/{id}` | Soft-delete a type |

### Training Management
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/training/documents` | Upload a labeled training sample — text extracted immediately |
| `GET` | `/api/v1/training/documents` | List training samples |
| `DELETE` | `/api/v1/training/documents/{id}` | Remove a training sample |
| `POST` | `/api/v1/training/train` | Backfill extraction for any samples missing text (sync, instant) |

### Health
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | DB + service connectivity check |

---

## How Training Works

Training uses **few-shot prompting** — no model fine-tuning, no retraining jobs.

Uploading a labeled document adds it as an example in the classification prompt. Effect is immediate.

```
POST /api/v1/training/documents  (document_type_id=9, file=bank_statement.pdf)
  → Docling extracts text from the PDF
  → Stored in DB as a labeled example
  → Prompt builder refreshed — example active for all future classify calls
  → 201 returned (no polling required)
```

**More labeled examples = better accuracy**, especially for document types that look visually similar (e.g. bank statement vs statement of account).

---

## Adding a New Document Type

1. Add an entry to `prompts/document_types/seed_data.yaml`
2. Restart the server — seeds on startup
3. Upload labeled training samples via `POST /api/v1/training/documents`
4. Done — the system classifies the new type immediately

## Adding or Editing XLSX Keywords

Edit `prompts/rules/payable_ageing.yaml` or `prompts/rules/receivable_ageing.yaml` and restart. No code change needed.

---

## Running Tests

```bash
pytest tests/ -v
```

50 tests covering: container DI, classification engine, local LLM service, prompt builder, Docling parser, XLSX parser, rule-based scorer, classify endpoint, document type CRUD, training routes.

## Running Evals

Place real sample files in `data/raw/<doc_type>/` then:

```bash
python evals/run_evals.py --base-url http://localhost:8000

# Run a single doc type only:
python evals/run_evals.py --base-url http://localhost:8000 \
  --cases evals/test_cases/bank_statement_cases.json
```

**Eval pass criteria** — all three fields must match exactly:

| Field | Rule |
|---|---|
| `document_type` | Exact match against `name` from `seed_data.yaml` |
| `subject_type` | `"business"` or `"individual"` |
| `classification_method` | `"local_llm"` (PDF/image/DOCX) or `"rule_based"` (XLSX) |

Confidence is captured in the scorecard but does not affect pass/fail. Missing sample files are skipped, not failed.

Scorecards saved to `evals/scorecards/{timestamp}.json`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./document_identifier.db` | Database connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen2.5:14b` | Model used for classification |
| `LOCAL_TRAINING_DIR` | `data/training` | Local directory for training document storage |
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum LLM confidence to accept a classification |
| `XLSX_RULE_THRESHOLD` | `0.5` | Minimum keyword hit ratio for XLSX classification |
| `MAX_UPLOAD_BYTES` | `20971520` | Max upload size (20 MB) |
| `DEBUG` | `false` | Enable SQLAlchemy query logging |
