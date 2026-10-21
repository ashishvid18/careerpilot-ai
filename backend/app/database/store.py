
import sqlite3
from pathlib import Path

from streamlit import status


DB_PATH = Path(__file__).resolve().parents[2] / "careerpilot.db"


def _validate_identifier(value: str, field_name: str) -> str:
    """Validate identifiers used by application records."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} is required.")

    if len(value) > 128:
        raise ValueError(f"{field_name} must be 128 characters or fewer.")

    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{field_name} contains invalid characters.")

    return value


def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'saved_demo',
                submission_reference TEXT,
                UNIQUE(session_id, job_id)
            )
            """
        )
        conn.commit()


def save_application(
    session_id: str,
    job_id: str,
    status: str = "saved_demo",
) -> dict:
    """Save an application record without creating duplicates."""
    session_id = _validate_identifier(session_id, "Session ID")
    job_id = _validate_identifier(job_id, "Job ID")


    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO applications
                (session_id, job_id, status)
            VALUES (?, ?, ?)
            """,
            (session_id, job_id, status),
        )
        conn.commit()

        created = cursor.rowcount == 1

        row = conn.execute(
            """
            SELECT id, session_id, job_id, applied_at,
                   status, submission_reference
            FROM applications
            WHERE session_id = ? AND job_id = ?
            """,
            (session_id, job_id),
        ).fetchone()

        if row is None:
            raise RuntimeError("Could not retrieve the saved application.")

        result = dict(row)
        result["created"] = created
        return result


def list_applications(session_id: str) -> list[dict]:
    """Return saved applications for one session."""
    session_id = _validate_identifier(session_id, "Session ID")


    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT id, session_id, job_id, applied_at,
                   status, submission_reference
            FROM applications
            WHERE session_id = ?
            ORDER BY applied_at DESC, id DESC
            """,
            (session_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def update_application_status(
    session_id: str,
    job_id: str,
    status: str,
) -> dict | None:
    """Update the status of an existing application record."""
    session_id = _validate_identifier(session_id, "Session ID")
    job_id = _validate_identifier(job_id, "Job ID")

    if not isinstance(status, str):
        raise ValueError("Status must be a string.")

    status = status.strip()

    allowed_statuses = {
        "saved_demo",
        "submitted",
        "under_review",
        "interview",
        "rejected",
        "offer",
        "withdrawn",
    }

    if status not in allowed_statuses:
        raise ValueError(
            f"Invalid status. Allowed values: {', '.join(sorted(allowed_statuses))}"
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute(
            """
            UPDATE applications
            SET status = ?
            WHERE session_id = ? AND job_id = ?
            """,
            (status, session_id, job_id),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT id, session_id, job_id, applied_at,
                   status, submission_reference
            FROM applications
            WHERE session_id = ? AND job_id = ?
            """,
            (session_id, job_id),
        ).fetchone()

    return dict(row) if row else None
