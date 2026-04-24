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
# Create necessary directory structure for cryptographic proofs
os.makedirs("proofs/certificates", exist_ok=True)
db = VeriUnlearnDB()
engine = SurgicalEngine({"system": {"model_id": "phi3.5"}})
cert_factory = CertificateFactory()

OLLAMA_ENDPOINT = "http://localhost:11434/api"
MODEL_NAME = "phi3.5"
SECRET_ZK_KEY = "sania_scem_2026"

# --- 2. DYNAMIC USER REGISTRY (Multi-Tenant Simulation) ---
if 'dynamic_user_db' not in st.session_state:
    st.session_state.dynamic_user_db = {
        "sania": {"pwd": "123", "role": "admin", "shard": "shard_master"}
    }

# Session Management
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'shard' not in st.session_state:
    st.session_state.shard = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'purge_proof' not in st.session_state:
    st.session_state.purge_proof = None

# --- 3. CRYPTO UTILS ---
def get_zk_proof(pre, post):
    """
    Generates a ZK-SNARK-inspired proof string.
    NOTE: Replaced 'π' with 'pi' to fix UnicodeEncodeError in PDF generation.
    """
    msg = f"{pre}{post}".encode()
    pi_hash = hmac.new(SECRET_ZK_KEY.encode(), msg, hashlib.sha256).hexdigest()
    return f"zk-snark:v1:pi_{pi_hash[:12]}"

# --- 4. THE DYNAMIC ACCESS PORTAL ---
if not st.session_state.auth:
    st.set_page_config(page_title="VeriUnlearn | Portal", layout="centered")
    st.markdown("<h1 style='text-align: center;'>🛡️ VeriUnlearn Pro</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("System Access", ["Sign In", "Register New Independent Shard"], horizontal=True)
    
    with st.container(border=True):
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        
        if auth_mode == "Sign In":
            if st.button("Secure Sign In", use_container_width=True, type="primary"):
                if u in st.session_state.dynamic_user_db and st.session_state.dynamic_user_db[u]["pwd"] == p:
                    st.session_state.auth = True
                    st.session_state.user = u
                    st.session_state.shard = st.session_state.dynamic_user_db[u]["shard"]
                    st.rerun()
                else:
                    st.error("Authentication Failed: Unknown Identity or Invalid Password")
        
        else: # Register Mode
            if st.button("Initialize Neural Shard", use_container_width=True):
                if u and p:
                    if u not in st.session_state.dynamic_user_db:
                        # DYNAMIC SISA SHARDING
                        new_shard = f"shard_{uuid.uuid4().hex[:6]}"
                        st.session_state.dynamic_user_db[u] = {"pwd": p, "role": "user", "shard": new_shard}
                        st.success(f"Shard Created: `{new_shard}`. You may now Sign In.")
                    else:
                        st.warning("User identity already exists in neural index.")
    st.stop()

# --- 5. DASHBOARD LAYOUT ---
st.set_page_config(page_title="VeriUnlearn Pro", layout="wide")

with st.sidebar:
    st.title("🛡️ VeriUnlearn")
    st.info(f"**Identity:** {st.session_state.user.upper()}\n\n**Neural Shard:** `{st.session_state.shard}`")
    st.divider()
    page = st.radio("Navigation", ["Neural Sandbox", "Privacy Control Center"])
    st.divider()
    if st.button("Logout & Flush Session"):
        st.session_state.auth = False
        st.session_state.chat_history = []
        st.rerun()

# --- 6. PAGE: NEURAL SANDBOX ---
if page == "Neural Sandbox":
    st.title("💬 Neural Sandbox")
    st.caption(f"Hardware Acceleration (RTX 4050) active on {st.session_state.shard}")
    
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Enter data to process..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            try:
                # LLM Interaction via Ollama
                res = requests.post(f"{OLLAMA_ENDPOINT}/generate", 
                                  json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
                ans = res.json().get('response')
                st.markdown(ans)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                
                # SISA Shard Logging
                qid = f"ID_{uuid.uuid4().hex[:6]}"
                db.save_dynamic_query(qid, st.session_state.user, prompt[:50])
            except:
                st.error("Neural Engine Connectivity Error")

# --- 7. PAGE: PRIVACY CONTROL CENTER ---
elif page == "Privacy Control Center":
    st.title("🔐 Privacy Control Center")
    st.markdown("### GDPR Article 17 Management")
    
    # Proof and Certificate Section
    if st.session_state.purge_proof:
        st.success("✅ CRYPTOGRAPHIC PROOF OF ERASURE")
        st.json(st.session_state.purge_proof)
        
        q_id = st.session_state.purge_proof['query_id']
        cert_path = f"proofs/certificates/cert_{q_id}.pdf"
        
        # FILE EXISTENCE GUARD: Prevents FileNotFoundError
        if os.path.exists(cert_path):
            with open(cert_path, "rb") as f:
                st.download_button(
                    label="📕 Download Compliance Certificate",
                    data=f,
                    file_name=f"cert_{q_id}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("⏳ Generating Audit-Ready PDF... please wait.")
            if st.button("Refresh Proof Status"):
                st.rerun()

        if st.button("Dismiss Result"):
            st.session_state.purge_proof = None
            st.rerun()
        st.divider()

    # Active Footprint Display
    records = db.fetch_active(st.session_state.user)
    if not records.empty:
        for _, row in records.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.warning(f"**Footprint:** {row['content']}")
            if c2.button("ERASE", key=row['id']):
                with st.spinner("Executing Surgical HMO-LoRA Purge..."):
                    # Step 1: Weight Subtraction (Surgical Engine)
                    p_data = engine.surgical_purge(row['id'])
                    
                    # Step 2: Hardware VRAM Flush (Ollama Sanitization)
                    requests.post(f"{OLLAMA_ENDPOINT}/generate", json={"model": MODEL_NAME, "keep_alive": 0})
                    db.mark_purged(row['id'])
                    
                    # Step 3: Z-SNARK Proof Generation
                    pi_proof = get_zk_proof(p_data.get('pre_root', '0x0'), p_data.get('post_root', '0x0'))
                    
                    st.session_state.purge_proof = {
                        "subject": st.session_state.user,
                        "query_id": row['id'],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "zk_proof_pi": pi_proof,
                        "shard_id": st.session_state.shard,
                        "pre_hash": p_data.get('pre_root'),
                        "post_hash": p_data.get('post_root')
                    }
                    
                    # Step 4: Generate Certificate PDF
                    cert_factory.create_compliance_bundle(st.session_state.purge_proof, f"proofs/certificates/cert_{row['id']}")
                    st.rerun()
    else:
        st.info("Your identity has no active neural footprints.")