# RegTrack — Regulatory Change Tracker

Compares an existing company compliance policy against a new regulatory
circular and reports which clauses are compliant, gaps, conflicts, or missing.

## Quick start (local/offline test mode -- no API key, no downloads)

```bash
pip install -r requirements.txt --break-system-packages
cd regtrack
python3 pipeline.py data/sample_policy.txt data/sample_circular.txt
```

This runs with `REGTRACK_LOCAL_TEST_MODE=true` (the default), using
TF-IDF similarity + a rule-based mock verdict instead of real embeddings
and a real LLM call. Good for confirming the pipeline plumbing works
before you have API access set up.

## Real mode (for the actual hackathon demo)

```bash
export REGTRACK_LOCAL_TEST_MODE=false
export XAI_API_KEY=your_key_here
pip install sentence-transformers chromadb openai --break-system-packages
python3 pipeline.py sample_policy.txt sample_circular.txt
```

This downloads the `bge-small-en-v1.5` embedding model (needs internet,
~130MB, first run only), stores vectors in ChromaDB, and calls Grok
for the actual gap-analysis reasoning. Results will be meaningfully
better than mock mode -- the mock uses word overlap and misses things
like numeric/threshold changes (e.g. "10 years" vs "8 years"), which
the real LLM catches correctly.

## Running as a web app

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/` to use the web UI. It fetches live RBI
notices from `rbi.org.in`, lets you pick one, upload your policy, and
run gap analysis.

API endpoints:
- `GET /regtrack/notices` — fetch parsed RBI notifications
- `POST /regtrack/analyze` — upload `policy_file` + `circular_file`
- `POST /regtrack/analyze-notice` — upload `policy_file` + RBI notice URL/id

## Auto-fetching new circulars from RBI

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

**For the live demo:** don't rely on scraping RBI's site in real time --
run `scraper.py` once beforehand to cache a couple of real circulars
locally, then demo the analysis pipeline against those cached files.

## File structure
```
regtrack/
├── config.py           # LOCAL_TEST_MODE toggle, model names, paths
├── pdf_parser.py        # extracts text from .pdf or .txt
├── chunker.py            # splits documents into clause-level chunks
├── embeddings.py          # TF-IDF (local) or sentence-transformers (real)
├── vector_store.py         # in-memory cosine sim (local) or ChromaDB (real)
├── gap_analyzer.py          # mock heuristic (local) or Grok API (real)
├── pipeline.py                # orchestrates the full flow
├── main.py                     # FastAPI web app entry point
├── router.py                   # FastAPI endpoints + RBI notice routes
├── scraper.py                    # RBI notice parser + auto-fetch scheduler
├── static/index.html             # web UI for RBI notice analysis
└── data/
    ├── sample_policy.txt          # test old-policy doc
    └── sample_circular.txt         # test new-circular doc
```
