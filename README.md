# Advisor Onboarding – Web Portal & Orchestration

This repository contains the **Advisor Onboarding** product: a web portal (React frontend) and orchestration API (backend) for creating agents, submitting transfer requests to carriers, and processing documents. The system supports standard and custom carrier formats and uses AWS Bedrock for document parsing and carrier payload transformation where needed.

---

## Architecture

High-level flow:

1. **Web portal (React frontend)** – Users create agents, upload documents, trigger transfers to carriers, and view submission status.
2. **Orchestration Service (backend API)** – Receives requests from the frontend, coordinates carrier submissions, calls an external OCR service for document extraction, and stores transfer status and audit data.
3. **Carrier adaptor** – Builds request payloads in standard (simple/structured) or custom (YAML-defined) format and dispatches to carrier assignment APIs. Uses **AWS Bedrock (Claude)** when a carrier has a custom format YAML.
4. **Carrier assignment APIs** – Standard endpoints (`/api/carrier/standard/simple/appointments`, `/api/carrier/standard/structured/appointments`) and a custom endpoint (`/api/carrier/custom/appointments`) for carrier-specific payloads.
5. **Carrier platforms** – Send status updates back via webhook (`POST /api/carrier/appointments/status`), which the orchestration service persists and exposes through the admin API.

![Architecture flow](docs/architecture-flow.png)

*Place the architecture flow diagram image at `docs/architecture-flow.png` (e.g. the diagram showing Web Portal → React Frontend → Orchestration Service → Carrier Adaptor / OCR / Database and Carrier Platform → Webhook Callback).*

---

## What’s in this repo

| Area | Description |
|------|-------------|
| **`frontend/`** | React (React Router) web app: dashboard, create-and-transfer, carrier formats, upload document, pending transfers. |
| **`backend/`** | FastAPI orchestration API: advisors, carrier submissions, carrier format YAML, document extract (pass-through to OCR), carrier webhook, SNS. |

---

## Quick start (frontend + backend)

1. **Backend (orchestration API)**  
   See **[backend/README.md](backend/README.md)** for venv, env vars, and Bearer token.
   ```bash
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   USE_JSON_STORE=true .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend (web portal)**  
   See **[frontend/README.md](frontend/README.md)** for npm and `VITE_API_BASE_URL`.
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   App: http://localhost:5173. Set `VITE_AUTH_TOKEN` (and optionally `VITE_API_BASE_URL`) so the frontend can call the backend (see backend README).

3. **API docs** – http://localhost:8000/docs (Swagger). Use **Authorize** with the Bearer token.

---

## Product capabilities

- **Agents** – Create and list advisors/agents; optional seed script for sample data.
- **Transfers** – Submit agents to one or multiple carriers (create-and-transfer, dispatch-all, or single-carrier submit). Payload is built in standard simple, standard structured, or custom (Bedrock + carrier YAML) format.
- **Carrier formats** – Upload per-carrier YAML to define custom request shapes; Bedrock maps advisor data into that shape. Standard formats (simple/structured) are built in.
- **Document upload** – Upload PDF/Excel/images for extraction; backend forwards to an external OCR service and returns structured data; optional transfer-from-document flow.
- **Status and webhooks** – Carriers (or tests) update submission status via `POST /api/carrier/appointments/status`; UI and `GET /api/admin/carrier-submissions` show status (e.g. completed, rejected with reason).
- **SNS** – Optional AWS SNS notifications for transfer and document events (see backend README).

---

## Docs and references

- **[backend/README.md](backend/README.md)** – API setup, auth, carrier formats, Bedrock, SNS, environment.
- **[frontend/README.md](frontend/README.md)** – Frontend setup and run.
- **backend [TESTING.md](backend/TESTING.md)** – End-to-end testing and logs (standard vs custom, Bedrock).
- **OpenAPI** – http://localhost:8000/docs when the backend is running.

---

## IRI and governance

- **Get started** – [SwaggerHub](https://www.swaggerhub.com) is being stood up for OpenAPI definitions.
- **Style guide** – [IRI Style Guide](https://github.com/Insured-Retirement-Institute/Style-Guide) for technical governance, data dictionary, and code of conduct.
- **Business case / user stories** – To be loaded in this repo or linked here.
- **Business owners** – Carrier, Distributor, Solution Provider (contacts TBD).
- **Engage and contribute** – Contact IRI (e.g. hpikus@irionline.org) for working group discussions.
- **Issues and security** – Report security issues to Katherine Dease (kdease@irionline.org). Other issues and bugs via the repository Issues tab; change requests per standards governance on the [main page](https://github.com/Insured-Retirement-Institute).
