# Document Identifier

Automatically classifies uploaded business and individual documents using **Google Document AI Custom Classifier** and a rule-based fallback for Excel files. Designed for onboarding journeys where users upload multiple documents at once — the system identifies each one and routes it to the correct slot.

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

### Individual / Shareholder (4)
| # | Name | class_label |
|---|---|---|
| 12 | Passport (any country) | `passport` |
| 13 | QID (Qatar ID) | `qid` |
| 14 | National Address | `national_address` |
| 15 | Credit Bureau Report (Individual) | `credit_bureau_report_individual` |

---

## Classification Pipeline

```
Upload file (PDF, XLSX, DOCX, JPG, PNG)
    │
    ▼
Validate extension + file size
    │
    ├── XLSX? ──→ XlsxParser → keyword scoring (prompts/rules/*.yaml)
    │
    └── Other ──→ Google Document AI Custom Classifier
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
- `document_ai` — All other formats sent to Google Document AI
- `unclassified` — No match or confidence below threshold

---

## Project Structure

```
document_identifier/
├── app/                        FastAPI backend
│   ├── classification/         Engine + rule-based scorer
│   ├── db/                     SQLAlchemy base, session, seed loader
│   ├── models/                 DocumentType, TrainingDocument, ClassificationLog
│   ├── parsers/                XLSX parser + MIME factory
│   ├── routers/                classify, document_types, training, health
│   ├── schemas/                Pydantic request/response models
│   ├── services/               Google Document AI wrapper
│   ├── config.py               Pydantic-settings (reads .env)
│   ├── exceptions.py           Custom exceptions + FastAPI handlers
│   └── main.py                 App factory + lifespan hooks
│
├── prompts/                    AI artifacts — versioned like code
│   ├── rules/                  XLSX keyword rules (edit to add keywords, no deploy needed)
│   │   ├── payable_ageing.yaml
│   │   └── receivable_ageing.yaml
│   └── document_types/
│       └── seed_data.yaml      All 15 document type definitions
│
├── data/                       Test inputs and eval fixtures
│   ├── raw/                    Sample files per doc type (gitignored if large)
│   └── fixtures/               JSON fixture definitions for evals
│
├── agents/                     Classifier configuration
│   └── document_ai/
│       └── processor_config.yaml   Non-secret AI config (thresholds, MIME types)
│
├── evals/                      End-to-end accuracy measurement
│   ├── test_cases/             Input + expected output per document type
│   ├── scorecards/             Output from eval runs (gitignored)
│   └── run_evals.py            Eval runner script
│
├── alembic/                    DB migrations
│   └── versions/001_initial_schema.py
└── tests/                      Unit + integration tests (33 tests)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A Google Cloud project with [Document AI API enabled](https://cloud.google.com/document-ai/docs/setup)
- A `CUSTOM_CLASSIFICATION_PROCESSOR` created in Document AI
- A GCS bucket for training data

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in your GCP values in .env
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

The server seeds all 15 document types on startup. Open `http://localhost:8000/docs` for the interactive API.

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
| `POST` | `/api/v1/training/documents` | Upload a labeled training sample |
| `GET` | `/api/v1/training/documents` | List training samples |
| `DELETE` | `/api/v1/training/documents/{id}` | Remove a training sample |
| `POST` | `/api/v1/training/train` | Trigger classifier retraining (async LRO) |
| `GET` | `/api/v1/training/status` | Poll training operation status |

### Health
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | DB + service connectivity check |

---

## Adding a New Document Type

1. Add an entry to `prompts/document_types/seed_data.yaml`
2. Restart the server — it seeds on startup
3. Upload labeled training samples via `POST /api/v1/training/documents`
4. Trigger retraining via `POST /api/v1/training/train`
5. Poll `GET /api/v1/training/status` until done

## Adding or Editing XLSX Keywords

Edit `prompts/rules/payable_ageing.yaml` or `prompts/rules/receivable_ageing.yaml` and restart. No code change needed.

---

## Running Tests

```bash
pytest tests/ -v
```

33 tests covering: classification engine, XLSX parser, rule-based scorer, classify endpoint, document type CRUD.

## Running Evals

Place real sample files in `data/raw/<doc_type>/` then:

```bash
python evals/run_evals.py --base-url http://localhost:8000
```

Outputs accuracy per document type and saves a scorecard to `evals/scorecards/`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./document_identifier.db` | Database connection string |
| `GOOGLE_CLOUD_PROJECT_ID` | — | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to service account JSON |
| `DOCUMENT_AI_LOCATION` | `us` | Processor region (`us` or `eu`) |
| `DOCUMENT_AI_PROCESSOR_ID` | — | Custom classifier processor ID |
| `GCS_TRAINING_BUCKET` | — | GCS bucket for training data |
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum Document AI confidence to accept |
| `XLSX_RULE_THRESHOLD` | `0.5` | Minimum keyword hit ratio for XLSX classification |
| `MAX_UPLOAD_BYTES` | `20971520` | Max file size (20 MB) |
| `DEBUG` | `false` | Enable SQLAlchemy query logging |
