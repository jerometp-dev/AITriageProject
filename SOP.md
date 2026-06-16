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