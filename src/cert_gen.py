from fpdf import FPDF
import json

class CertificateFactory:
    def create_compliance_bundle(self, data, file_path_no_ext):
        # 1. Save JSON Trace (Digital Proof)
        with open(f"{file_path_no_ext}.json", "w") as f:
            json.dump(data, f, indent=4)
            
        # 2. Save PDF Certificate (Visual Proof)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="GDPR COMPLIANCE: CERTIFICATE OF ERASURE", ln=True, align='C')
        
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        for key, value in data.items():
            pdf.cell(200, 10, txt=f"{key.upper()}: {value}", ln=True)
            
        pdf.output(f"{file_path_no_ext}.pdf")