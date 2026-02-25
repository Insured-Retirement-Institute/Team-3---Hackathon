# Advisor Onboarding API

## Restart backend and frontend

- **Backend:** In a terminal, run the server so logs are visible (see [Run locally](#run-locally) below). All `[CARRIER]` and `[BEDROCK]` logs appear in this terminal.
- **Frontend:** In another terminal: `cd frontend && npm run dev` → app at http://localhost:5173.
- **Full testing steps and how to view logs (flat vs custom YAML, Bedrock):** see **[TESTING.md](TESTING.md)**.

## Run locally

1. **Create venv and install dependencies** (first time only):
   ```bash
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Start the server** (uses JSON file storage by default; no database required):
   ```bash
   cd backend
   USE_JSON_STORE=true .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Open **http://localhost:8000/docs** for Swagger UI.

## Insert sample data (local JSON store)

With the server running and `USE_JSON_STORE=true`:

- **Option A – API:** `curl -X POST http://localhost:8000/api/admin/seed`  
  Creates 3 sample advisors (Jane Smith, John Doe, Maria Garcia). Safe to call multiple times (skips existing NPNs).

- **Option B – Script (no server):**  
  `cd backend && USE_JSON_STORE=true .venv/bin/python scripts/seed_advisors.py`  
  Writes directly to `local_data/advisors.json`.

You can also create advisors one by one with `POST /api/admin/advisors` (see Swagger).

## Carrier format YAML + Bedrock transform

You can define each carrier’s **request (and optionally response) format** in a YAML file. That YAML is stored locally and used so that **AWS Bedrock (Claude 3.5 Sonnet)** transforms advisor data into the carrier’s expected shape before the carrier API is called.

1. **Upload a format YAML** for a carrier:
   - `POST /api/admin/carrier-formats/{carrier_id}` with a YAML file in the request body (e.g. `carrier_id=carrier-a`).
   - YAML describes the expected request body structure (and optionally response). Examples: `carrier_format_examples/carrier-a.example.yaml`, `carrier_format_examples/carrier-b.example.yaml`.

2. **Stored location:** `local_data/carrier_formats/{carrier_id}.yaml`.

3. **When you submit an advisor to that carrier** (e.g. `POST /api/admin/advisors/{id}/carriers/submit` or dispatch-all), if a format YAML exists for that carrier, the backend calls Bedrock to produce the request body from the advisor + states; otherwise it uses the built-in **flat** or **nested** payload builders.

4. **Bedrock:** Set `AWS_REGION` and ensure the runtime has Bedrock access and a model such as `anthropic.claude-3-5-sonnet-v2:0`. Override with `BEDROCK_CLAUDE_MODEL_ID`. If Bedrock is unavailable, the built-in payload format is used.

- **List format IDs:** `GET /api/admin/carrier-formats` — includes `template_used` (custom_yaml) and `default_template` (flat/nested) per carrier.
- **Get format YAML:** `GET /api/admin/carrier-formats/{carrier_id}`  
- **Standard template (reference):** `GET /api/admin/carrier-formats/sample` — returns the **standard (flat)** YAML. Use as reference when uploading carrier-specific YAMLs.
- **Which carrier uses which template:** `GET /api/admin/carriers` returns each carrier with `default_template` (**flat** or **nested**) and `has_custom_yaml`. Carrier IDs are numeric (1–8). Default: 1 → flat, 2 → nested, 3–8 → flat.
- **Test transform (no submit):** `POST /api/admin/carrier-formats/test-transform` with `{"carrier_id": "1", "advisor_id": "<uuid>", "states": ["AL"]}` — returns the exact JSON payload. Use to compare built-in vs custom YAML without async dispatch.

**Test the sample endpoint** (with backend running on port 8000):
```bash
curl -s http://localhost:8000/api/admin/carrier-formats/sample
```
Expected: `{"success":true,"yaml":"# Sample carrier request format...","description":"..."}`. If you get "Connection refused", start the backend first. If the frontend still shows "Could not load sample", ensure `VITE_API_BASE_URL` points to the same origin (e.g. `http://localhost:8000` when running the API locally).

### Do all carriers have their own YAML?

**No.** Only carriers you explicitly upload a YAML for use a custom format. The rest use a **default built-in** template:

| Carrier ID | Default template | Custom YAML? |
|------------|------------------|--------------|
| 1          | flat   | Only if you upload one |
| 2          | nested | Only if you upload one |
| 3 … 8      | flat (standard) | Only if you upload one |

- **flat** = payload shape: `carrierId`, `advisor`, `statesRequested`.
- **nested** = payload shape: `meta`, `agent`, `appointment`.
- **No YAML uploaded** → backend uses the default (flat or nested) to build the payload; no Bedrock call.
- **YAML uploaded** → backend uses Bedrock to transform advisor + states into JSON matching the YAML; then sends that to the carrier.

So you can have zero, one, or many carriers with custom YAMLs; the rest always use the default template.

### Sample YAML to test the API

Use the file **`carrier_format_examples/sample-for-testing.yaml`** to test upload and test-transform:

1. **Upload (UI):** Carrier format YAML page → choose a carrier (e.g. **Principal** / 3) → Choose file → select `backend/carrier_format_examples/sample-for-testing.yaml` → Upload.
2. **Test transform (UI):** Same page → Test transform → Carrier: Principal, Agent: pick one → **Run test**. You should see `format_used: "custom_yaml"` and a payload matching the YAML shape (when Bedrock is available); otherwise you still get the default payload.
3. **Test transform (curl):**
   ```bash
   curl -s -X POST http://localhost:8000/api/admin/carrier-formats/test-transform \
     -H "Content-Type: application/json" \
     -d '{"carrier_id":"1","advisor_id":"<advisor-uuid>","states":["AL","AK"]}'
   ```
   Replace `<advisor-uuid>` with an advisor ID from `GET /api/admin/advisors`. Response: `{"success":true,"payload":{...},"format_used":"flat","carrier_id":"1"}`.

### See if Bedrock is actually working (different payload shape)

Use **`carrier_format_examples/bedrock-test-format.yaml`**. That YAML describes a **different** structure: `application`, `applicant`, `jurisdictions` (instead of `advisor`, `statesRequested`). So you can tell at a glance whether the payload came from Bedrock or from the built-in template.

1. Upload `bedrock-test-format.yaml` for one carrier (e.g. **Principal** / 3).
2. **Test transform** for that carrier + any agent → **Run test**.
3. **If Bedrock is working:** `format_used` is `"custom_yaml"` and the payload has top-level `application` with `applicant` and `jurisdictions` (and possibly different field names like `national_producer_number`, `email_address`).
4. **If Bedrock is not used** (no AWS credentials or Bedrock unavailable): `format_used` is `"flat"` and the payload has `carrierId`, `advisor`, `statesRequested` — same as the built-in flat template.

Other example YAMLs: `carrier-a.example.yaml` (flat shape), `carrier-b.example.yaml` (nested shape: meta/agent/appointment).

### Custom YAML: supported shapes

The Bedrock transform supports **any** carrier YAML shape:

| YAML shape | Supported |
|------------|-----------|
| **Single name field** (e.g. `full_name`, `agent_name`) | Yes – AI merges advisor `first_name` + `last_name` into one value. |
| **Separate first/last** (e.g. `first_name`, `last_name` or `agent_first_name`, `agent_last_name`) | Yes – AI maps advisor `first_name` and `last_name` to those keys at any nesting level. |
| **Arbitrary nesting** (e.g. `application.applicant`, `meta.agent.contacts`, `level1.level2.level3`) | Yes – output JSON matches the exact structure and depth in the YAML. |
| **Different field names** (e.g. `national_producer_number`, `email_address`, `jurisdictions`) | Yes – AI maps by meaning (npn → national_producer_number, states → jurisdictions, etc.). |

You can mix these: e.g. a deeply nested YAML with a single `applicant.full_name` or with separate `applicant.first_name` and `applicant.last_name`. The model is instructed to conform to the schema and map advisor data into it.

## Async carrier dispatch (background only)

Carrier API calls run **only in the background**. Create-and-transfer, dispatch-all, and submit return immediately with `status: "queued"` and `submission_ids`; the actual HTTP calls to the carrier happen asynchronously.

**How to test:**

1. Start the backend with logs visible: `USE_JSON_STORE=true .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
2. Create a transfer (e.g. from the UI **Create agent & transfer** or curl below). The API returns right away with `"status": "queued"`.
3. Watch the **server logs**: you’ll see `[CARRIER] Dispatch started`, then `[CARRIER] Hitting carrier API: POST ...` for each submission. For carriers using **custom YAML** or **nested (Bedrock)** you’ll see `[BEDROCK] Using Bedrock to build carrier request...` and `[BEDROCK] Invoking Claude...` before the carrier call.
4. Poll submissions: `GET /api/admin/carrier-submissions` — status moves from `queued` to `sent_to_carrier` (or `error`) as the background task runs.

**Example (create-and-transfer, async):**
```bash
curl -s -X POST http://localhost:8000/api/admin/create-and-transfer \
  -H "Content-Type: application/json" \
  -d '{"agent":{"npn":"99999","first_name":"Demo","last_name":"User","email":"d@e.com","phone":"555-0000","broker_dealer":"BD","license_states":["CA","TX"]},"carriers":["1","2","3"],"states":["CA"]}'
```
Response is immediate with `"status": "queued"`. Check logs for `[BEDROCK]` when carrier 2 (nested) or 3 (if custom YAML uploaded) is processed.

## Data sources for carrier request payload (demo)

When a **transfer request is created** (create-and-transfer, dispatch-all, or submit), the payload sent to the carrier is built from:

| Source | Where it comes from |
|--------|---------------------|
| **Advisor data** | `json_store.get_advisor(advisor_id)` (or the advisor from the request). Fields: `npn`, `first_name`, `last_name`, `email`, `phone`, `broker_dealer`, `license_states`. |
| **Submitted states** | Request body: `body.states` in create-and-transfer, or per-carrier `submitted_states` in dispatch-all/submit. |
| **YAML format** | Loaded **at request time** from `carrier_formats_store.load_carrier_format(carrier_id)` → reads `backend/local_data/carrier_formats/{carrier_id}.yaml`. |

So: **add or update a carrier format (YAML) before creating a transfer**; the next transfer that includes that carrier will use the current YAML from disk. No restart needed. For carriers with custom YAML, Bedrock is invoked with that YAML + advisor + states to produce the JSON request body; for flat/nested without custom YAML, the built-in builders (or Bedrock with built-in nested YAML) are used.

## AWS SNS Notifications

The API includes built-in support for sending notifications via **AWS SNS (Simple Notification Service)**:

- **Automatic notifications** when agents are transferred to carriers
- **Automatic notifications** when agents are dispatched to multiple carriers  
- **Automatic notifications** for single carrier submissions
- Optional notifications when documents are processed
- Custom notifications for workflow events

### Automatic Triggers

SNS notifications are **automatically sent** for:
- `POST /api/admin/create-and-transfer` - Agent created and transferred
- `POST /api/admin/advisors/{id}/carriers/dispatch-all` - Dispatched to multiple carriers
- `POST /api/admin/advisors/{id}/carriers/{carrier_id}/submit` - Single carrier submission

See [SNS_TRIGGERS.md](SNS_TRIGGERS.md) for complete trigger documentation.

### Quick Setup

1. **Configure AWS credentials and SNS topic in `.env`:**
   ```env
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789:your-topic
   SNS_ENABLED=true
   ```

2. **Test SNS:**
   ```bash
   cd backend
   .venv/bin/python test_sns.py
   ```

3. **API Endpoints:** All SNS endpoints are under `/api/notifications`. See interactive docs at `http://localhost:8000/docs#/Notifications`.

4. **Full documentation:** See [SNS_SETUP.md](SNS_SETUP.md) for complete setup instructions, API reference, and examples.

### Example Usage

Send notification when document is processed:
```bash
curl -X POST "http://localhost:8000/api/extract?send_notification=true" \
  -F "file=@advisor_form.pdf"
```

Send custom notification:
```bash
curl -X POST "http://localhost:8000/api/notifications/send" \
  -H "Content-Type: application/json" \
  -d '{"subject": "Test", "message": "Hello from API"}'
```

## Environment

- `USE_JSON_STORE` — set to `true` (default) to use local JSON files under `local_data/`; set to `false` to use a database (set `DATABASE_URL`).
- `S3_BUCKET` — optional; if set, advisor file uploads go to S3; if unset, uploads are stored under `local_data/uploads/` for local dev.
- `CARRIER_BASE_URL` — base URL for carrier API calls (default: http://localhost:8000).
- `BEDROCK_CLAUDE_MODEL_ID` — optional; Bedrock model for YAML-based transform. If you see "on-demand throughput isn't supported", your account may require an **inference profile** ARN instead of the model ID (set this env to the profile ARN from the Bedrock console). The code will try fallback models and log at INFO when one succeeds.
- `AWS_REGION` — used for Bedrock and SNS (default: us-east-1).
- `SNS_TOPIC_ARN` — optional; ARN of SNS topic for notifications.
- `SNS_ENABLED` — optional; set to `true` to enable SNS notifications (default: false).
