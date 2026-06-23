# Enterprise AI Omnichannel Triage Engine

An automated, production-grade AI incident classification and orchestration engine designed to intake raw customer support tickets, dynamically structure and analyze context via LLMs, preserve transactional history, and dispatch real-time operational alerts to Slack infrastructure.

## 🏗️ System Architecture & Data Flow

```text
[Inbound Webhook / Streamlit UI Request] 
               │
               ▼
   [FastAPI Ingestion Endpoint]
               │
               ▼
┌────────────────────────────────────────┐
│  Vector Database Context Extraction    │ ◄─── [ChromaDB Policy Store]
└────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│     Groq LLM Intelligence Client       │ ──► Analytics Payload
└────────────────────────────────────────┘     (Intent, Sentiment, Priority)
               │
               ▼
   Is Priority >= 4 / Human Action?
               │
               ├──► YES ──► [Celery Task Queue] ──► [Redis Broker] ──► 🚨 Live Slack Alert
               │
               └──► NO  ──► [Contextual RAG Model Generation] ──► 🤖 UI Auto-Reply Card
               │
               ▼
┌────────────────────────────────────────┐
│  SQLite Shared-Cache Transaction Log   │ ──► Idempotent Historical Tracking
└────────────────────────────────────────┘

## 🛠️ Core Production Architectures
       Decoupled Asynchronous Processing: Offloads heavy downstream execution tasks (like hitting external Slack endpoints) to a background worker pool using Celery and Redis, maintaining lightning-fast API responses.            
       
       Context-Aware Local RAG: Queries an integrated ChromaDB instance to pull live company operational policies, dynamically appending factual data to the LLM context layer to eradicate AI hallucinations.
       
       Smart Escalation Fail-Safes: Enforces rigid automated routing pathways. Sensitive intents or high-priority tickets ($Urgency \ge 4/5$) bypass the bot response engine entirely and are instantly dispatched to live human chat queues.
       
       Thread-Safe Logbook Storage: Features an isolated, shared-cache SQLite historical engine configuration allowing concurrent read-writes without application deadlocks.

## 🧰 Tech Stack

* **Frameworks:** FastAPI, Streamlit, Celery
* **AI & Vector Infrastructure:** ChromaDB (Vector DB), Groq Cloud API (Llama 3.3 70B)
* **Data & Transport Layers:** Redis (In-memory Message Broker), SQLite (Historical Storage), HTTPX
* **Validation & Testing:** Pydantic v2, Python Unittest Framework

## 🚀 Local Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/jerometp-dev/AITriageProject.git](https://github.com/jerometp-dev/AITriageProject.git)
   cd AITriageProject