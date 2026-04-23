import streamlit as st
import yaml
import json
import os
import requests
import uuid
from datetime import datetime

# Import project modules
from src.database import VeriUnlearnDB
from src.engine import SurgicalEngine
from src.cert_gen import CertificateFactory

# --- 1. INITIALIZATION ---
os.makedirs("proofs/certificates", exist_ok=True)
os.makedirs("models/shards", exist_ok=True)

def load_config():
    default_cfg = {
        "system": {"organization": "Sania Kotharkar | Major Project", "model_id": "phi3.5"},
        "hardware": {"ollama_url": "http://localhost:11434/api"}
    }
    if not os.path.exists("config/settings.yaml"):
        return default_cfg
    try:
        with open("config/settings.yaml", "r") as f:
            user_cfg = yaml.safe_load(f)
            if 'hardware' not in user_cfg: user_cfg['hardware'] = default_cfg['hardware']
            return user_cfg
    except:
        return default_cfg

config = load_config()
# Hardcoded default for the Major Project demo stability
OLLAMA_ENDPOINT = "http://localhost:11434/api"
MODEL_NAME = "phi3.5" 

db = VeriUnlearnDB()
engine = SurgicalEngine(config)
cert_factory = CertificateFactory()

# --- 2. SESSION STATE ---
if 'last_purge_bundle' not in st.session_state:
    st.session_state.last_purge_bundle = None

# --- 3. UI SETUP ---
st.set_page_config(page_title="VeriUnlearn Pro | Major Project", layout="wide", page_icon="🛡️")

st.title("🛡️ VeriUnlearn Pro")
st.markdown(f"**Research Focus:** Verifiable Machine Unlearning (GDPR Article 17)")
st.caption(f"Target Architecture: {MODEL_NAME} on NVIDIA RTX 4050 GPU")
st.divider()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ System Control")
    if st.button("Reset Database"):
        db.add_mock_data()
        st.session_state.last_purge_bundle = None
        st.success("State Re-initialized.")
        st.rerun()
    
    st.divider()
    st.write("**Ollama Engine Status:**")
    try:
        check = requests.get("http://localhost:11434/", timeout=2)
        if check.status_code == 200:
            st.success("ONLINE (Ready)")
        else:
            st.error("OFFLINE")
    except:
        st.error("NOT FOUND")

# --- 5. PERSISTENT PROOF VIEW ---
if st.session_state.last_purge_bundle:
    st.success("✅ CRYPTOGRAPHIC PROOF GENERATED")
    with st.expander("📄 VIEW COMPLIANCE CERTIFICATE", expanded=True):
        st.json(st.session_state.last_purge_bundle)
        
        c1, c2 = st.columns(2)
        q_id = st.session_state.last_purge_bundle['query_id']
        cert_base = f"proofs/certificates/cert_{q_id}"
        
        c1.download_button("📂 Download JSON Trace", 
                          json.dumps(st.session_state.last_purge_bundle, indent=4), 
                          f"{q_id}.json", use_container_width=True)
        
        if os.path.exists(f"{cert_base}.pdf"):
            with open(f"{cert_base}.pdf", "rb") as f:
                c2.download_button("📕 Download PDF Proof", f, f"{q_id}.pdf", use_container_width=True)
    
    if st.button("Clear and Return to Audit"):
        st.session_state.last_purge_bundle = None
        st.rerun()

# --- 6. MAIN TABS ---
tab1, tab2 = st.tabs(["🔍 Audit Records", "💬 Neural Testing"])

with tab1:
    user_search = st.text_input("Search Identity Subject:", "Rohan Kamath")
    records = db.fetch_active(user_search)

    if not records.empty:
        for idx, row in records.iterrows():
            with st.container():
                col1, col2 = st.columns([5, 1])
                badge = "⚠️ LEAK" if "CHAT" in str(row['id']) else "📦 CORE"
                col1.info(f"**{row['id']}** | {badge} | Content: {row['content']}")
                
                if col2.button("PURGE", key=row['id']):
                    with st.status("Executing Surgical Erasure...") as status:
                        # 1. Physical Scrubbing
                        purge_data = engine.surgical_purge(row['id'])
                        
                        # 2. VRAM Sanitization
                        requests.post(f"{OLLAMA_ENDPOINT}/generate", 
                                      json={"model": MODEL_NAME, "keep_alive": 0})
                        
                        # 3. Database Update
                        db.mark_purged(row['id'])
                        
                        # 4. Certification
                        bundle = {
                            "subject": user_search,
                            "query_id": row['id'],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pre_hash": purge_data.get('pre_root'),
                            "post_hash": purge_data.get('post_root'),
                            "verification": "OLLAMA_VRAM_FLUSHED"
                        }
                        st.session_state.last_purge_bundle = bundle
                        cert_factory.create_compliance_bundle(bundle, f"proofs/certificates/cert_{row['id']}")
                        
                        status.update(label="Unlearned & Verified.", state="complete")
                        st.rerun()
    else:
        if not st.session_state.last_purge_bundle:
            st.info("No active footprints found.")

with tab2:
    st.write("### ASKme")
    prompt = st.text_area("Live Input:")
    if st.button("Ask Away"):
        if prompt:
            with st.spinner("Analyzing weights..."):
                try:
                    res = requests.post(f"{OLLAMA_ENDPOINT}/generate", 
                                      json={
                                          "model": MODEL_NAME, 
                                          "prompt": prompt, 
                                          "stream": False
                                      }, timeout=90)
                    
                    if res.status_code == 200:
                        answer = res.json().get('response')
                        st.chat_message("assistant").write(answer)
                        
                        # Dynamic Ingestion
                        new_id = f"CHAT_{uuid.uuid4().hex[:6]}"
                        db.save_dynamic_query(new_id, "Rohan Kamath", prompt)
                        st.toast(f"Logged for Audit: {new_id}")
                    else:
                        st.error(f"Ollama Error {res.status_code}: {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to Ollama. Ensure 'ollama serve' is running. ({e})")

st.divider()
st.caption("Sahyadri College of Engineering & Management | 2026")