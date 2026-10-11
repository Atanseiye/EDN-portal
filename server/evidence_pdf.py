"""Dependency-free paginated PDF for CPython and Cloudflare Python Workers.

Built-in PDF fonts use transliterated text; the companion JSON preserves Unicode.
"""
import textwrap
import unicodedata


def printable(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in normalized if not unicodedata.combining(c)).encode("ascii", "backslashreplace").decode()


def validation_pdf(snapshot):
    pages = []
    commands = []
    y = 735

    def escape(text):
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def page():
        nonlocal commands, y
        if commands:
            pages.append(commands)
        commands = ["0.02 0.20 0.19 rg 0 782 595 60 re f",
                    "BT /F2 17 Tf 1 1 1 rg 42 805 Td (EDNAi | Developer validation) Tj ET"]
        y = 745

    def line(text, size=10, bold=False):
        nonlocal y
        if y < 65:
            page()
        font = "F2" if bold else "F1"
        commands.append(f"BT /{font} {size} Tf 0.05 0.12 0.13 rg 42 {y} Td ({escape(printable(text))}) Tj ET")
        y -= size + 6

    def paragraph(label, value):
        nonlocal y
        line(label, 10, True)
        text = printable(value if value not in (None, "") else "Not provided")
        for block in text.splitlines() or [""]:
            for chunk in textwrap.wrap(block, 86, replace_whitespace=False) or [""]:
                line(chunk)
        y -= 7

    page()
    line("NATIONAL AI INNOVATION CHALLENGE 2026", 12, True)
    line("PS1 - Developer Infrastructure", 18, True)
    paragraph("Report snapshot (UTC)", snapshot["generated_at"])
    stats = snapshot["validation"]
    verified = stats["unique_verified_external_beta_testers"]
    paragraph("Validation status", f"{verified} unique verified external testers / target 2. " +
              ("Tester threshold met." if verified >= 2 else "INCOMPLETE: tester threshold not met."))
    paragraph("Collection summary", f"{stats['consented_feedback_records']} consented records; "
              f"{stats['unique_external_beta_submissions']} unique external submissions; "
              f"{stats['pending_external_submissions']} pending external records.")
    paragraph("Methodology", "Feedback was submitted by developers, deduplicated using a hashed stable identifier, "
              "and reviewed by an EDNAi administrator. Repeat submissions count once toward the tester threshold. "
              "Admin verification records an internal review, not independent certification.")
    paragraph("Evidence boundary", "This report documents developer validation. Tester statements and supplied samples "
              "are self-reported unless corroborated by linked records. It does not independently prove model "
              "provenance, production readiness, or benchmark quality. Submit integration evidence separately.")
    paragraph("Privacy and text", "Names and raw identifiers are excluded. Free-text evidence should be redacted before "
              "submission. PDF text is transliterated for portable rendering; the JSON export preserves original Unicode.")
    verified_records = [r for r in snapshot["records"] if r["verified_external"] and r["external_tester"]]
    pending = [r for r in snapshot["records"] if r not in verified_records]
    for heading, records in [("VERIFIED EXTERNAL EVIDENCE", verified_records),
                             ("APPENDIX - UNVERIFIED / INTERNAL FEEDBACK", pending)]:
        page()
        line(heading, 13, True)
        if not records:
            paragraph("Records", "No records in this category at the time of export.")
        for index, r in enumerate(records):
            if index:
                page()
            paragraph("Evidence reference", r["id"])
            paragraph("Tester reference (hashed)", r["tester_hash"])
            paragraph("Review status", "Verified external" if r in verified_records else "Unverified - does not count toward threshold")
            paragraph("Submitted / reviewed (UTC)", f"{r['created_at']} / {r.get('verified_at') or 'Not reviewed'}")
            paragraph("Affiliation / developer role", f"{r.get('affiliation') or 'Not provided'} / {r.get('role') or 'Not provided'}")
            paragraph("Features tested", ", ".join(r["features"]))
            paragraph("Rating / usefulness", f"{r['rating']}/5; useful: {r['useful']}")
            for key, value in r["test_details"].items():
                paragraph(key.replace("_", " ").title(), value)
            if not r["test_details"]:
                paragraph("Evidence completeness", "Legacy feedback: detailed test evidence not supplied.")
            paragraph("Blockers", r.get("blocker"))
            paragraph("Other feedback", r.get("notes"))
    pages.append(commands)
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", 
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
    kids = []
    for number, cmds in enumerate(pages, 1):
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {page_id+1} 0 R >>".encode())
        cmds.append(f"BT /F1 9 Tf 0.4 0.4 0.4 rg 42 32 Td (EDNAi | NAIC validation evidence | Page {number} of {len(pages)}) Tj ET")
        stream = "\n".join(cmds).encode("ascii")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(result)
    result.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010} 00000 n \n".encode())
    result.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode())
    return bytes(result)
