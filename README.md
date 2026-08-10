# Guard — AI Compliance Suite

**Guard** is an AI-powered compliance suite containing three independent tools for financial institutions:

1. **Regulatory Change Tracker (RegTrack)** — compares an existing company compliance policy against a new regulatory circular and identifies compliant clauses, gaps, conflicts, and missing requirements.
2. **AML Alert Re-ranker** — re-scores alerts already flagged by a bank's rule engine, prioritizes the most suspicious cases, and explains the scores using SHAP.
3. **KYC Verifier** — verifies identity documents and performs face/document checks to support automated KYC verification.

These are **three separate tools sharing a common compliance-operations narrative**, rather than one tightly coupled technical pipeline.

---

# Regulatory Change Tracker

RegTrack helps compliance teams understand how a new regulatory circular affects an existing company policy.

It compares the policy against the circular and reports:

- Compliant requirements
- Regulatory gaps
- Conflicts
- Missing clauses
- Relevant policy sections
- Reasoning behind each finding

## Quick start — local/offline test mode

No API key or model download is required.

```bash
pip install -r requirements.txt --break-system-packages
python3 pipeline.py data/sample_policy.txt data/sample_circular.txt
```

The default configuration uses:

- TF-IDF similarity
- Rule-based mock verdicts
- Local processing

This mode is useful for verifying the pipeline before configuring external AI services.

## Real mode

For the full AI-powered analysis:

```bash
export REGTRACK_LOCAL_TEST_MODE=false
export XAI_API_KEY=your_key_here
pip install sentence-transformers chromadb openai --break-system-packages
python3 pipeline.py data/sample_policy.txt data/sample_circular.txt
```

The real mode:

- Uses `bge-small-en-v1.5` embeddings
- Stores vectors using ChromaDB
- Uses Grok for regulatory gap-analysis reasoning

The embedding model is downloaded on first use and requires an internet connection.

## Running the web app

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

### API endpoints

| Endpoint                        | Description                             |
| ------------------------------- | --------------------------------------- |
| `GET /regtrack/notices`         | Fetch and parse RBI notifications       |
| `POST /regtrack/analyze`        | Analyze an uploaded policy and circular |
| `POST /regtrack/analyze-notice` | Analyze a policy against an RBI notice  |

## RBI circular fetching

```bash
python3 scraper.py
```

Run this before a live demo to confirm that RBI's current page structure is still compatible with the scraper.

For demos, it is recommended to cache a few real circulars beforehand instead of depending on RBI's website being available during the presentation.

---

# AML Alert Re-ranker

The AML module sits **downstream of an existing rule-based AML system**.

The rule engine identifies transactions that require investigation. Guard then assigns each flagged transaction a **0–100 suspicion score**, allowing investigators to prioritize the most suspicious cases first.

The model considers signals such as:

- Transaction amount relative to the sender's normal activity
- Percentage of account balance drained
- Transaction velocity
- New-beneficiary indicators
- Transaction hour
- Account age
- Other behavioral features

The queue is then re-ranked according to the model's suspicion score.

**SHAP** explanations show analysts why an alert received its score.

### Main evaluation metric

The dashboard compares the re-ranked queue against the original arrival-order queue using **Precision@K**.

## Quick start

The dataset and trained model are already committed to the repository.

```bash
pip install -r aml/requirements.txt --break-system-packages
cd aml
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### Regenerating the model

Only required if the data-generation or training pipeline is modified:

```bash
cd aml
python3 generate_data.py
python3 train_model.py
```

### macOS XGBoost note

If XGBoost reports an error involving `libomp.dylib`:

```bash
brew install libomp
```

This is a known macOS dependency issue with XGBoost.

---

# KYC Verifier

The **KYC Verifier** provides automated identity-verification capabilities for financial institutions.

It is designed to reduce manual KYC workload by combining document processing with identity and face verification.

The module can be used as a standalone KYC verification tool within the Guard suite.

### Capabilities

- Identity document processing
- OCR-based information extraction
- Document/image analysis
- Face verification
- KYC verification workflow
- Automated verification results

### Quick start

Navigate to the KYC module:

```bash
cd kyc-verifier
```

Install its dependencies:

```bash
pip install -r requirements.txt
```

The project is currently configured for **Python 3.12** because its computer-vision and deep-learning dependencies, including TensorFlow and DeepFace, are more compatible with Python 3.12 than Python 3.14.

Run the application according to the entry point provided in `kyc-verifier`.

> **Note:** Python 3.14 is not currently recommended for this module because some of its TensorFlow/DeepFace dependencies do not provide compatible Windows wheels.

---

# Repository Structure

```text
guard/
│
├── config.py
├── pdf_parser.py
├── chunker.py
├── embeddings.py
├── vector_store.py
├── gap_analyzer.py
├── pipeline.py
├── main.py
├── router.py
├── report_formatter.py
├── scraper.py
│
├── static/
│   └── index.html
│
├── data/
│   ├── sample_policy.txt
│   └── sample_circular.txt
│
├── aml/
│   ├── app.py
│   ├── aml_dashboard.py
│   ├── generate_data.py
│   ├── train_model.py
│   ├── requirements.txt
│   ├── data/
│   │   └── transactions.csv
│   └── artifacts/
│       ├── model.joblib
│       ├── features.joblib
│       ├── precision_at_k.csv
│       └── scored_alerts.csv
│
└── kyc-verifier/
    ├── requirements.txt
    └── ...
```

---

# Architecture

Guard currently consists of three independent applications/modules:

```text
                    GUARD
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   RegTrack          AML           KYC
       │              │              │
 Regulatory       Alert          Identity
  Changes        Prioritization  Verification
       │              │              │
       ▼              ▼              ▼
   FastAPI        Streamlit      KYC App
```

They share the same **compliance-operations narrative**, but they do not currently depend on one another technically.

---

# Current Application Status

| Tool             | Purpose                                 | Application                |
| ---------------- | --------------------------------------- | -------------------------- |
| **RegTrack**     | Regulatory change & policy gap analysis | FastAPI                    |
| **AML**          | Alert prioritization & explainability   | Streamlit                  |
| **KYC Verifier** | Identity/document verification          | Standalone KYC application |

## Current limitation

RegTrack, AML, and KYC are currently separate applications rather than a single unified interface.

A future version could provide a unified Guard dashboard where compliance teams can access:

```text
Guard Dashboard
│
├── Regulatory Change Tracker
├── AML Alert Re-ranker
└── KYC Verifier
```

This would turn the three tools into a single compliance-operations platform while keeping their underlying services modular.
