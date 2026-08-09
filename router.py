"""
FastAPI router for the RegTrack module.
"""

import os
import shutil
import tempfile

import requests
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse

from pipeline import run_regtrack_pipeline
from report_formatter import format_report
from scraper import fetch_rbi_notices, download_circular


router = APIRouter()


def _save_upload(upload: UploadFile) -> str:
    """Save an uploaded PDF/TXT file temporarily."""

    suffix = os.path.splitext(upload.filename or "")[1]

    if suffix.lower() not in (".pdf", ".txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Use .pdf or .txt"
        )

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    with tmp as f:
        shutil.copyfileobj(upload.file, f)

    return tmp.name


# ---------------------------------------------------------
# RBI NOTICES
# ---------------------------------------------------------

@router.get("/notices")
async def list_rbi_notices(
    limit: int = Query(
        default=50,
        ge=1,
        le=200
    )
):
    """Fetch recent RBI notices."""

    try:
        notices = fetch_rbi_notices(
            limit=limit
        )

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch RBI notices: {exc}"
        ) from exc

    return {
        "count": len(notices),
        "notices": notices
    }


# ---------------------------------------------------------
# MANUAL PDF COMPARISON
# ---------------------------------------------------------

@router.post(
    "/analyze",
    response_class=PlainTextResponse
)
async def analyze_gap(
    policy_file: UploadFile = File(...),
    circular_file: UploadFile = File(...)
):
    """
    Compare a company policy against an uploaded RBI circular.
    Returns a human-readable compliance report.
    """

    policy_path = _save_upload(
        policy_file
    )

    circular_path = _save_upload(
        circular_file
    )

    try:

        detailed_report = run_regtrack_pipeline(
            policy_path,
            circular_path
        )

        report = format_report(
            detailed_report
        )

        return PlainTextResponse(
            content=report,
            media_type="text/plain"
        )

    finally:

        if os.path.exists(policy_path):
            os.unlink(policy_path)

        if os.path.exists(circular_path):
            os.unlink(circular_path)


# ---------------------------------------------------------
# RBI NOTICE + COMPANY POLICY
# ---------------------------------------------------------

@router.post(
    "/analyze-notice",
    response_class=PlainTextResponse
)
async def analyze_with_rbi_notice(
    policy_file: UploadFile = File(...),

    notice_id: str = Query(
        ...,
        description="Notice id from /notices"
    ),

    pdf_url: str = Query(
        ...,
        description="PDF URL from /notices"
    )
):
    """
    Download an RBI notice and compare it
    against the uploaded company policy.
    """

    policy_path = _save_upload(
        policy_file
    )

    circular_path = None

    try:

        # Download RBI circular
        circular_path = download_circular(
            pdf_url,
            notice_id
        )

        # Run complete compliance pipeline
        detailed_report = run_regtrack_pipeline(
            policy_path,
            circular_path
        )

        # Convert detailed result into
        # human-readable report
        report = format_report(
            detailed_report
        )

        return PlainTextResponse(
            content=report,
            media_type="text/plain"
        )

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Failed to download RBI circular: {exc}"
        ) from exc

    finally:

        # Delete uploaded policy
        if os.path.exists(policy_path):
            os.unlink(policy_path)

        # Delete downloaded RBI circular
        if (
            circular_path
            and os.path.exists(circular_path)
        ):
            os.unlink(circular_path)