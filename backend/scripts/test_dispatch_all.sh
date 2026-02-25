#!/usr/bin/env bash
# Test dispatch-all: run dispatch to multiple carriers and verify payloads/carrier_format.
# Usage: ./scripts/test_dispatch_all.sh [BASE_URL]
# Example: ./scripts/test_dispatch_all.sh http://localhost:8000
# Requires: backend running with USE_JSON_STORE=true (default).
# Tip: Run backend in foreground (uvicorn) to see logs: "Carrier X: building payload via direct flat builder"
#      vs "building payload via Bedrock (custom YAML)" and "Creating carrier API request: POST ...".

set -e
BASE_URL="${1:-http://localhost:8000}"
echo "=== Dispatch-all test (base_url=$BASE_URL) ==="

# 1. Get first advisor
ADVISORS=$(curl -s "$BASE_URL/api/admin/advisors")
ADVISOR_ID=$(echo "$ADVISORS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || true)
if [ -z "$ADVISOR_ID" ]; then
  echo "No advisors found. Seed first: curl -s -X POST $BASE_URL/api/admin/seed"
  exit 1
fi
echo "Using advisor_id: $ADVISOR_ID"

# 2. Dispatch to carriers 1 (flat), 2 (nested), 3 (may have custom YAML)
BODY=$(cat <<EOF
{
  "carriers": [
    { "carrier_id": "1", "carrier_format": "flat", "submitted_states": ["AL", "CA"] },
    { "carrier_id": "2", "carrier_format": "nested", "submitted_states": ["AL", "CA"] },
    { "carrier_id": "3", "carrier_format": "flat", "submitted_states": ["AL", "CA"] }
  ],
  "carrier_base_url": "$BASE_URL"
}
EOF
)
RESP=$(curl -s -X POST "$BASE_URL/api/admin/advisors/$ADVISOR_ID/carriers/dispatch-all" \
  -H "Content-Type: application/json" \
  -d "$BODY")
echo "Dispatch response: $RESP"

SUB_IDS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(d.get('submission_ids',[])))" 2>/dev/null || true)
if [ -z "$SUB_IDS" ]; then
  echo "No submission_ids in response. Check response above."
  exit 1
fi
echo "Submission IDs: $SUB_IDS"
echo "(Dispatch runs synchronously; carrier API calls complete before this response.)"

# 3. Dispatch is synchronous; submissions are already sent. List submissions to verify.
# 4. List submissions and show carrier_format + payload shape + status (only our submission_ids)
SUBS=$(curl -s "$BASE_URL/api/admin/carrier-submissions")
echo ""
echo "=== Submissions from this run (carrier_format, status, payload top-level keys) ==="
export SUB_IDS
echo "$SUBS" | python3 -c "
import sys, json, os
want = set(os.environ.get('SUB_IDS','').split())
d = json.load(sys.stdin)
if not d.get('success') or not d.get('data'):
    print(d)
else:
    for s in d['data']:
        if want and s.get('id') not in want:
            continue
        rid = (s.get('id') or '')[:8]
        cid = s.get('carrier_id', '')
        req = s.get('request_data') or {}
        fmt = req.get('carrier_format', '?')
        payload = req.get('payload') or {}
        keys = list(payload.keys())[:10]
        status = s.get('status', '?')
        res = s.get('response_data') or {}
        r = res.get('carrier_api_response')
        api_status = r.get('status', '') if isinstance(r, dict) else ''
        print('  id=%s... carrier_id=%s format=%s status=%s payload_keys=%s' % (rid, cid, fmt, status, keys))
        if api_status:
            print('    -> carrier_api response status: %s' % api_status)
"

echo ""
echo "Expected: carrier 1=flat, carrier 2=nested, carrier 3=custom_yaml (if YAML uploaded). status should be sent_to_carrier if dispatch succeeded."

# --- Curl-only copy-paste (replace ADVISOR_ID and BASE_URL) ---
# ADVISOR_ID=$(curl -s http://localhost:8000/api/admin/advisors | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
# curl -s -X POST http://localhost:8000/api/admin/advisors/$ADVISOR_ID/carriers/dispatch-all -H "Content-Type: application/json" -d '{"carriers":[{"carrier_id":"1","carrier_format":"flat","submitted_states":["AL","CA"]},{"carrier_id":"2","carrier_format":"nested","submitted_states":["AL","CA"]},{"carrier_id":"3","carrier_format":"flat","submitted_states":["AL","CA"]}],"carrier_base_url":"http://localhost:8000"}'
# sleep 4 && curl -s http://localhost:8000/api/admin/carrier-submissions
