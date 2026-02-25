# Viewing carrier logs during demo

During a demo you can show that the backend **frames the request differently per carrier** (flat / nested / custom_yaml) and **hits each carrier API**. All of this is logged with the `[CARRIER]` prefix.

## Where to view logs

**Run the backend in a terminal (foreground).** Logs are printed to **that same terminal**.

1. Open a terminal.
2. From the repo:
   ```bash
   cd backend
   .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```
   (Or use your usual way to start the backend, e.g. `source venv/bin/activate` then `uvicorn ...`.)

3. Leave this terminal visible during the demo. Every request that builds payloads or calls carrier APIs will produce lines here.

## What you’ll see

When you trigger **dispatch-all** (or submit to a carrier), you’ll see lines like:

**Framing the request (different format per carrier):**
```
[CARRIER] Framing request for carrier_id=1 as format=flat (direct builder)
[CARRIER] Framing request for carrier_id=2 as format=nested (Bedrock + built-in YAML)
[CARRIER] Framing request for carrier_id=3 as format=custom_yaml (Bedrock + uploaded YAML)
[CARRIER] Carrier 3 payload shaped with keys: ['application', ...]
```

**Hitting each carrier API:**
```
[CARRIER] Dispatch started: 3 submission(s), base_url=http://localhost:8000
[CARRIER] Hitting carrier API: POST http://localhost:8000/api/carrier/dummy/1/appointments (carrier_id=1, format=flat)
[CARRIER] Carrier API responded: /api/carrier/dummy/1/appointments carrier_id=1 status=200 keys=[...]
[CARRIER] Hitting carrier API: POST http://localhost:8000/api/carrier/dummy/2/appointments (carrier_id=2, format=nested)
[CARRIER] Carrier API responded: /api/carrier/dummy/2/appointments carrier_id=2 status=200 keys=[...]
[CARRIER] Hitting carrier API: POST http://localhost:8000/api/carrier/appointments (carrier_id=3, format=custom_yaml)
[CARRIER] Carrier API responded: /api/carrier/appointments carrier_id=3 status=200 keys=[...]
```

## Quick test

1. Start backend in terminal (see above).
2. In another terminal run:
   ```bash
   cd backend && ./scripts/test_dispatch_all.sh
   ```
3. Watch the first terminal for the `[CARRIER]` lines.

## Filter only carrier logs (optional)

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | grep CARRIER
```

This shows only lines containing `CARRIER`.
