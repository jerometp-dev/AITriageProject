from tasks import async_save_to_database, async_send_slack_alert
from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv
load_dotenv()

import sqlite3
import os
from typing import Literal
from pydantic import BaseModel, Field
from groq import AsyncGroq
import chromadb

# 💡 Points directly to your local workspace file
DB_PATH = "triage_history.db"

app = FastAPI(title="AI Support Triage Engine")

API_KEY_NAME = "X-Triage-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    expected_key = os.getenv("INTERNAL_API_TOKEN", "super_secret_handshake_key_123")
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: Access Denied.")
    return api_key

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            message_id TEXT PRIMARY KEY,
            channel TEXT,
            customer_id TEXT,
            text_content TEXT,
            intent TEXT,
            sentiment TEXT,
            priority_score INTEGER,
            summary TEXT,
            recommended_action TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# 💡 Uses standard local storage folder natively on Windows
chroma_client = chromadb.PersistentClient(path="./chroma_db_storage")
collection = chroma_client.get_or_create_collection(name="company_policy_kb")

def load_knowledge_base():
    global collection
    # 💡 UPDATED POLICY TEXT STRINGS
    documents = [
        "REFUND_POLICY: Customers can get a full refund if requested within 14 days of purchase. It takes 3 to 5 business days to clear back into their bank account.",
        "System account lockouts require an explicit secure verification handshake link dispatch.",
        "Company operating times span Monday through Saturday from 8:00 AM to 6:00 PM."
    ]
    ids = ["policy_refunds", "policy_security", "policy_hours"]
    collection.upsert(documents=documents, ids=ids)

load_knowledge_base()

class TriageAnalysis(BaseModel):
    intent: Literal["billing_issue", "technical_support", "account_access", "general_inquiry"]
    sentiment: Literal["positive", "neutral", "frustrated", "urgent_anger"]
    priority_score: int = Field(ge=1, le=5)
    summary: str
    recommended_action: Literal["respond_with_bot", "escalate_to_human"]

class InboundMessage(BaseModel):
    message_id: str
    channel: str
    customer_id: str
    text_content: str

@app.post("/webhook/triage")
async def triage_incoming_message(payload: InboundMessage, background_tasks: BackgroundTasks, api_key: str = Depends(verify_api_key)):
    try:
        search_results = collection.query(query_texts=[payload.text_content], n_results=2)
        matched_context = "\n".join(search_results['documents'][0]) if search_results and search_results['documents'] else "No context."

        analysis_response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Analyze this ticket using context: {matched_context}. Return strict JSON matching schema: {TriageAnalysis.model_json_schema()}"},
                {"role": "user", "content": payload.text_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        raw_json_str = analysis_response.choices[0].message.content
        analysis_result = TriageAnalysis.model_validate_json(raw_json_str)
        is_human = analysis_result.recommended_action == "escalate_to_human" or analysis_result.priority_score >= 4

        # 🤖 GENERATE DRAFT IF LOW PRIORITY / AUTOMATED
        bot_draft = ""
        if not is_human:
            draft_response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"You are a helpful support bot. Draft a short, direct message responding to the customer based strictly on this context:\n{matched_context}"},
                    {"role": "user", "content": payload.text_content}
                ],
                temperature=0.5
            )
            bot_draft = draft_response.choices[0].message.content

        if is_human:
            async_send_slack_alert.delay(payload.message_id, analysis_result.priority_score, analysis_result.intent, analysis_result.summary)

        async_save_to_database.delay(
            payload.message_id, payload.channel, payload.customer_id, payload.text_content,
            analysis_result.intent, analysis_result.sentiment, analysis_result.priority_score, 
            analysis_result.summary, analysis_result.recommended_action
        )

        # 💡 FIX: bot_draft_response is now explicitly included here!
        return {
            "status": "processed",
            "routing_path": "human_escalation" if is_human else "automated_bot",
            "triage_metrics": analysis_result.model_dump(),
            "bot_draft_response": bot_draft
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))