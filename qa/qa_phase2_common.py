"""Shared fixtures + helpers for Phase 2 Dataset Management QA."""
from __future__ import annotations

import csv
import io
import json
import zipfile

import httpx

BASE = "http://127.0.0.1:8000"


def make_client(base: str = BASE) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=120)


def register_and_login(client: httpx.Client, email: str = "phase2@veriunlearn.dev", password: str = "password123") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "full_name": "Phase2 QA", "password": password})
    if r.status_code == 409:
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def auth_headers(client: httpx.Client) -> dict:
    return register_and_login(client)


def upload(client: httpx.Client, headers: dict, filename: str, content: bytes, shard_count: int = 4, base: str = BASE):
    return client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        data={"shard_count": str(shard_count)},
        files={"file": (filename, content)},
    )


# --------------------------------------------------------------------------- fixtures

def csv_bytes(n: int = 50, *, name_col: bool = False, label=True) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    if name_col:
        w.writerow(["name", "a", "b", "label"])
        for i in range(n):
            w.writerow([f"user{i}", round((i % 7) / 3, 3), round(((i * 2) % 11) / 5, 3), i % 2])
    else:
        w.writerow(["a", "b", "label"])
        for i in range(n):
            w.writerow([round((i % 7) / 3, 3), round(((i * 2) % 11) / 5, 3), i % 2])
    return buf.getvalue().encode()


def json_bytes(n: int = 20) -> bytes:
    return json.dumps([{"a": i % 7, "b": (i * 2) % 11, "label": i % 2} for i in range(n)]).encode()


def jsonl_bytes(n: int = 20) -> bytes:
    return b"\n".join(
        json.dumps({"a": i % 7, "b": (i * 2) % 11, "label": i % 2}).encode() for i in range(n)
    ) + b"\n"


def txt_bytes(n_lines: int = 12) -> bytes:
    return ("\n".join(f"This is knowledge line number {i} about privacy and unlearning." for i in range(n_lines)) + "\n").encode()


def md_bytes() -> bytes:
    return (
        "# Privacy Report 2026\n\n"
        "## Section 1\nVeriUnlearn enables verifiable machine unlearning.\n\n"
        "## Section 2\nGDPR Article 17 requires erasure of personal data.\n\n"
        "- item one\n- item two\n"
    ).encode()


def docx_bytes() -> bytes:
    """Minimal valid DOCX (zip with XML parts)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Hello DOCX world</w:t></w:r></w:p></w:body></w:document>",
        )
    return buf.getvalue()


def exe_bytes() -> bytes:
    return b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x0e\x1f\xba\x0e\x00\xb4\t\xcd!\xb8\x01L\xcd!This program cannot be run in DOS mode.\x00\r\n"


def corrupt_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\nthis is not a real pdf body\n\x00\xff\xfe garbage"


def empty_pdf_bytes() -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def encrypted_pdf_bytes(password: str = "secret123") -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes(pages=2)))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def pdf_bytes(pages: int = 3, *, title: str = "Phase 2 QA Document", author: str = "VeriUnlearn QA") -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_title(title)
    pdf.set_author(author)
    pdf.add_page()
    for p in range(pages):
        pdf.set_font("helvetica", size=12)
        pdf.multi_cell(0, 8, f"PDF page {p + 1} content: verifiable machine unlearning and privacy compliance.")
        if p < pages - 1:
            pdf.add_page()
    return bytes(pdf.output())


def oversized_bytes(mb: int = 51) -> bytes:
    return (b"x" * 1024 * 1024 * mb)  # > 50 MB limit
