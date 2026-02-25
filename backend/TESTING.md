# How to test: restart both apps and see Bedrock vs flat in logs

## 1. Restart backend and frontend

### Backend (Terminal 1)

Use a **dedicated terminal** so you can see all logs. Logs are printed in this terminal.

```bash
cd /Users/jayasreeneelapu/repos/irihackathon/Team-3---Hackathon/backend
source .venv/bin/activate
# If no venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
USE_JSON_STORE=true uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- Leave this running. Every request and every `[CARRIER]` / `[BEDROCK]` log line will appear here.
- API: **http://localhost:8000**  
- Docs: **http://localhost:8000/docs**

### Frontend (Terminal 2)

```bash
cd /Users/jayasreeneelapu/repos/irihackathon/Team-3---Hackathon/frontend
npm run dev
```

- Leave this running.
- App: **http://localhost:5173** (or the URL printed by the dev server)

---

## 2. Where to view logs (Bedrock vs flat)

**All logs come from the backend terminal (Terminal 1).**

- `[CARRIER]` = carrier dispatch and payload building.
- `[BEDROCK]` = Bedrock is used to transform advisor + states into the carrier request body **before** the carrier API is called.

So: **to see that Bedrock is used before sending the API request**, watch that same backend terminal for the sequence: **`[BEDROCK]` lines first**, then **`[CARRIER] Hitting carrier API`**.

---

## 3. Test with one flat carrier and one custom-format carrier

Goal: one carrier **flat** (no Bedrock), one carrier **custom YAML** (Bedrock). Then create one transfer and read the logs.

### Step 3.1 – Seed advisors (optional)

```bash
curl -s -X POST http://localhost:8000/api/admin/seed
```

### Step 3.2 – Upload custom YAML for one carrier (e.g. Principal = 3)

So we have:

- **Carrier 1 (MassMutual)** = flat only → no Bedrock, direct builder.
- **Carrier 3 (Principal)** = custom YAML → Bedrock transform, then carrier API.

Upload the test format (different shape so Bedrock is obvious):

From the **backend** directory:

```bash
cd /Users/jayasreeneelapu/repos/irihackathon/Team-3---Hackathon/backend
curl -s -X POST http://localhost:8000/api/admin/carrier-formats/3 \
  -F "file=@carrier_format_examples/bedrock-test-format.yaml"
```

Expected response: `{"success":true,"saved_as":"..."}`.  
YAML is stored under `backend/local_data/carrier_formats/3.yaml`.

### Step 3.3 – Create a transfer for carriers 1 (flat) and 3 (custom)

One request, one state, so you get **2 submissions** (carrier 1 + carrier 3):

```bash
curl -s -X POST http://localhost:8000/api/admin/create-and-transfer \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {
      "npn": "88880000",
      "first_name": "Log",
      "last_name": "Tester",
      "email": "log@test.com",
      "phone": "555-1111",
      "broker_dealer": "Test BD",
      "license_states": ["CA", "TX"]
    },
    "carriers": ["1", "3"],
    "states": ["CA"]
  }'
```

- Response returns **immediately** with `"status": "queued"` and two `submission_ids`.  
- The actual carrier calls run in the **background**. All action is in **Terminal 1 (backend)**.

---

## 4. Exact log lines to look for (in order)

In the **backend terminal**, you should see something like the following. Order matters: payload is built (with or without Bedrock), then the carrier API is hit.

### 4.1 – Background dispatch starts

```
[CARRIER] Dispatch started: 2 submission(s), base_url=http://localhost:8000
```

### 4.2 – Carrier 1 (flat) – **no Bedrock**

- Payload is built with the **direct flat builder** (no YAML, no Claude):

```
[CARRIER] Framing request for carrier_id=1 as format=flat (direct builder, no Bedrock)
```

- Then the carrier API is called:

```
[CARRIER] Hitting carrier API: POST http://localhost:8000/api/carrier/dummy/1/appointments (carrier_id=1, format=flat)
[CARRIER] Carrier API responded: ...
```

So for carrier 1 you **do not** see any `[BEDROCK]` line. That’s expected: flat format does not use Bedrock.

### 4.3 – Carrier 3 (custom YAML) – **Bedrock used**

- Bedrock is used to transform advisor + states into the custom YAML shape **before** the carrier API:

```
[BEDROCK] Using Bedrock to build carrier request for carrier_id=3 (custom YAML from carrier format upload)
[BEDROCK] Invoking Claude for carrier_id=3 (YAML-driven request body)
[BEDROCK] Bedrock transform succeeded for carrier_id=3 (custom_yaml), payload keys: ['application', ...]
```

- Then the carrier API is called with that Bedrock-generated payload:

```
[CARRIER] Hitting carrier API: POST http://localhost:8000/api/carrier/appointments (carrier_id=3, format=custom_yaml)
[CARRIER] Carrier API responded: ...
```

So for carrier 3 you **do** see the three `[BEDROCK]` lines above before the `[CARRIER] Hitting carrier API` line. That proves Bedrock is used to transform before sending the API request for the carrier that has a custom format.

---

## 5. Quick reference: what each carrier type logs

| Carrier setup              | Log you see (payload build) | Then |
|----------------------------|-----------------------------|------|
| **Flat (e.g. 1)**         | `[CARRIER] Framing request for carrier_id=1 as format=flat (direct builder, no Bedrock)` | No `[BEDROCK]`; then `[CARRIER] Hitting carrier API... dummy/1/appointments` |
| **Custom YAML (e.g. 3)**   | `[BEDROCK] Using Bedrock... carrier_id=3 (custom YAML...)` → `[BEDROCK] Invoking Claude...` → `[BEDROCK] Bedrock transform succeeded...` | Then `[CARRIER] Hitting carrier API... /appointments` |

---

## 6. Verify submissions after the run

```bash
curl -s http://localhost:8000/api/admin/carrier-submissions | python3 -m json.tool
```

- You should see two submissions (carrier 1 and 3) with `"status": "sent_to_carrier"` (and `request_data.payload` with the shape used: flat for 1, custom for 3).

---

## 7. Optional: test only from the UI

1. **Backend** and **frontend** running as above; logs in backend terminal.
2. **Carrier formats** page: upload `backend/carrier_format_examples/bedrock-test-format.yaml` for **Principal (3)**.
3. **Create agent & transfer**: create an agent, select carriers **MassMutual (1)** and **Principal (3)**, pick one state (e.g. CA), submit.
4. Watch **Terminal 1**: same sequence as in section 4 — flat for 1 (no `[BEDROCK]`), then Bedrock lines for 3, then carrier API calls.

---

## 8. If you don’t see `[BEDROCK]` for carrier 3

- **AWS credentials**: Bedrock must be available in the environment (e.g. `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` or `~/.aws/credentials`). If Bedrock fails, the code may fall back and you might see an error or flat payload.
- **Custom YAML present**: Confirm `backend/local_data/carrier_formats/3.yaml` exists (upload in step 3.2).
- **Carrier id in request**: Request must include `"carriers": ["1", "3"]` (or at least `"3"`) so that carrier 3 is processed and its format is loaded from disk.
