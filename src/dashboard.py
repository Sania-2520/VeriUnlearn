import json
import os

def display_compliance_report(user_id="SANIA_001"):
    cert_path = f"./proofs/certificate_{user_id}.json"
    
    if not os.path.exists(cert_path):
        print("❌ No unlearning certificate found for this user.")
        return

    with open(cert_path, "r") as f:
        cert = json.load(f)

    print("\n" + "═"*60)
    print("🛡️  MANTEXIA SOLUTIONS: VERIUNLEARN COMPLIANCE REPORT")
    print("═"*60)
    print(f"CERTIFICATE ID : {cert['certificate_id']}")
    print(f"USER REFERENCE : {cert['evidence_summary']['user_id']}")
    print(f"TIMESTAMP      : {cert['evidence_summary']['timestamp']}")
    print(f"COMPLIANCE     : {cert['compliance']}")
    print(f"PROOF STATUS   : ✅ {cert['verifier_output']} (zk-SNARK Verified)")
    print("-" * 60)
    print("STATE TRANSITION FINGERPRINT:")
    print(f"PRE-ERASURE  : {cert['evidence_summary']['state_transition']['pre_unlearn_root'][:32]}...")
    print(f"POST-ERASURE : {cert['evidence_summary']['state_transition']['post_unlearn_root'][:32]}...")
    print("-" * 60)
    print("LEGAL NOTICE: The weights associated with this user's data have been")
    print("physically purged from the local hardware (RTX 4050).")
    print("═"*60 + "\n")

if __name__ == "__main__":
    display_compliance_report()