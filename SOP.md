# Standard Operating Procedure (SOP): AI Omnichannel Triage Engine

**Document Reference:** SOP-AI-001  
**Target Role:** AI Automation Specialist / Support Engineers  
**System Status:** Operational-Production  

---

## 1. Objective & System Purpose
This document provides complete instructions for provisioning, operating, maintaining, and troubleshooting the AI Omnichannel Triage Engine. The engine acts as a resilient middle tier that absorbs inbound platform tickets, formats transactional data arrays under strict Pydantic rules, structures semantic analytics through the Groq LLaMA-3 model infrastructure, and routes priority payloads to live Slack alerts.

## 2. Environment Configuration & Variables
The codebase relies on strict isolation of credentials through an unindexed environment file (`.env`). If credentials expire or client webhooks change routing parameters, modify these keys securely within the local deployment scope:

* `GROQ_API_KEY`: Token authorizing access to the cloud LLM compilation gateway.
* `SLACK_WEBHOOK_URL`: The distinct target API URL directing structural payload formatting into the company workspace alert channels.

## 3. Data Integrity & Validation Enforcement
To maintain absolute data integrity across integrations, data inputs must strictly comply with the schema validation criteria outlined below. If any constraints fail, the engine intercepts the execution block to prevent downstream script failure:

| Field Name | Expected Data Type | Constraints / Validation Rules | Purpose |
| :--- | :--- | :--- | :--- |
| `intent` | String | Must evaluate contextually | Tracks client request type |
| `sentiment` | String | Evaluation classification text | Gauges customer satisfaction trends |
| `priority_score` | Integer | System scale mapping | Numerical priority rating (e.g., 1-5) |
| `summary` | String Text | Comprehensive summary string | Condenses the problem description |
| `recommended_action` | Strict Literal | **MUST** exactly be: `respond_with_bot` OR `escalate_to_human` | Directs downstream lifecycles |

## 4. Quality Control & Testing Routines
Before shipping any core modifications or updating client infrastructure, you must verify the state of your build by triggering the automated data integrity testing profile:

```bash
python -m unittest test_triage.py
```
---

## 5. System Access Controls & Token Rotation
To prevent unauthorized ingestion payloads, the middleware layer enforces strict authorization token matching. 
* **Authorization Scheme:** Secure Bearer Token validation via `INTERNAL_API_TOKEN`.
* **Token Storage:** Encrypted within the local machine's `.env` cluster scope.
* **Rotation Policy:** In production environments, client credentials and webhook secrets must be updated quarterly via the centralized credentials vault.

## 6. Troubleshooting & Disaster Recovery
If system processes drop or operational metrics stagnate, support engineers must execute the following triage workflow:

| Incident Scenario | Primary Symptom | Resolution Action |
| :--- | :--- | :--- |
| **Broker Failure** | Celery workers fail to receive inbound triage alerts. | Verify local Redis connection health: run `redis-cli ping` to confirm `PONG` response. |
| **API Rate-Limiting** | Groq Client throws HTTP `429` status codes. | The system automatically falls back to an exponential backoff retry scheme. If persistent, check API quota ceilings. |
| **Database Lock** | SQLite historical engine rejects concurrent read-writes. | Confirm database shared-cache parameters are safely active within `triage_engine.py` configurations. |