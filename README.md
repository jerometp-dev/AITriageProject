# Enterprise AI Omnichannel Triage Engine

An automated, production-grade AI incident classification and orchestration engine designed to intake raw customer support tickets, dynamically structure and analyze context via LLMs, preserve transactional history, and dispatch real-time operational alerts to Slack infrastructure.

## 🏗️ System Architecture & Data Flow

```text
[Inbound Webhook / UI Request] 
       │
       ▼
[Pydantic Validation Layer] ──(If Invalid)──► [Log Error & Drop]
       │
       ▼
[Groq LLM Client API] ──► [Contextual Extraction: Sentiment, Priority, Tagging]
       │
       ▼
[SQLite Transaction Log] ──► [Idempotent Storage & History Write]
       │
       ▼
[Slack Webhook Dispatcher] ──► [#support-triage Channel Alerting]