# Advisor Onboarding API

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

## Environment

- `USE_JSON_STORE` — set to `true` (default) to use local JSON files under `local_data/`; set to `false` to use a database (set `DATABASE_URL`).
- `S3_BUCKET` — optional; if set, advisor file uploads go to S3; if unset, uploads are stored under `local_data/uploads/` for local dev.
- `CARRIER_BASE_URL` — base URL for carrier API calls (default: http://localhost:8000).
- `BEDROCK_CLAUDE_MODEL_ID` — optional; Bedrock model for YAML-based transform (default: `anthropic.claude-3-5-sonnet-v2:0`).
- `AWS_REGION` — used for Bedrock (default: us-east-1).
