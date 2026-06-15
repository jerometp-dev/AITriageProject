import sqlite3
import os
import json
from typing import Literal
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
# 🔄 Swapped Google GenAI out for the official Groq client
from groq import Groq 

app = FastAPI(title="AI Support Triage Engine")

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

# 🔑 Reads GROQ_API_KEY from your environment variables
# Get a free key instantly from: https://console.groq.com/
client = Groq()

class TriageAnalysis(BaseModel):
    intent: Literal["billing_issue", "technical_support", "account_access", "general_inquiry"] = Field(
        description="The primary category of the customer's request."
    )
    sentiment: Literal["positive", "neutral", "frustrated", "urgent_anger"] = Field(
        description="The emotional state of the customer."
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

def trigger_real_slack_alert(message_id: str, priority_score: int, intent: str, summary: str):
    print(f"📡 [SLACK DISPATCHER] Alerting triage ops for ticket {message_id} [Priority {priority_score}]")
    url = "https://hooks.slack.com/services/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"
    payload = {
        "text": f"🚨 *CRITICAL TICKET ESCALATION* 🚨\n\n*ID:* {message_id}\n*Urgency:* {priority_score}/5\n*Category:* {intent.upper()}\n*Summary:* {summary}"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"📢 Slack webhook status code: {res.status_code}")
    except Exception as e:
        print(f"❌ Failed to dispatch Slack webhook notification: {e}")

def route_to_human_queue(ticket_id: str, analysis: TriageAnalysis):
    print(f"📥 [HUMAN PIPELINE] Logging ticket {ticket_id} into CRM matrix.")

def route_to_automated_bot(ticket_id: str, content: str, intent: str):
    print(f"🤖 [AUTO-BOT WORKFLOW] Intercepted message {ticket_id} for automated response.")

@app.post("/webhook/triage")
async def triage_incoming_message(payload: InboundMessage, background_tasks: BackgroundTasks):
    try:
        bot_draft = "Thank you for reaching out! Our business hours are Monday through Saturday 9:00 AM to 6:00 PM. We are closed on Sundays."

        # --- PHASE 1: DYNAMIC AGENT TOOL INVOCATION & ROUTING ---
        # Defining the schema pattern for tool arguments mapping
        tools = [{
            "type": "function",
            "function": {
                "name": "trigger_real_slack_alert",
                "description": "Execute this tool if the ticket text presents urgent context, system bugs, billing complaints, or severe anger.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID string for the message payload."
                        },
                        "priority_score": {
                            "type": "integer", 
                            "description": "CRITICAL: Provide a raw integer number strictly from 1 (low urgency) to 5 (extreme crisis). Do NOT wrap this in quotation marks."
                        },
                        "intent": {
                            "type": "string",
                            "description": "The determined intent category matching the structural metrics."
                        },
                        "summary": {
                            "type": "string",
                            "description": "A short 1-sentence summary of the core crisis issue."
                        }
                    },
                    "required": ["message_id", "priority_score", "intent", "summary"]
                }
            }
        }]

        tool_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a fast tool-routing agent. Call the trigger_real_slack_alert function only if urgent criteria match."},
                {"role": "user", "content": payload.text_content}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )

        response_message = tool_response.choices[0].message
        if response_message.tool_calls:
            print("🤖 Llama Agent requested a tool pipeline dispatch!")
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "trigger_real_slack_alert":
                    args = json.loads(tool_call.function.arguments)
                    background_tasks.add_task(
                        trigger_real_slack_alert,
                        message_id=payload.message_id,
                        priority_score=int(args.get("priority_score", 5)),
                        intent=str(args.get("intent", "billing_issue")),
                        summary=str(args.get("summary", "Urgent escalation triggered by AI pipeline."))
                    )

        # --- PHASE 2: HIGH-SPEED STRUCTURED DATA PARSING ---
        # Using Groq's native JSON output enforcement structure matching your Pydantic schema
        analysis_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Analyze the following incoming customer ticket and extract clean triage metrics matching this JSON schema target layout: {TriageAnalysis.model_json_schema()}"},
                {"role": "user", "content": payload.text_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        # Validate the raw JSON object string back into our concrete Pydantic object
        raw_json_str = analysis_response.choices[0].message.content
        analysis_result = TriageAnalysis.model_validate_json(raw_json_str)

        # --- PHASE 3: BOT RESPONSE CUSTOMIZATION ---
        if analysis_result.intent == "billing_issue":
            bot_draft = "Refunds are processed automatically if requested within 14 days of purchase. It takes 3-5 business days to clear."
        elif analysis_result.intent in ["technical_support", "account_access"]:
            bot_draft = "Our engineering team has been notified of this system interference. We are investigating account access options."

        # --- PHASE 4: HISTORICAL LOGGING & PIPELINE EXECUTION ---
        def save_to_db(msg_id, chan, cust_id, text, intent, sent, score, summ, action):
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
                print(f"💾 Ticket {msg_id} logged via Groq Pipeline execution.")
            except Exception as db_err:
                print(f"❌ Database error: {db_err}")

        background_tasks.add_task(
            save_to_db, 
            payload.message_id, payload.channel, payload.customer_id, payload.text_content,
            analysis_result.intent, analysis_result.sentiment, analysis_result.priority_score, 
            analysis_result.summary, analysis_result.recommended_action
        )

        is_human = analysis_result.recommended_action == "escalate_to_human" or analysis_result.priority_score >= 4

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
        raise HTTPException(status_code=500, detail=f"Groq Core Execution Failure: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)