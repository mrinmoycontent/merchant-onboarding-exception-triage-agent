# Merchant Onboarding Exception Triage Agent

An AI-assisted operations automation project that helps merchant onboarding teams review applications, identify missing or invalid information, classify onboarding cases, and generate clear resubmission emails.

## Problem

Merchant onboarding teams often spend time manually checking applications for missing or invalid GST/PAN information, bank proof, KYC documents, and other required fields.

This project automates the first-level exception check so operations teams can identify problematic applications faster and provide merchants with clear next steps.

## Workflow

Google Sheets → Apps Script → Cloud Run → Python Validation → PASS / FLAG / REJECT → Hugging Face AI Email → Google Sheets

## What It Does

1. Reads merchant onboarding records from Google Sheets.
2. Validates required fields, GST, PAN, bank proof, and KYC.
3. Classifies each record:
   - **PASS** — no validation exception.
   - **FLAG** — missing information or documents require correction.
   - **REJECT** — hard validation failure such as invalid GST/PAN format.
4. Generates an AI-assisted resubmission email for FLAG and REJECT cases.
5. Writes the status, exception reason, email draft, and processing timestamp back to Google Sheets.

## Architecture

```text
Merchant Onboarding Queue
          ↓
     Google Sheets
          ↓
     Google Apps Script
          ↓
       Cloud Run
          ↓
   Python / Flask API
          ↓
 Deterministic Validation
          ↓
   PASS / FLAG / REJECT
          ↓
 Hugging Face LLM
          ↓
 AI Draft Email
          ↓
     Google Sheets
```

## Why the AI Is Used

The core onboarding decision is rule-based rather than delegated to the LLM. This keeps the operational classification predictable and auditable.

The AI is used for the communication layer: drafting concise, professional emails that explain the detected exception without inventing information.

A deterministic fallback email is returned if the Hugging Face service is unavailable.

## Technology Stack

- Python
- Flask
- Google Sheets
- Google Apps Script
- Google Cloud Run
- Google Sheets API
- gspread
- Hugging Face Inference Providers
- OpenAI-compatible API client
- Docker
- GitHub

## Repository Files

```text
merchant-onboarding-exception-triage-agent/
├── app.py
├── apps_script.gs
├── Dockerfile
├── requirements.txt
├── sample_data.csv
├── README.md
└── .gitignore
```

## Example

A merchant with valid GST and bank proof but a missing PAN and KYC document can be classified as:

```text
FLAG
```

with an exception such as:

```text
Missing PAN; KYC Document missing
```

The system then generates a professional resubmission email for the merchant.

## Verified End-to-End Result

The deployed workflow was successfully tested through Cloud Run and the Google Apps Script trigger.

```text
Records processed: 25
PASS:   11
FLAG:    7
REJECT:  7
Status: success
```

## Business Value

The project demonstrates how merchant operations teams can automate repetitive onboarding checks while keeping business rules deterministic.

Potential benefits:

- Faster exception identification
- More consistent validation
- Reduced manual checking
- Clearer merchant communication
- Better visibility into onboarding queues
- Easier exception handling and prioritization

## Recruiter Summary

**Merchant Onboarding Exception Triage Agent** is an operations automation project that combines deterministic business-rule validation with AI-assisted communication. It automates the first-level review of merchant onboarding submissions, classifies cases as PASS/FLAG/REJECT, and generates resubmission emails for exceptions.

## Future Improvements

- Merchant notification tracking
- Audit history
- API authentication
- Retry and failure monitoring
- Role-based access
- Operations dashboard
- Additional document validation
- Integration with a production merchant onboarding platform

## Author

**Mrinmoy Choudhury**

Operations & Merchant Operations | Process Automation | Analytics
