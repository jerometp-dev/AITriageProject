# AI Triage Engine

An AI-powered support ticket triage system. It reads incoming customer support tickets, uses an LLM to figure out what the customer wants and how urgent it is, and then either sends an automatic reply or escalates the ticket to a human via Slack — depending on how serious it is.

## How it works

```text
[Ticket comes in via Webhook / Streamlit UI]
               │
               ▼
   [FastAPI receives the request]
               │
               ▼
┌────────────────────────────────────────┐
│  Look up relevant company policy info  │ ◄─── [ChromaDB: stored policies]
└────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│   LLM analyzes the ticket (Groq)       │ ──► Output: intent, sentiment, priority
└────────────────────────────────────────┘
               │
               ▼
   Is priority 4 or higher (needs a human)?
               │
               ├──► YES ──► [Celery + Redis] ──► 🚨 Alert sent to Slack
               │
               └──► NO  ──► [LLM drafts a reply using the policy context] ──► 🤖 Shown in the UI
               │
               ▼
┌────────────────────────────────────────┐
│   Every ticket is logged in SQLite     │ ──► Keeps a history, avoids duplicate entries
└────────────────────────────────────────┘
```

## Key design decisions

* **Background processing for Slack alerts:** Sending a Slack message can be slow, so that work is handed off to a Celery worker (using Redis as the queue) instead of making the API wait on it. This keeps ticket submission fast even when an alert is being sent.
* **Grounded responses, not guesses:** Before the LLM drafts a reply, it pulls real company policy text from a ChromaDB vector store and includes it in the prompt. This keeps auto-replies based on actual policy instead of the model making things up.
* **Hard rule for urgent tickets:** Any ticket scored 4 or higher in priority skips the auto-reply step entirely and goes straight to a human via Slack. This is a fixed rule, not something the LLM can override.
* **Concurrent-safe logging:** Ticket history is stored in SQLite configured for shared-cache mode, so multiple processes can read and write without locking each other out.

## Example: how a ticket gets routed

**Low urgency** — *"How do I change my profile theme?"*
This is a routine question. The system looks up relevant policy info in ChromaDB, has the LLM draft a reply using that context, and shows the auto-drafted response right in the UI. No human needed.

**High urgency** — *"I cannot access my account."*
This looks like an account security issue, so it gets a priority score of 4 or higher. The system skips the auto-reply step completely and sends the ticket straight to a human through Slack, via the Celery/Redis background worker.

## Tech stack

* **Backend / UI:** FastAPI, Streamlit, Celery
* **AI:** ChromaDB (vector search), Groq API running Llama 3.3 70B
* **Infrastructure:** Redis (message broker), SQLite (ticket history), HTTPX
* **Testing:** Pydantic v2, Python's built-in unittest

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/jerometp-dev/AITriageProject.git
   cd AITriageProject
   ```

2. **Add environment variables**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   SLACK_WEBHOOK_URL=your_slack_webhook_url
   INTERNAL_API_TOKEN=your_secure_local_token
   ```

3. **Run the services** (each in its own terminal)
   ```bash
   # FastAPI backend
   uvicorn triage_engine:app --reload

   # Celery worker (handles Slack alerts)
   celery -A tasks worker --loglevel=info -P threads

   # Streamlit dashboard
   streamlit run app.py
   ```

4. **Run the tests**
   ```bash
   python test_triage.py
   ```

## Why I built this

Before moving into tech, I worked as a contact center associate, so I saw firsthand how much time gets spent manually reading, categorizing, and routing support tickets — and how often urgent issues sit in the same queue as routine ones. I built this project to explore whether an LLM could reliably handle that triage step: understanding what a customer actually needs and deciding which tickets truly need a human versus which ones can be handled automatically. The hardest part was building the escalation logic so it didn't rely purely on the LLM's judgment — sensitive or high-priority tickets needed a hard rule that bypasses the AI response entirely, since a wrong auto-reply on a serious issue would be worse than no reply at all.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
