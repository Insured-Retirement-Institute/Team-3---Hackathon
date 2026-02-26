# Advisor Onboarding API (Orchestration Service)

API for broker/dealer advisor onboarding and carrier integration. It acts as the **orchestration layer** between a React frontend, carrier assignment APIs, document processing (OCR), and optional AWS SNS notifications.

---

## Architecture

The system follows this flow:

1. **Web portal → React frontend**  
   Users interact with the web app (create agents, upload documents, trigger transfers).

2. **React frontend → Orchestration Service (this API)**  
   The frontend calls the backend for advisors, transfers, carrier formats, and document extraction.

3. **Orchestration Service**  
   - **Carrier adaptor:** Builds the request payload (standard simple/structured or custom YAML) and dispatches to the appropriate carrier API. Uses **AWS Bedrock (Claude)** when a carrier has a custom format YAML to adapt advisor data to the carrier’s schema.  
   - **OCR / document processing:** Forwards uploaded documents to an external **OCR Service** (e.g. vision/OCR on AWS Bedrock or another provider) for parsing.  
   - **Persistence:** Stores transfer request status and audit data (local JSON store or database).  
   - **Webhook callback:** Receives status updates from carrier platforms via `POST /api/carrier/appointments/status` (e.g. completed, rejected with reason).

4. **Carrier adaptor → Carrier assignment APIs**  
   - **Standard APIs (IRI-style):** `POST /api/carrier/standard/simple/appointments` (single-level: carrierId + advisor + statesRequested) and `POST /api/carrier/standard/structured/appointments` (hierarchical: meta + agent + appointment).  
   - **Custom API:** `POST /api/carrier/custom/appointments` for carrier-specific payloads produced by Bedrock from a carrier YAML.

5. **Carrier platform → Orchestration Service**  
   Carriers call the webhook to update submission status (e.g. completed, rejected); the orchestration service updates storage and exposes status via the admin APIs.

*Place the architecture flow diagram in `docs/architecture-flow.png` for a visual reference.*

---

## Quick start

### Run backend and frontend

- **Backend:** From repo root: `cd backend && .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` (see [Run locally](#run-locally) for first-time setup). Watch this terminal for `[CARRIER]` and `[BEDROCK]` logs.
- **Frontend:** `cd frontend && npm run dev` → app at http://localhost:5173.
- **Testing (standard vs custom, Bedrock):** see **[TESTING.md](TESTING.md)**.

### Run locally (first time)

1. **Backend**
   ```bash
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   USE_JSON_STORE=true .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Open **http://localhost:8000/docs** for Swagger UI.

### API authentication (Bearer token)

All `/api/*` requests **must** include: `Authorization: Bearer <token>`.

- **Backend:** Set `AUTH_TOKEN` in env (default in `src/main.py`).
- **Frontend:** Set `VITE_AUTH_TOKEN` to the same value.

In Swagger, use **Authorize** and paste the token. For `curl`, add: `-H "Authorization: Bearer <token>"`.

---

## Sample data (local JSON store)

With `USE_JSON_STORE=true`:

- **Script:** `cd backend && USE_JSON_STORE=true .venv/bin/python scripts/seed_advisors.py`  
  Writes 3 sample advisors to `local_data/advisors.json` (safe to run multiple times).
- Or create advisors via `POST /api/admin/advisors` (Swagger).

---

## Carrier format YAML and Bedrock (carrier adaptor)

The **carrier adaptor** sends requests to carrier assignment APIs in one of three ways:

| Format | When used | Carrier API path |
|--------|-----------|------------------|
| **Standard simple** | Carrier default is simple (single-level) | `POST /api/carrier/standard/simple/appointments` |
| **Standard structured** | Carrier default is structured (hierarchical) | `POST /api/carrier/standard/structured/appointments` |
| **Custom** | Carrier has a format YAML uploaded | `POST /api/carrier/custom/appointments` (payload built by Bedrock from YAML) |

- **Standard simple** = `carrierId`, `advisor`, `statesRequested`.
- **Standard structured** = `meta`, `agent`, `appointment`.
- **Custom** = Shape defined by a carrier-specific YAML; **AWS Bedrock (Claude)** maps advisor + states into that shape.

### Upload and use a carrier format

1. **Upload a format YAML:** `POST /api/admin/carrier-formats/{carrier_id}` with a YAML file (carrier IDs 1–8). Stored under `local_data/carrier_formats/{carrier_id}.yaml`.
2. **On transfer** (create-and-transfer, dispatch-all, or submit): if that carrier has a YAML, the backend uses Bedrock to build the request body; otherwise it uses the built-in simple or structured builder.
3. **Bedrock:** Set `AWS_REGION` and ensure Bedrock access (e.g. `anthropic.claude-3-5-sonnet-v2:0`). Override with `BEDROCK_CLAUDE_MODEL_ID`.

**Endpoints:**  
- List formats: `GET /api/admin/carrier-formats`  
- Get/sample: `GET /api/admin/carrier-formats/{id}`, `GET /api/admin/carrier-formats/sample`  
- Test transform (no submit): `POST /api/admin/carrier-formats/test-transform` with `{"carrier_id":"1","advisor_id":"<uuid>","states":["AL"]}`

### Carrier defaults (no custom YAML)

| Carrier ID | Default | Custom YAML |
|------------|---------|-------------|
| 1 | simple | Optional |
| 2 | structured | Optional |
| 3–8 | simple | Optional |

---

## Document extraction (OCR)

`POST /api/documents/extract` (or the mounted extract route) forwards PDF/Excel/images to an **external OCR service** (configurable via `OCR_SERVICE_URL`). The orchestration service does not run OCR itself; it delegates to that service and returns the extracted result. See the repo’s document-extraction docs for OCR service setup (e.g. Poppler for PDFs).

---

## Async carrier dispatch and status

- **Dispatch:** Create-and-transfer, dispatch-all, and submit return immediately with `status: "queued"` and `submission_ids`. The actual HTTP calls to the carrier APIs run in the **background**.
- **Logs:** In the backend terminal you’ll see `[CARRIER] Dispatch started`, then `[CARRIER] Hitting carrier API: POST .../standard/simple/appointments` (or `.../standard/structured/...` or `.../custom/appointments`). For custom or Bedrock-built payloads you’ll see `[BEDROCK]` logs.
- **Status updates:** Carriers (or tests) can update submission status via **`POST /api/carrier/appointments/status`** (webhook). The orchestration service stores the new status and audit data.
- **Polling:** `GET /api/admin/carrier-submissions` to see status move from `queued` to `sent_to_carrier`, `completed`, or `error`/`rejected`.

**Example (create-and-transfer with Bearer token):**
```bash
curl -s -X POST http://localhost:8000/api/admin/create-and-transfer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"agent":{"npn":"99999","first_name":"Demo","last_name":"User","email":"d@e.com","phone":"555-0000","broker_dealer":"BD","license_states":["CA","TX"]},"carriers":["1","2","3"],"states":["CA"]}'
```

---

## AWS SNS notifications

Optional notifications for agent transfers, document processed, and custom events. Set `SNS_ENABLED=true`, `SNS_TOPIC_ARN`, and AWS credentials in `.env`. See [SNS_SETUP.md](SNS_SETUP.md) and [SNS_TRIGGERS.md](SNS_TRIGGERS.md).

---

## Environment

| Variable | Purpose |
|----------|---------|
| `USE_JSON_STORE` | `true` (default): local JSON under `local_data/`; `false`: use DB (`DATABASE_URL`) |
| `AUTH_TOKEN` | Bearer token for `/api/*` (default in code) |
| `CARRIER_BASE_URL` | Base URL for carrier API calls (default: http://localhost:8000) |
| `OCR_SERVICE_URL` | Document extraction service URL |
| `AWS_REGION` | Bedrock and SNS (default: us-east-1) |
| `BEDROCK_CLAUDE_MODEL_ID` | Optional; Bedrock model (or inference profile ARN) for carrier format transform |
| `SNS_TOPIC_ARN`, `SNS_ENABLED` | Optional; SNS notifications |

---

## Relevant docs

- **[TESTING.md](TESTING.md)** — End-to-end testing, logs, standard vs custom flows.
- **Swagger** — http://localhost:8000/docs (use **Authorize** with the Bearer token).
- **Carrier API paths** — Under the **Carrier** tag: `standard/simple/appointments`, `standard/structured/appointments`, `custom/appointments`, and `appointments/status` (webhook).
