import streamlit as st
import yaml
import json
import os
import requests
import uuid
from datetime import datetime
from src.database import VeriUnlearnDB
from src.engine import SurgicalEngine
from src.cert_gen import CertificateFactory

# --- 1. INITIALIZATION ---
os.makedirs("proofs/certificates", exist_ok=True)
os.makedirs("models/shards", exist_ok=True)

OLLAMA_ENDPOINT = "http://localhost:11434/api"
MODEL_NAME = "phi3.5" 

db = VeriUnlearnDB()
engine = SurgicalEngine({"system": {"model_id": MODEL_NAME}})
cert_factory = CertificateFactory()

# --- 2. AUTHENTICATION & GLOBAL STATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_purge_bundle' not in st.session_state:
    st.session_state.last_purge_bundle = None

# Mock User Database (Sania as Admin, Rohan/Isha as Users)
USER_DB = {
    "sania": {"pwd": "123", "role": "admin"},
    "akash": {"pwd": "456", "role": "user"},
    "varun": {"pwd": "789", "role": "user"}
}

# --- 3. LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.set_page_config(page_title="Login | VeriUnlearn", layout="centered")
    st.title("🛡️ VeriUnlearn Secure Portal")
    
    with st.form("login_panel"):
        u_in = st.text_input("Username").lower()
        p_in = st.text_input("Password", type="password")
        if st.form_submit_button("Authenticate", use_container_width=True):
            if u_in in USER_DB and USER_DB[u_in]["pwd"] == p_in:
                st.session_state.authenticated = True
                st.session_state.username = u_in
                st.session_state.user_role = USER_DB[u_in]["role"]
                st.rerun()
            else:
                st.error("Access Denied: Invalid Credentials")
    st.stop()

# --- 4. APP LAYOUT & STYLING ---
st.set_page_config(page_title="VeriUnlearn Pro", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .main .block-container { max-width: 850px; padding-top: 2rem; }
    .stChatMessage { border-radius: 12px; margin-bottom: 15px; background-color: rgba(255,255,255,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🛡️ VeriUnlearn")
    st.write(f"Logged in: **{st.session_state.username.upper()}**")
    st.caption(f"Access Level: {st.session_state.user_role.upper()}")
    st.divider()
    
    nav_options = ["Neural Sandbox", "My Privacy Rights"]
    if st.session_state.user_role == "admin":
        nav_options.append("Compliance Audit")
        
    page = st.radio("Navigation", nav_options)
    
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.messages = []
        st.session_state.last_purge_bundle = None
        st.rerun()

# --- 6. GLOBAL CERTIFICATE LISTENER ---
# This ensures certificates appear regardless of what page the user is on
if st.session_state.last_purge_bundle:
    with st.container():
        st.success("✅ CRYPTOGRAPHIC PROOF OF ERASURE ISSUED")
        with st.expander("📄 VIEW VERIFICATION DETAILS", expanded=True):
            st.json(st.session_state.last_purge_bundle)
            
            q_id = st.session_state.last_purge_bundle['query_id']
            cert_path = f"proofs/certificates/cert_{q_id}.pdf"
            
            c1, c2 = st.columns(2)
            c1.download_button("📂 JSON Proof", json.dumps(st.session_state.last_purge_bundle, indent=4), f"proof_{q_id}.json", use_container_width=True)
            if os.path.exists(cert_path):
                with open(cert_path, "rb") as f:
                    c2.download_button("📕 PDF Certificate", f, f"cert_{q_id}.pdf", use_container_width=True)
            
            if st.button("Acknowledge & Dismiss", type="primary", use_container_width=True):
                st.session_state.last_purge_bundle = None
                st.rerun()
    st.divider()

# --- 7. PAGE LOGIC: NEURAL SANDBOX ---
if page == "Neural Sandbox":
    st.title("💬 Neural Sandbox")
    st.caption("ChatGPT-Style Interface | Identity-Locked Logging Active")
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask the model..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    res = requests.post(f"{OLLAMA_ENDPOINT}/generate", 
                                      json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=90)
                    ans = res.json().get('response')
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    
                    # LOGGING: Strictly associated with logged-in username
                    new_id = f"CHAT_{uuid.uuid4().hex[:6]}"
                    # Automatically summarize for privacy in the log
                    summary = prompt[:30] + "..." if len(prompt) > 30 else prompt
                    db.save_dynamic_query(new_id, st.session_state.username, summary)
                    st.toast(f"Footprint recorded for {st.session_state.username}")
                except:
                    st.error("Neural Engine Offline.")

# --- 8. PAGE LOGIC: MY PRIVACY RIGHTS (USER VIEW) ---
elif page == "My Privacy Rights":
    st.title("🔐 My Privacy Rights")
    st.markdown(f"User: **{st.session_state.username.capitalize()}**")
    st.info("You have the right to delete any personal data currently influencing this model.")
    
    records = db.fetch_active(st.session_state.username)
    if not records.empty:
        for idx, row in records.iterrows():
            with st.container():
                col1, col2 = st.columns([5, 1])
                col1.info(f"**ID:** {row['id']} | **Topic:** {row['content']}")
                if col2.button("ERASE", key=row['id']):
                    with st.status("Executing Surgical Unlearning...") as status:
                        purge_data = engine.surgical_purge(row['id'])
                        requests.post(f"{OLLAMA_ENDPOINT}/generate", json={"model": MODEL_NAME, "keep_alive": 0})
                        db.mark_purged(row['id'])
                        
                        st.session_state.last_purge_bundle = {
                            "subject": st.session_state.username,
                            "query_id": row['id'],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pre_hash": purge_data.get('pre_root'),
                            "post_hash": purge_data.get('post_root'),
                            "status": "VERIFIED_PURGED"
                        }
                        cert_factory.create_compliance_bundle(st.session_state.last_purge_bundle, f"proofs/certificates/cert_{row['id']}")
                        st.rerun()
    else:
        st.success("Your neural footprint is clean.")

# --- 9. PAGE LOGIC: COMPLIANCE AUDIT (ADMIN ONLY) ---
elif page == "Compliance Audit" and st.session_state.user_role == "admin":
    st.title("🔍 Master Compliance Audit")
    st.warning("Authorized Personnel Only: System-wide footprint monitoring.")
    
    search_q = st.text_input("Filter by Subject Name:", "rohan")
    records = db.fetch_active(search_q)
    if not records.empty:
        st.dataframe(records, use_container_width=True)
    else:
        st.info("No active footprints for this subject.")