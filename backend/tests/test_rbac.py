from fastapi.testclient import TestClient

from app.security import COLLECTIONS, current_user
from app.sql_rag import extract_sql
from app.main import app, is_analytical

def test_nurse_cannot_access_billing_or_equipment():
    allowed=set(COLLECTIONS["nurse"])
    assert "billing" not in allowed
    assert "equipment" not in allowed

def test_doctor_access_matches_assignment():
    assert set(COLLECTIONS["doctor"]) == {"clinical", "general"}

def test_admin_all_collections():
    assert set(COLLECTIONS["admin"]) == {"general","clinical","nursing","billing","equipment"}

def test_sql_rejects_write():
    try:
        extract_sql("DELETE FROM claims")
        assert False
    except ValueError:
        assert True

def test_sql_rejects_unapproved_table():
    try:
        extract_sql("SELECT * FROM users")
        assert False
    except ValueError:
        assert True


def test_normal_claim_question_is_not_analytical():
    assert is_analytical("Explain the claim submission process") is False


def test_normal_total_question_is_not_analytical():
    assert is_analytical("What is the total procedure for submitting a claim?") is False


def test_claims_analytics_question_is_analytical():
    assert is_analytical("How many claims are pending?") is True


def test_maintenance_ticket_analytics_question_is_analytical():
    assert is_analytical("What is the average number of maintenance tickets?") is True


def test_nurse_analytics_question_is_forbidden():
    from app.security import ANALYTICAL_ROLES

    assert "nurse" not in ANALYTICAL_ROLES
    assert is_analytical("How many claims are pending?") is True


def test_billing_executive_analytics_question_is_allowed():
    from app.security import ANALYTICAL_ROLES

    assert "billing_executive" in ANALYTICAL_ROLES
    assert is_analytical("How many claims are pending?") is True


def test_nurse_actual_analytics_question_returns_403():
    app.dependency_overrides[current_user] = lambda: {
        "role": "nurse"
    }

    client = TestClient(app)

    try:
        response = client.post(
            "/chat",
            json={"question": "How many claims are pending?"}
        )

        assert response.status_code == 403

        data = response.json()
        assert data["detail"]["code"] == "SQL_RAG_FORBIDDEN"
        assert data["detail"]["role"] == "nurse"

    finally:
        app.dependency_overrides.clear()


def test_billing_executive_actual_analytics_question_uses_sql_rag(monkeypatch):
    app.dependency_overrides[current_user] = lambda: {
        "role": "billing_executive"
    }

    monkeypatch.setattr(
        "app.main.sql_rag_chain",
        lambda question: "Mock SQL analytics answer"
    )

    client = TestClient(app)

    try:
        response = client.post(
            "/chat",
            json={"question": "How many claims are pending?"}
        )

        assert response.status_code == 200

        data = response.json()
        assert data["retrieval_type"] == "sql_rag"
        assert data["role"] == "billing_executive"
        assert data["answer"] == "Mock SQL analytics answer"

    finally:
        app.dependency_overrides.clear()

def test_sql_schema_context_contains_real_values_and_date_ranges():
    import sqlite3
    from pathlib import Path

    from app.config import settings
    from app.sql_rag import schema_text

    db = Path(settings.database_path).resolve()
    conn = sqlite3.connect(db)

    try:
        context = schema_text(conn)

        assert "pending" in context
        assert "approved" in context
        assert "rejected" in context
        assert "submitted_date range: 2024-01-03 to 2024-12-19" in context
        assert "resolved_date range: 2024-01-06 to 2024-12-28" in context
    finally:
        conn.close()