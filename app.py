import streamlit as st
import time
import hashlib
import json
from datetime import datetime
import uuid

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="VeriUnlearn",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (Matching the prototype aesthetic) ---
st.markdown("""
<style>
    .reportview-container {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stTextInput > div > div > input {
        background-color: #1E2127;
        color: #FAFAFA;
        border: 1px solid #333;
    }
    .stButton>button {
        width: 100%;
        background-color: transparent;
        color: #FAFAFA;
        border: 1px solid #4CAF50;
        border-radius: 4px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #4CAF50;
        color: #0E1117;
    }
    .nuclear-btn>button {
        border-color: #F44336;
    }
    .nuclear-btn>button:hover {
        background-color: #F44336;
        color: white;
    }
    .record-box {
        background-color: #1E2127;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #3b82f6;
    }
    .hash-text {
        font-family: monospace;
        color: #eab308;
        font-size: 0.9em;
        word-break: break-all;
    }
</style>
""", unsafe_allow_html=True)

# --- SIMULATED LLM STATE ---
# In a real app, this would query your Llama/Mistral node.
def fetch_llm_records(identity):
    mock_db = {
        "Rohan Kamath": [
            {"id": "C107_1", "type": "Note", "text": "The database root password is 'Sahyadri@2026'."},
            {"id": "C107_2", "type": "Classification", "text": "Photo of Aadhaar Card - Rohan K."},
            {"id": "C107_3", "type": "Metadata", "text": "College_ID_Scan_Rohan.jpg"},
            {"id": "C107_4", "type": "Message", "text": "My current location is near Pabba's, Lalbagh."},
            {"id": "C107_5", "type": "Title", "text": "Neural_Network_Optimization_Notes.pdf"}
        ]
    }
    return mock_db.get(identity, [])

def generate_merkle_root(seed):
    """Simulates a cryptographic fingerprint of the model weights."""
    return hashlib.sha256(f"MANTEXIA_NODE_STATE_{seed}_{time.time()}".encode()).hexdigest()

# --- APP STATE MANAGEMENT ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'records' not in st.session_state:
    st.session_state.records = []
if 'selected_records' not in st.session_state:
    st.session_state.selected_records = []

# --- UI HEADER ---
st.markdown("<h1 style='color: #60a5fa; margin-bottom: 0px;'>VERIUNLEARN AUDITOR</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='color: #94a3b8; margin-top: 0px; font-weight: 300;'>CRYPTOGRAPHIC PRIVACY VERIFICATION GATEWAY</h4>", unsafe_allow_html=True)
st.markdown("<hr style='border-color: #333;'>", unsafe_allow_html=True)

# ==========================================
# STEP 1: SEARCH GATEWAY
# ==========================================
if st.session_state.step == 1:
    st.markdown("🔍 **Search Identity across AI Node:**")
    query = st.text_input("", value=st.session_state.search_query, placeholder="e.g., Rohan Kamath")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("RUN PRIVACY AUDIT"):
        if query:
            st.session_state.search_query = query
            st.session_state.records = fetch_llm_records(query)
            st.session_state.step = 2
            st.rerun()

# ==========================================
# STEP 2: RECORD SELECTION
# ==========================================
elif st.session_state.step == 2:
    st.markdown(f"Identity **'{st.session_state.search_query}'** has {len(st.session_state.records)} records resident in model weights.")
    st.markdown("**Audit Result Details:**")
    
    selected_ids = []
    for rec in st.session_state.records:
        st.markdown(f"""
        <div class="record-box">
            <b>{rec['id']}</b> | {rec['type']}: {rec['text']}
        </div>
        """, unsafe_allow_html=True)
        # We use a unique key for the checkbox
        if st.checkbox(f"Target {rec['id']}", key=f"chk_{rec['id']}"):
            selected_ids.append(rec['id'])
    
    st.session_state.selected_records = selected_ids
    
    st.markdown("<hr style='border-color: #333;'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Surgical Strike")
        if st.button("PURGE SELECTED ITEMS"):
            if not selected_ids:
                st.warning("Select at least one record to activate.")
            else:
                st.session_state.unlearn_mode = "SURGICAL"
                st.session_state.step = 3
                st.rerun()
                
    with col2:
        st.markdown("### Nuclear Option")
        st.markdown('<div class="nuclear-btn">', unsafe_allow_html=True)
        if st.button("EXECUTE FULL IDENTITY PURGE"):
            st.session_state.unlearn_mode = "NUCLEAR"
            st.session_state.step = 3
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    if st.button("← Back to Search"):
        st.session_state.step = 1
        st.rerun()

# ==========================================
# STEP 3: EXECUTION & CERTIFICATE
# ==========================================
elif st.session_state.step == 3:
    mode = st.session_state.unlearn_mode
    target_count = len(st.session_state.selected_records) if mode == "SURGICAL" else len(st.session_state.records)
    
    st.markdown(f"### Executing {mode} Protocol...")
    
    # Progress Simulation
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1. Pre-Hash
    status_text.text("Loading Llama-3 Node...")
    time.sleep(1)
    pre_hash = generate_merkle_root("PRE")
    st.markdown(f"🔒 **Pre-Root Captured:** <span class='hash-text'>{pre_hash}</span>", unsafe_allow_html=True)
    progress_bar.progress(30)
    
    # 2. Scrubbing
    status_text.text(f"Scrubbing {target_count} specific records from weight-space...")
    time.sleep(2)
    progress_bar.progress(70)
    
    # 3. Post-Hash
    status_text.text("Verifying neural reset...")
    time.sleep(1)
    post_hash = generate_merkle_root("POST")
    st.markdown(f"🔓 **Post-Root Verified:** <span class='hash-text'>{post_hash}</span>", unsafe_allow_html=True)
    progress_bar.progress(100)
    status_text.text("✅ Model weights scrubbed and verified!")
    
    st.markdown("<hr style='border-color: #333;'>", unsafe_allow_html=True)
    
    # --- GENERATE COMPLIANCE CERTIFICATE ---
    st.subheader("EXISTING_COMPLIANCE_CERTIFICATES")
    
    cert_data = {
        "subject": st.session_state.search_query,
        "strategy": mode,
        "records_scrubbed": target_count,
        "llm_certification": {
            "base_model": "meta-llama/Llama-3.2-1B-Instruct",
            "framework": "VeriUnlearn SISA-HMO v0.1"
        },
        "merkle_root_pre": pre_hash,
        "merkle_root_post": post_hash,
        "timestamp": str(datetime.now()),
        "status": "VERIFIED_PURGED"
    }
    
    st.json(cert_data)
    
    json_string = json.dumps(cert_data, indent=4)
    st.download_button(
        label=f"Download Certificate (cert_{st.session_state.search_query.replace(' ', '_')}.json)",
        data=json_string,
        file_name=f"cert_{st.session_state.search_query.replace(' ', '_')}.json",
        mime="application/json"
    )

    if st.button("Start New Audit"):
        st.session_state.step = 1
        st.session_state.search_query = ""
        st.session_state.records = []
        st.session_state.selected_records = []
        st.rerun()

# --- FOOTER ---
st.markdown("<br><hr style='border-color: #333;'><center><small style='color:#64748b;'>VeriUnlearn SISA-HMO Framework | v0.1</small></center>", unsafe_allow_html=True)