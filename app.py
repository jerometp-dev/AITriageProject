import sqlite3
import pandas as pd
import streamlit as st
import requests
import uuid
import os
from dotenv import load_dotenv

# Load environment variables cleanly
load_dotenv()

# 💡 LOCAL ROUTING: Fallback points directly to localhost since Docker networks are gone
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page configuration for a professional look
st.set_page_config(page_title="AI Triage Control Center", page_icon="🤖", layout="wide")

st.title("🤖 Omnichannel AI Support Triage Engine")
st.markdown("---")

# Setup columns for side-by-side execution layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📬 Simulate Inbound Customer Message")
    
    channel = st.selectbox("Inbound Channel", ["email", "whatsapp", "webchat"])
    customer_id = st.text_input("Customer ID", value="cust_9921")
    
    preset = st.selectbox("Quick Presets (Test Cases)", [
        "Custom Message",
        "🚨 Angry: Double Charge / Refund Demands",
        "🌤️ Calm: Question about operating hours",
        "📉 Churn Threat: Technical Bug / Cancellation"
    ])
    
    if preset == "🚨 Angry: Double Charge / Refund Demands":
        default_text = "Your system double charged my visa card this morning! I need my money back immediately or I am canceling my subscription and disputing this with my bank!!!"
    elif preset == "🌤️ Calm: Question about operating hours":
        default_text = "Hey there, quick question: Are you guys open tomorrow or on Sundays to handle shipment collections? Thanks!"
    elif preset == "📉 Churn Threat: Technical Bug / Cancellation":
        default_text = "I am locked out of my billing portal entirely and your dashboard keeps freezing. If this isn't resolved by tonight, close my account."
    else:
        default_text = ""

    text_content = st.text_area("Customer Message Body", value=default_text, height=150)
    trigger_simulation = st.button("Simulate Incoming Webhook", type="primary")

# Allocate Right column (col2) for outputs
with col2:
    st.subheader("⚙️ AI Triage Gateway Outputs")
    
    if trigger_simulation:
        generated_id = f"msg_{uuid.uuid4().hex[:8]}"
        payload = {
            "message_id": generated_id,
            "channel": channel,
            "customer_id": customer_id,
            "text_content": text_content
        }
        
        with st.spinner("Processing omnichannel triage pipelines..."):
            try:
                headers = {
                    "X-Triage-Token": os.getenv("INTERNAL_API_TOKEN", "super_secret_handshake_key_123"),
                    "Content-Type": "application/json"
                }
                response = requests.post(f"{BACKEND_URL}/webhook/triage", json=payload, headers=headers, timeout=60)
                
                if response.status_code == 200:
                    res_json = response.json()
                    metrics = res_json.get("triage_metrics", {})
                    routing_path = res_json.get("routing_path", "")
                    
                    st.success("Message Processed Successfully!")
                    
                    p_score = metrics.get("priority_score", 1)
                    st.metric(label="Priority Urgency Score", value=f"{p_score} / 5")
                    st.progress(p_score * 20)
                    
                    intent_display = str(metrics.get("intent", "general_inquiry")).replace('_', ' ').title()
                    st.info(f"**Identified Intent:** {intent_display}")
                    
                    sentiment_color = {
                        "positive": "🟢 Positive",
                        "neutral": "🔵 Neutral",
                        "frustrated": "🟠 Frustrated",
                        "urgent_anger": "🔴 Urgent Anger"
                    }
                    raw_sent = metrics.get("sentiment", "neutral")
                    st.write(f"**Customer Sentiment:** {sentiment_color.get(raw_sent, raw_sent)}")
                    
                    st.subheader("AI Executive Summary")
                    st.info(metrics.get("summary", "No summary provided."))
                    
                    if metrics.get("recommended_action") == "escalate_to_human" or routing_path == "human_escalation":
                        st.error("🚨 ACTION: Escalated to Human Queue & Dispatched Real Slack Alert!")
                    else:
                        st.success("🤖 ACTION: Safe for Automated RAG Bot Response Path.")
                        bot_reply = res_json.get("bot_draft_response")
                        if bot_reply:
                            st.subheader("🤖 Auto-Bot Draft Response")
                            st.warning(f"\"{bot_reply}\"")
                else:
                    st.error(f"🚨 Backend Error ({response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"Could not connect to FastAPI server at {BACKEND_URL}. Error: {e}")
    else:
        st.write("Awaiting inbound webhook event... Use left panel to trigger.")

st.markdown("---")
st.subheader("📊 Historical Triage Analytics Logbook")

# 💡 LOCAL PATH HANDLING: Connect securely to the active folder space on Windows
def fetch_historical_logs():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "triage_history.db")
    
    if not os.path.exists(db_path):
        return pd.DataFrame()
        
    db_uri = f"file:{db_path}?mode=ro&cache=shared"
    conn = None
    try:
        conn = sqlite3.connect(db_uri, uri=True, timeout=0.5)
        df = pd.read_sql_query("SELECT * FROM tickets", conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# Quick manual refresh feature for the datatables logs
if st.button("🔄 Refresh Logbook"):
    st.rerun()

df = fetch_historical_logs()

if not df.empty:
    try:
        st.dataframe(df[["message_id", "customer_id", "channel", "intent", "sentiment", "priority_score", "summary"]], use_container_width=True)
        st.markdown("### 📈 Ticket Urgency Distribution Chart")
        priority_counts = df["priority_score"].value_counts().sort_index()
        st.bar_chart(priority_counts)
    except Exception:
        st.info("Logbook synchronizing live assets...")
else:
    st.info("The database tracking history is empty. Simulate a webhook message above to see data logs compile live!")