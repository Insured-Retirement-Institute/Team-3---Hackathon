#!/usr/bin/env bash
# Test the three carrier API endpoints with sample payloads (no Bedrock, direct payloads).
# Usage: ./scripts/test_carrier_endpoints.sh [BASE_URL]
# Requires: backend running (e.g. http://localhost:8000).
# Endpoints: dummy/1 (flat), dummy/2 (nested), /appointments (custom JSON).

set -e
BASE_URL="${1:-http://localhost:8000}"
echo "=== Testing carrier endpoints (base_url=$BASE_URL) ==="

# 1. Flat format -> POST /api/carrier/dummy/1/appointments
echo ""
echo "--- 1. Flat format (direct): POST /api/carrier/dummy/1/appointments ---"
FLAT_RESP=$(curl -s -X POST "$BASE_URL/api/carrier/dummy/1/appointments" \
  -H "Content-Type: application/json" \
  -d '{
    "carrierId": "1",
    "advisor": {
      "advisor_id": "test-advisor-001",
      "npn": "12345678",
      "first_name": "Jane",
      "last_name": "Smith",
      "email": "jane@example.com",
      "phone": "555-0101",
      "broker_dealer": "Example BD",
      "license_states": ["CA", "TX"]
    },
    "statesRequested": ["AL", "CA"]
  }')
echo "$FLAT_RESP" | python3 -m json.tool 2>/dev/null || echo "$FLAT_RESP"

# 2. Nested format -> POST /api/carrier/dummy/2/appointments
echo ""
echo "--- 2. Nested format (direct): POST /api/carrier/dummy/2/appointments ---"
NESTED_RESP=$(curl -s -X POST "$BASE_URL/api/carrier/dummy/2/appointments" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": { "carrier_id": "2" },
    "agent": {
      "advisor_id": "test-advisor-002",
      "npn": "87654321",
      "name": { "first": "John", "last": "Doe" },
      "contacts": [
        { "type": "email", "value": "john@example.com" },
        { "type": "phone", "value": "555-0102" }
      ],
      "broker_dealer": "Other BD",
      "license_states": ["CA", "FL"]
    },
    "appointment": { "states": ["AL", "CA"] }
  }')
echo "$NESTED_RESP" | python3 -m json.tool 2>/dev/null || echo "$NESTED_RESP"

# 3. Custom format (Bedrock-style payload) -> POST /api/carrier/appointments
echo ""
echo "--- 3. Custom format (e.g. Bedrock-generated): POST /api/carrier/appointments ---"
CUSTOM_RESP=$(curl -s -X POST "$BASE_URL/api/carrier/appointments" \
  -H "Content-Type: application/json" \
  -d '{
    "application": {
      "carrier_code": "3",
      "applicant": {
        "id": "test-advisor-003",
        "national_producer_number": "11223344",
        "first_name": "Maria",
        "last_name": "Garcia",
        "email_address": "maria@example.com",
        "phone_number": "555-0103",
        "broker_dealer": "Another BD",
        "licensed_states": ["TX", "AZ"]
      },
      "jurisdictions": ["AL", "CA"]
    }
  }')
echo "$CUSTOM_RESP" | python3 -m json.tool 2>/dev/null || echo "$CUSTOM_RESP"

echo ""
echo "Done. All three carrier endpoints should return 200 and a success-style response."
