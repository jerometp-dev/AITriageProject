# ⚙️ 1. ALWAYS LOAD ENVIRONMENT VARIABLES FIRST!
from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv
load_dotenv()
import sqlite3
import os
import json
from typing import Literal
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from groq import Groq 

app = FastAPI(title="AI Support Triage Engine")

API_KEY_NAME = "X-Triage-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    # This is the secret value your backend expects. We pull it from .env or default to a static string
    expected_key = os.getenv("INTERNAL_API_TOKEN", "super_secret_handshake_key_123")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: Access to Triage Core Denied.")
    return api_key

def init_db():
    conn = sqlite3.connect("triage_history.db")
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

# 🔑 2. Explicitly pull the key from your loaded .env file
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class TriageAnalysis(BaseModel):
    intent: Literal["billing_issue", "technical_support", "account_access", "general_inquiry"] = Field(
        description="The primary category of the customer's request. Must be exactly one of the allowed options."
    )
    sentiment: Literal["positive", "neutral", "frustrated", "urgent_anger"] = Field(
        description="The emotional state of the customer. Must be lowercase."
    )
    priority_score: int = Field(
        description="An integer from 1 (low urgency) to 5 (extreme crisis).", ge=1, le=5
    )
    summary: str = Field(description="A 1-sentence summary of the core issue.")
    recommended_action: Literal["respond_with_bot", "escalate_to_human"] = Field(
        description="Decision path based on urgency."
    )

class InboundMessage(BaseModel):
    message_id: str
    channel: str
    customer_id: str
    text_content: str

# 🛠️ MOVED OUT OF METRIC LOOP: Dedicated DB logger execution function
def save_to_db(msg_id: str, chan: str, cust_id: str, text: str, intent: str, sent: str, score: int, summ: str, action: str):
    try:
        conn = sqlite3.connect("triage_history.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO tickets
            (message_id, channel, customer_id, text_content, intent, sentiment, priority_score, summary, recommended_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, chan, cust_id, text, intent, sent, score, summ, action))
        conn.commit()
        conn.close()
        print(f"💾 Ticket {msg_id} successfully saved to local log database!")
    except Exception as db_err:
        print(f"❌ Database error: {db_err}")

async def trigger_real_slack_alert(message_id: str, priority_score: int, intent: str, summary: str):
    import httpx
    
    print(f"📡 [SLACK DISPATCHER] Alerting triage ops for ticket {message_id} [Priority {priority_score}]")
    
    url = os.getenv("SLACK_WEBHOOK_URL") 
    
    payload = {
        "text": f"🚨 *CRITICAL TICKET ESCALATION* 🚨\n\n*ID:* {message_id}\n*Urgency:* {priority_score}/5\n*Category:* {intent.upper()}\n*Summary:* {summary}"
    }
    
    try:
        # Use the non-blocking async client to dispatch the payload
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=5.0)
            print(f"📢 Async Slack webhook status code: {res.status_code}")
    except Exception as e:
        print(f"❌ Failed to dispatch async Slack webhook notification: {e}")

def route_to_human_queue(ticket_id: str, analysis: TriageAnalysis):
    print(f"📥 [HUMAN PIPELINE] Logging ticket {ticket_id} into ZenDesk enterprise CRM matrix.")

def route_to_automated_bot(ticket_id: str, content: str, intent: str):
    print(f"🤖 [AUTO-BOT WORKFLOW] Intercepted message {ticket_id} for resolution.")

@app.post("/webhook/triage")
async def triage_incoming_message(
    payload: InboundMessage, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)  # 🔒 THIS LOCKS THE ENTIRE ENDPOINT!
):
    try:
        bot_draft = "Thank you for reaching out! Our business hours are Monday through Saturday 9:00 AM to 6:00 PM. We are closed on Sundays."

        # --- PHASE 1: HIGH-SPEED STRUCTURED PARSING VIA GROQ ---
        analysis_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": f"Analyze the following incoming customer ticket and extract clean triage metrics matching this JSON schema target layout exactly: {TriageAnalysis.model_json_schema()}. Do not use values outside the specified Literal options."
                },
                {"role": "user", "content": payload.text_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        raw_json_str = analysis_response.choices[0].message.content
        analysis_result = TriageAnalysis.model_validate_json(raw_json_str)

        # --- PHASE 2: EXPLICIT SLACK ESCALATION DETERMINATION ---
        is_human = analysis_result.recommended_action == "escalate_to_human" or analysis_result.priority_score >= 4

        if is_human:
            print(f"🔥 Critical Ticket Detected! Dispatching Slack Webhook to channel...")
            background_tasks.add_task(
                trigger_real_slack_alert,
                message_id=payload.message_id,
                priority_score=analysis_result.priority_score,
                intent=analysis_result.intent,
                summary=analysis_result.summary
            )

        # --- PHASE 3: BOT RESPONSE CUSTOMIZATION ---
        if analysis_result.intent == "billing_issue":
            bot_draft = "Refunds are processed automatically if requested within 14 days of purchase. It takes 3-5 business days to clear."
        elif analysis_result.intent in ["technical_support", "account_access"]:
            bot_draft = "Our engineering team has been notified of this system interference. We are investigating account access options."

        # --- PHASE 4: HISTORICAL LOGGING & PIPELINE EXECUTION ---
        background_tasks.add_task(
            save_to_db, 
            payload.message_id, payload.channel, payload.customer_id, payload.text_content,
            analysis_result.intent, analysis_result.sentiment, analysis_result.priority_score, 
            analysis_result.summary, analysis_result.recommended_action
        )

        if is_human:
            background_tasks.add_task(route_to_human_queue, payload.message_id, analysis_result)
            final_bot_reply = None 
        else:
            background_tasks.add_task(route_to_automated_bot, payload.message_id, payload.text_content, analysis_result.intent)
            final_bot_reply = bot_draft

        return {
            "status": "processed",
            "routing_path": "human_escalation" if is_human else "automated_bot",
            "triage_metrics": analysis_result.model_dump(),
            "bot_draft_response": final_bot_reply
        }

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Groq Core Execution Failure: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)