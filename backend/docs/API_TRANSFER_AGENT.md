# API: Enter agent details + initiate transfer (one call)

Use this when the UI combines “enter agent details” and “initiate transfer” on one page. One request creates the agent and submits transfer requests for the chosen carriers and states.

---

## Endpoint

**`POST /api/admin/create-and-transfer`**

- **Content-Type:** `application/json`
- **Requires:** `USE_JSON_STORE=true` (default for local backend).

---

## Request body

| Field      | Type     | Required | Description |
|-----------|----------|----------|-------------|
| `agent`   | object   | Yes      | Agent details (same shape as create-advisor). |
| `carriers`| string[] | Yes      | List of carrier IDs, e.g. `["1", "2", "3"]`. |
| `states`  | string[] | Yes      | List of state codes, e.g. `["AL", "CA", "TX"]`. |
| `carrier_base_url` | string | No  | Override carrier API base URL (default from env). |

### `agent` object (same as `POST /api/admin/advisors`)

| Field            | Type     | Required | Description |
|------------------|----------|----------|-------------|
| `npn`            | string   | Yes      | National Producer Number. |
| `first_name`     | string   | No       | |
| `last_name`     | string   | No       | |
| `email`          | string   | No       | |
| `phone`          | string   | No       | |
| `broker_dealer`  | string   | No       | |
| `license_states` | string[] | No       | e.g. `["CA", "TX"]`. |
| `status`         | string   | No       | Default `"pending"`. |

**Example request:**

```json
{
  "agent": {
    "npn": "12345678",
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com",
    "phone": "555-0101",
    "broker_dealer": "Example BD",
    "license_states": ["CA", "TX"],
    "status": "pending"
  },
  "carriers": ["1", "2", "3"],
  "states": ["AL", "CA"]
}
```

---

## Response

**200 OK**

```json
{
  "success": true,
  "advisor_id": "uuid-of-created-agent",
  "submission_ids": ["id1", "id2", "id3", ...],
  "status": "sent_to_carrier"
}
```

- **`advisor_id`:** ID of the created agent.
- **`submission_ids`:** One submission per (carrier, state). Example: 2 carriers × 2 states → 4 IDs.
- **`status`:** Always `"sent_to_carrier"` when the call succeeds (dispatch is synchronous).

---

## Errors

| Status | Meaning |
|--------|--------|
| **400** | `USE_JSON_STORE` is not true, or validation error. |
| **409** | Agent with this NPN already exists. |
| **500** | Server error (e.g. advisor created but not found). |

---

## Behaviour (for UI)

1. Backend creates one agent from `agent`.
2. For each pair (carrier, state), it creates one transfer submission and dispatches it.
3. Response is returned after all carrier API calls complete.
4. UI can use `submission_ids` or `advisor_id` to link to “Pending transfers” or agent detail.

No separate “create agent” then “submit transfer” calls are required; this single API does both.
