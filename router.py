"""
FastAPI router for the RegTrack module.
Mount this in your main app with:
    from regtrack.router import router as regtrack_router
    app.include_router(regtrack_router, prefix="/regtrack")
"""

import os
import shutil
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from pipeline import run_regtrack_pipeline

router = APIRouter()


def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename)[1]
    if suffix.lower() not in (".pdf", ".txt"):
        raise HTTPException(400, f"Unsupported file type: {suffix}. Use .pdf or .txt")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    with tmp as f:
        shutil.copyfileobj(upload.file, f)
    return tmp.name


@router.post("/analyze")
async def analyze_gap(policy_file: UploadFile = File(...),
                       circular_file: UploadFile = File(...)):
    policy_path = _save_upload(policy_file)
    circular_path = _save_upload(circular_file)

    try:
        report = run_regtrack_pipeline(policy_path, circular_path)
    finally:
        os.unlink(policy_path)
        os.unlink(circular_path)

    return report
