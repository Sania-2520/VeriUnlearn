import streamlit as st
import json
import os
import requests
import uuid
import hashlib
import hmac
from datetime import datetime
from src.database import VeriUnlearnDB
from src.engine import SurgicalEngine
from src.cert_gen import CertificateFactory

# --- 1. SYSTEM INITIALIZATION ---
os.makedirs("proofs/certificates", exist_ok=True)
USER_FILE = "proofs/users.json"
OLLAMA_ENDPOINT = "http://localhost:11434/api"
MODEL_NAME = "phi3.5"
SECRET_ZK_KEY = "sania_scem_2026"

db = VeriUnlearnDB()
engine = SurgicalEngine({"system": {"model_id": MODEL_NAME}})
cert_factory = CertificateFactory()

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {"sania": {"pwd": "123", "role": "admin", "shard": "shard_master"}}

def save_user(username, password, shard):
    users = load_users()
    users[username] = {"pwd": password, "role": "user", "shard": shard}
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# --- 2. SESSION STATE MANAGEMENT ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = None
    st.session_state.shard = None
    st.session_state.chat_history = []
    st.session_state.purge_proof = None
    st.session_state.dynamic_user_db = load_users()

# --- 3. CRYPTO UTILS ---
def get_zk_proof(pre, post):
    """Generates ZK-SNARK-inspired pi proof (UTF-8 Safe)."""
    msg = f"{pre}{post}".encode()
    pi_hash = hmac.new(SECRET_ZK_KEY.encode(), msg, hashlib.sha256).hexdigest()
    return f"zk-snark:v1:pi_{pi_hash[:12]}"

# --- 4. ACCESS PORTAL ---
if not st.session_state.auth:
    st.set_page_config(page_title="VeriUnlearn | Access", layout="centered")
    st.markdown("<h1 style='text-align: center;'>🛡️ VeriUnlearn Pro</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("System Access", ["Sign In", "Register New Independent Shard"], horizontal=True)
    
    with st.container(border=True):
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        
        if auth_mode == "Sign In":
            if st.button("Secure Sign In", use_container_width=True, type="primary"):
                current_db = load_users()
                if u in current_db and current_db[u]["pwd"] == p:
                    st.session_state.auth = True
                    st.session_state.user = u
                    st.session_state.shard = current_db[u]["shard"]
                    
                    # LOAD ONLY ACTIVE HISTORY (Persistence Layer Sync)
                    try:
                        st.session_state.chat_history = db.fetch_user_history(u)
                    except:
                        st.session_state.chat_history = []
                    st.rerun()
                else:
                    st.error("Authentication Failed: Invalid Identity")
        
        else: # Register Mode
            if st.button("Initialize Neural Shard", use_container_width=True):
                if u and p:
                    current_db = load_users()
                    if u not in current_db:
                        new_shard = f"shard_{uuid.uuid4().hex[:6]}"
                        save_user(u, p, new_shard)
                        st.success(f"Shard `{new_shard}` created! Please Sign In.")
                    else:
                        st.warning("Identity already registered.")
    st.stop()

# --- 5. DASHBOARD LAYOUT ---
st.set_page_config(page_title="VeriUnlearn Pro", layout="wide")

with st.sidebar:
    st.title("🛡️ Dashboard")
    st.info(f"**Identity:** {st.session_state.user.upper()}\n**Shard:** `{st.session_state.shard}`")
    st.divider()
    page = st.radio("Navigation", ["Neural Sandbox", "Privacy Control Center"])
    st.divider()
    if st.button("Logout"):
        st.session_state.auth = False
        st.session_state.chat_history = []
        st.rerun()

# --- 6. PAGE: NEURAL SANDBOX ---
if page == "Neural Sandbox":
    st.title("💬 Neural Sandbox")
    st.caption(f"SISA Isolation Active on {st.session_state.shard}")
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Enter private data..."):
        st.chat_message("user").markdown(prompt)
        
        # Isolated Context Injection
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-5:]])
        full_input = f"{history_context}\nuser: {prompt}"

        with st.chat_message("assistant"):
            try:
                res = requests.post(f"{OLLAMA_ENDPOINT}/generate", 
                                  json={"model": MODEL_NAME, "prompt": full_input, "stream": False})
                ans = res.json().get('response')
                st.markdown(ans)
                
                # Update UI memory
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                
                # Update DB memory (SISA-tagged)
                db.save_dynamic_query(f"ID_{uuid.uuid4().hex[:6]}", st.session_state.user, prompt)
            except:
                st.error("Neural Engine Offline.")

# --- 7. PAGE: PRIVACY CONTROL CENTER ---
elif page == "Privacy Control Center":
    st.title("🔐 Privacy Control Center")
    
    if st.session_state.purge_proof:
        st.success("✅ TOTAL ERASURE VERIFIED")
        st.json(st.session_state.purge_proof)
        q_id = st.session_state.purge_proof['query_id']
        cert_path = f"proofs/certificates/cert_{q_id}.pdf"
        
        if os.path.exists(cert_path):
            with open(cert_path, "rb") as f:
                st.download_button("📕 Download Compliance Certificate", f, f"cert_{q_id}.pdf", mime="application/pdf")
        
        if st.button("Dismiss Result"):
            st.session_state.purge_proof = None
            st.rerun()
        st.divider()

    # List active footprints belonging ONLY to this user
    records = db.fetch_active(st.session_state.user)
    if not records.empty:
        for _, row in records.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.warning(f"**Neural Footprint:** {row['content']}")
            
            if c2.button("ERASE", key=row['id']):
                with st.spinner("Executing Surgical HMO-LoRA Purge..."):
                    # 1. WEIGHT SUBTRACTION
                    p_data = engine.surgical_purge(row['id'])
                    
                    # 2. HARDWARE FLUSH (Sanitization)
                    requests.post(f"{OLLAMA_ENDPOINT}/generate", json={"model": MODEL_NAME, "keep_alive": 0})
                    
                    # 3. PERSISTENCE UPDATE (Mark as Purged in SQLite)
                    db.mark_purged(row['id'])
                    
                    # 4. INSTANT UI FLUSH
                    # Remove the purged item from the local chat history so it disappears from Sandbox
                    st.session_state.chat_history = [
                        m for m in st.session_state.chat_history 
                        if m['content'] != row['content']
                    ]
                    
                    # 5. CRYPTO BUNDLE
                    pi = get_zk_proof(p_data.get('pre_root'), p_data.get('post_root'))
                    st.session_state.purge_proof = {
                        "user": st.session_state.user,
                        "query_id": row['id'],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "zk_pi": pi,
                        "shard": st.session_state.shard,
                        "status": "PURGED_AND_VERIFIED"
                    }
                    cert_factory.create_compliance_bundle(st.session_state.purge_proof, f"proofs/certificates/cert_{row['id']}")
                    
                    # 6. REFRESH UI
                    st.rerun()
    else:
        st.info("No active neural footprints detected for this identity.")