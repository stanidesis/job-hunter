"""Google Sheets integration — push jobs to a sheet for n8n / outreach workflows."""

import gspread
from google.oauth2.service_account import Credentials
from core.database import get_jobs

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Title", "Company", "Location", "Location Fit", "Work Type", "Location Note",
    "Relevance Score", "Skills", "Experience Level", "Salary",
    "Job URL", "Source", "Posted Date", "Status", "Company Domain",
]


def _get_client(creds_file: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _job_to_row(job: dict) -> list:
    return [
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("location_fit", "unknown"),
        job.get("work_type", "unknown"),
        job.get("location_note", ""),
        job.get("relevance_score", 0),
        job.get("tech_stack", ""),
        job.get("experience_level", ""),
        job.get("salary", ""),
        job.get("url", ""),
        job.get("source", ""),
        job.get("posted_date", ""),
        job.get("status", "new"),
        job.get("company_domain", ""),
    ]


def export_to_sheet(
    creds_file: str,
    spreadsheet_id: str,
    sheet_name: str = "Jobs",
    min_score: int = 0,
    location_fit: str = None,
    work_type: str = None,
    source: str = None,
    search: str = None,
    skills: str = None,
    mode: str = "replace",
) -> dict:
    """Export filtered jobs to a Google Sheet."""
    client = _get_client(creds_file)
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(HEADERS))

    jobs = get_jobs(
        min_score=min_score,
        location_fit=location_fit,
        work_type=work_type,
        source=source,
        search=search,
        skills=skills,
        limit=500,
    )

    rows = [_job_to_row(j) for j in jobs]

    if mode == "replace":
        worksheet.clear()
        worksheet.update(values=[HEADERS] + rows, range_name="A1")
    else:
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.update(values=[HEADERS], range_name="A1")
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    worksheet.format("A1:O1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.15, "green": 0.15, "blue": 0.2},
    })

    return {
        "exported": len(rows),
        "sheet_name": sheet_name,
        "spreadsheet_id": spreadsheet_id,
        "mode": mode,
    }
