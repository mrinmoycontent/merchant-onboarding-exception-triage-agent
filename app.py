import os
import re
from datetime import datetime, timezone

import gspread
from google.auth import default
from flask import Flask, jsonify
from openai import OpenAI

app = Flask(__name__)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_MODEL = os.environ.get("HF_MODEL", "openai/gpt-oss-120b")


def get_sheet():
    if not SPREADSHEET_ID:
        raise RuntimeError("Spreadsheet ID is missing.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials, _ = default(
        scopes=scopes,
        quota_project_id="merchant-onboarding-507611",
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.get_worksheet(0)

    if worksheet is None:
        raise RuntimeError("No worksheet found in the spreadsheet.")

    return worksheet


GST_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
PAN_REGEX = r"^[A-Z]{5}[0-9]{4}[A-Z]$"


def validate_gst(value):
    value = str(value or "").strip().upper()

    if not value:
        return False, "Missing GST Number"

    if not re.fullmatch(GST_REGEX, value):
        return False, "Invalid GST Number format"

    return True, ""


def validate_pan(value):
    value = str(value or "").strip().upper()

    if not value:
        return False, "Missing PAN"

    if not re.fullmatch(PAN_REGEX, value):
        return False, "Invalid PAN format"

    return True, ""


def is_yes(value):
    return str(value or "").strip().upper() == "Y"


def validate_row(row):
    reasons = []
    hard_reject = False

    for field in ["Merchant Name", "Business Type", "Submitted Date"]:
        if not str(row.get(field, "")).strip():
            reasons.append(f"Missing {field}")

    gst_ok, gst_reason = validate_gst(row.get("GST Number"))
    if not gst_ok:
        reasons.append(gst_reason)
        if gst_reason == "Invalid GST Number format":
            hard_reject = True

    pan_ok, pan_reason = validate_pan(row.get("PAN"))
    if not pan_ok:
        reasons.append(pan_reason)
        if pan_reason == "Invalid PAN format":
            hard_reject = True

    bank_proof = row.get("Bank Proof")
    if bank_proof is None:
        bank_proof = row.get("Bank Proof (Y/N)", "")

    kyc_doc = row.get("KYC Doc")
    if kyc_doc is None:
        kyc_doc = row.get("KYC Doc (Y/N)", "")

    if not is_yes(bank_proof):
        reasons.append("Bank Proof missing")

    if not is_yes(kyc_doc):
        reasons.append("KYC Document missing")

    if hard_reject:
        status = "REJECT"
    elif reasons:
        status = "FLAG"
    else:
        status = "PASS"

    return status, "; ".join(reasons)


def fallback_email(merchant_name, reason):
    return (
        "Subject: Action Required – Merchant Onboarding\n\n"
        f"Dear {merchant_name},\n\n"
        "We reviewed your merchant onboarding submission "
        "and found the following issue(s):\n\n"
        f"{reason}\n\n"
        "Please correct the above information and resubmit "
        "the required documents so we can continue the "
        "onboarding process.\n\n"
        "Regards,\n"
        "Merchant Operations Team"
    )


def draft_email(merchant_name, reason):
    merchant_name = merchant_name or "Merchant"
    fallback = fallback_email(merchant_name, reason)

    if not HF_TOKEN:
        return fallback

    try:
        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=HF_TOKEN,
        )

        prompt = f"""
You are a merchant onboarding operations assistant.

Merchant name:
{merchant_name}

Exception found:
{reason}

Draft a short, professional email asking the merchant
to correct or resubmit only the missing or incorrect
onboarding information or documents.

Rules:
- Keep it under 100 words.
- Be polite and clear.
- Do not invent details.
- Mention the specific issue or issues.
- Do not claim permanent rejection.
- Ask the merchant to resubmit the corrected information
  or documents.
- Include a simple subject line.
- Return only the email.
"""

        response = client.chat.completions.create(
            model=HF_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional merchant "
                        "operations email assistant."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=250,
        )

        text = response.choices[0].message.content.strip()
        return text if text else fallback

    except Exception as exc:
        app.logger.exception(
            "Hugging Face email generation failed: %s", exc
        )
        return fallback


def run_triage():
    sheet = get_sheet()
    records = sheet.get_all_records()

    if not records:
        return {
            "status": "success",
            "processed": 0,
            "counts": {"PASS": 0, "FLAG": 0, "REJECT": 0},
        }

    headers = sheet.row_values(1)

    output_columns = [
        "Status",
        "Exception Reason",
        "AI Draft Email",
        "Processed At",
    ]

    for column in output_columns:
        if column not in headers:
            headers.append(column)

    sheet.update("1:1", [headers], value_input_option="USER_ENTERED")

    header_map = {name: index + 1 for index, name in enumerate(headers)}

    status_col = header_map["Status"]
    reason_col = header_map["Exception Reason"]
    email_col = header_map["AI Draft Email"]
    processed_col = header_map["Processed At"]

    counts = {"PASS": 0, "FLAG": 0, "REJECT": 0}
    updates = []

    for row_number, row in enumerate(records, start=2):
        status, reason = validate_row(row)
        email = ""

        if status in ("FLAG", "REJECT"):
            email = draft_email(
                row.get("Merchant Name", "Merchant"),
                reason,
            )

        processed_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        updates.extend([
            {
                "range": gspread.utils.rowcol_to_a1(row_number, status_col),
                "values": [[status]],
            },
            {
                "range": gspread.utils.rowcol_to_a1(row_number, reason_col),
                "values": [[reason if reason else "-"]],
            },
            {
                "range": gspread.utils.rowcol_to_a1(row_number, email_col),
                "values": [[email if email else "-"]],
            },
            {
                "range": gspread.utils.rowcol_to_a1(row_number, processed_col),
                "values": [[processed_at]],
            },
        ])

        counts[status] += 1

    if updates:
        sheet.batch_update(updates, value_input_option="USER_ENTERED")

    return {
        "status": "success",
        "processed": len(records),
        "counts": counts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def health():
    return jsonify({
        "service": "Merchant Onboarding Exception Triage Agent",
        "status": "ok",
        "endpoint": "POST /triage",
    })


@app.post("/triage")
def triage():
    try:
        result = run_triage()
        return jsonify(result), 200
    except Exception as exc:
        app.logger.exception("Triage failed")
        return jsonify({
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
