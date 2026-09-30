from app.security import COLLECTIONS
from app.sql_rag import extract_sql

def test_nurse_cannot_access_billing_or_equipment():
    allowed=set(COLLECTIONS["nurse"])
    assert "billing" not in allowed
    assert "equipment" not in allowed

def test_doctor_access_matches_assignment():
    assert set(COLLECTIONS["doctor"]) == {"clinical","nursing","general"}

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
