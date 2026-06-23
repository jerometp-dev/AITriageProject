from dotenv import load_dotenv
load_dotenv()
import sqlite3
import httpx
from celery import Celery

# 💡 Local path to sqlite database file
DB_PATH = "triage_history.db"

# 💡 Routes messages directly via localhost network loop
celery_app = Celery(
    "triage_tasks",
    broker="redis://localhost:6379/0",   
    backend="redis://localhost:6379/0"  
)

@celery_app.task
def async_save_to_database(msg_id, chan, cust_id, text, intent, sent, score, summ, action):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO tickets
        (message_id, channel, customer_id, text_content, intent, sentiment, priority_score, summary, recommended_action)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (msg_id, chan, cust_id, text, intent, sent, score, summ, action))
    conn.commit()
    conn.close()

@celery_app.task
def async_send_slack_alert(message_id, priority_score, intent, summary):
    import os
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_url:
        # 🌟 Format category string neatly into UPPERCASE
        category_formatted = str(intent).upper()
        
        # 📋 Build the full detailed alert format you had before
        slack_text = (
            f"🚨 *CRITICAL TICKET ESCALATION* 🚨\n\n"
            f"*ID:* {message_id}\n"
            f"*Urgency:* {priority_score}/5\n"
            f"*Category:* {category_formatted}\n"
            f"*Summary:* {summary}"
        )
        
        payload = {"text": slack_text}
        httpx.post(slack_url, json=payload)