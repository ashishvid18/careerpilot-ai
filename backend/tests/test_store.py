
import pytest

from app.database.store import (
    _validate_identifier,
    update_application_status,
)


@pytest.mark.parametrize(
    "value,field_name",
    [
        ("", "Session ID"),
        ("   ", "Session ID"),
        ("x" * 129, "Session ID"),
        ("valid\ninvalid", "Job ID"),
        (None, "Session ID"),
    ],
)
def test_invalid_identifiers_are_rejected(value, field_name):
    with pytest.raises(ValueError):
        _validate_identifier(value, field_name)


def test_valid_identifier_is_trimmed():
    assert _validate_identifier("  local-session  ", "Session ID") == "local-session"


def test_invalid_application_status_is_rejected():
    with pytest.raises(ValueError, match="Invalid status"):
        update_application_status(
            session_id="local-session",
            job_id="test-job",
            status="administrator",
        )


import sqlite3

from app.database import store


def test_save_and_list_application(monkeypatch, tmp_path):
    test_db = tmp_path / "test_careerpilot.db"
    monkeypatch.setattr(store, "DB_PATH", test_db)

    store.initialize_database()

    saved = store.save_application(
        session_id="test-session",
        job_id="job-123",
    )

    assert saved["created"] is True
    assert saved["status"] == "saved_demo"

    applications = store.list_applications("test-session")

    assert len(applications) == 1
    assert applications[0]["job_id"] == "job-123"


def test_duplicate_application_is_not_created(monkeypatch, tmp_path):
    test_db = tmp_path / "test_careerpilot.db"
    monkeypatch.setattr(store, "DB_PATH", test_db)

    store.initialize_database()

    first = store.save_application("test-session", "job-123")
    second = store.save_application("test-session", "job-123")

    assert first["created"] is True
    assert second["created"] is False
    assert len(store.list_applications("test-session")) == 1


def test_application_status_can_be_updated(monkeypatch, tmp_path):
    test_db = tmp_path / "test_careerpilot.db"
    monkeypatch.setattr(store, "DB_PATH", test_db)

    store.initialize_database()
    store.save_application("test-session", "job-123")

    updated = store.update_application_status(
        "test-session",
        "job-123",
        "interview",
    )

    assert updated is not None
    assert updated["status"] == "interview"


def test_invalid_status_does_not_change_application(monkeypatch, tmp_path):
    test_db = tmp_path / "test_careerpilot.db"
    monkeypatch.setattr(store, "DB_PATH", test_db)

    store.initialize_database()
    store.save_application("test-session", "job-123")

    with pytest.raises(ValueError, match="Invalid status"):
        store.update_application_status(
            "test-session",
            "job-123",
            "administrator",
        )

    applications = store.list_applications("test-session")
    assert applications[0]["status"] == "saved_demo"

