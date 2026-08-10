# Guard — AI Compliance Suite

Two tools for a bank compliance team, in one repo:

1. **Regulatory Change Tracker** — compares an existing company compliance
   policy against a new regulatory circular and reports which clauses are
   compliant, gaps, conflicts, or missing.
2. **AML Alert Re-ranker** (`aml/`) — re-scores alerts a rule engine already
   flagged with a 0–100 suspicion score, sorts the queue by that score
   instead of arrival order, and explains each score with SHAP.

These are two separate tools sharing a compliance-ops narrative ("catch the
regulatory change, then triage the alerts it causes"), not a shared
technical pipeline — worth saying that plainly to judges/teammates rather
than implying deeper integration than exists.

**Note on paths below:** RegTrack's files live at the repo root (not inside
a `regtrack/` subfolder), so the commands here are adjusted from a draft
version that assumed that subfolder — run everything from the repo root
unless a step says otherwise.

---

## Regulatory Change Tracker

### Quick start (local/offline test mode — no API key, no downloads)

```bash
pip install -r requirements.txt --break-system-packages
python3 pipeline.py data/sample_policy.txt data/sample_circular.txt
```

This runs with `REGTRACK_LOCAL_TEST_MODE=true` (the default), using TF-IDF
similarity + a rule-based mock verdict instead of real embeddings and a real
LLM call. Good for confirming the pipeline plumbing works before you have
API access set up.

### Real mode (for the actual hackathon demo)

```bash
export REGTRACK_LOCAL_TEST_MODE=false
export XAI_API_KEY=your_key_here
pip install sentence-transformers chromadb openai --break-system-packages
python3 pipeline.py data/sample_policy.txt data/sample_circular.txt
```

This downloads the `bge-small-en-v1.5` embedding model (needs internet,
~130MB, first run only), stores vectors in ChromaDB, and calls Grok for the
actual gap-analysis reasoning. Results will be meaningfully better than mock
mode — the mock uses word overlap and misses things like numeric/threshold
changes (e.g. "10 years" vs "8 years"), which the real LLM catches
correctly.

### Running as a web app

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/` to use the web UI. It fetches live RBI notices
from `rbi.org.in`, lets you pick one, upload your policy, and run gap
analysis.

API endpoints:
- `GET /regtrack/notices` — fetch parsed RBI notifications
- `POST /regtrack/analyze` — upload `policy_file` + `circular_file`
- `POST /regtrack/analyze-notice` — upload `policy_file` + RBI notice URL/id

### Auto-fetching new circulars from RBI

```bash
python3 scraper.py   # inspects the live page structure -- run this first
                      # to confirm selectors still match before a demo
```

To wire auto-fetch into the app on a schedule:

```python
from scraper import start_scheduler
from pipeline import run_regtrack_pipeline

def handle_new_circular(filepath, title):
    report = run_regtrack_pipeline("data/policies/current_policy.pdf", filepath)
    # push report to dashboard / DB here

start_scheduler(interval_hours=6, on_new_circular=handle_new_circular)
```

**For the live demo:** don't rely on scraping RBI's site in real time — run
`scraper.py` once beforehand to cache a couple of real circulars locally,
then demo the analysis pipeline against those cached files.

### File structure

```
guard/
├── config.py           # LOCAL_TEST_MODE toggle, model names, paths
├── pdf_parser.py        # extracts text from .pdf or .txt
├── chunker.py            # splits documents into clause-level chunks
├── embeddings.py          # TF-IDF (local) or sentence-transformers (real)
├── vector_store.py         # in-memory cosine sim (local) or ChromaDB (real)
├── gap_analyzer.py          # mock heuristic (local) or Grok API (real)
├── pipeline.py                # orchestrates the full flow
├── main.py                     # FastAPI web app entry point
├── router.py                   # FastAPI endpoints + RBI notice routes
├── report_formatter.py          # formats the gap-analysis report
├── scraper.py                    # RBI notice parser + auto-fetch scheduler
├── static/index.html             # web UI for RBI notice analysis
└── data/
    ├── sample_policy.txt          # test old-policy doc
    └── sample_circular.txt         # test new-circular doc
```

---

## AML Alert Re-ranker (`aml/`)

Banks' rule-based AML systems can only tell you a threshold was crossed, not
how suspicious a transaction actually is — so every alert lands in the same
first-in-first-out queue, and analysts burn hours on mostly false positives.

This module doesn't replace the rule engine (regulators require it to exist
for auditability). It sits **downstream** of it: every transaction the rule
engine already flagged gets a 0–100 suspicion score from an XGBoost model
trained on multiple weak signals at once (amount vs. that sender's own
typical size, % of balance drained, transaction velocity, new-beneficiary
flag, hour of day, account age), the queue gets re-sorted by that score, and
SHAP explains why each score is what it is.

The headline result: reviewing the same top-K alerts, the re-ranked queue
catches far more real fraud than the arrival-order queue does — that's the
whole pitch in one chart (Precision@K), shown at the top of the app.

### Quick start

Data and a trained model are already committed to the repo, so no
regeneration is required to just see it running:

```bash
pip install -r aml/requirements.txt --break-system-packages
cd aml
streamlit run app.py
```

Opens `http://localhost:8501`.

**Mac + XGBoost note:** if this errors with something about `libomp.dylib`,
run `brew install libomp` first — a known macOS issue with the XGBoost
wheel, not a problem with the code.

### Regenerating the data/model from scratch

Only needed if you change `generate_data.py` or `train_model.py`:

```bash
cd aml
python3 generate_data.py
python3 train_model.py
```

### File structure

```
aml/
├── app.py                # Streamlit entry point
├── aml_dashboard.py        # the actual dashboard: Precision@K chart,
│                            # queue comparison, SHAP explanations
├── generate_data.py          # synthetic transaction dataset generator
├── train_model.py              # feature engineering, XGBoost training,
│                                # Precision@K + SHAP, saved to artifacts/
├── requirements.txt
├── data/transactions.csv         # generated dataset (committed)
└── artifacts/                      # trained model + scored alerts (committed)
    ├── model.joblib
    ├── features.joblib
    ├── precision_at_k.csv
    └── scored_alerts.csv
```

---

## Still open: a single unified app

Right now RegTrack (FastAPI, `http://127.0.0.1:8000`) and AML (Streamlit,
`http://localhost:8501`) run as two separate apps in two terminals — not
yet one merged experience. Merging a FastAPI app and a Streamlit app into
one properly needs a decision on approach (e.g. exposing AML's scores as a
FastAPI endpoint and adding a page to RegTrack's `static/` UI, vs. embedding
RegTrack's web view inside Streamlit) — flagged here as a known next step
rather than solved yet.