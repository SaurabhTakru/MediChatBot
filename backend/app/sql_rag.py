"""Restricted SQL RAG. Uses read-only SQLite and validates generated statements."""
import re, sqlite3
from pathlib import Path
from openai import OpenAI
from .config import settings

ALLOWED_TABLES = {"claims", "maintenance_tickets"}

def schema_text(conn):
    rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
    return "\n".join(f"{name}: {sql}" for name, sql in rows if name in ALLOWED_TABLES)

def extract_sql(raw: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.I | re.S)
    sql = match.group(1).strip() if match else raw.strip()
    sql = re.sub(r"^.*?(?=\b(SELECT|WITH)\b)", "", sql, flags=re.I | re.S)
    sql = sql.rstrip(";").strip()
    if not re.match(r"^(SELECT|WITH)\b", sql, re.I):
        raise ValueError("Only SELECT queries are permitted")
    if ";" in sql:
        raise ValueError("Multiple SQL statements are not permitted")
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REPLACE)\b", sql, re.I):
        raise ValueError("Unsafe SQL keyword detected")
    referenced = set(re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql, re.I))
    if not referenced or not referenced.issubset(ALLOWED_TABLES):
        raise ValueError("Query references a table outside the approved analytics schema")
    return sql

def sql_rag_chain(question: str) -> str:
    """Three explicit steps: LLM-to-SQL, clean/validate, execute and narrate."""
    if not settings.groq_api_key:
        return "SQL RAG is not configured: set GROQ_API_KEY."
    db = Path(settings.database_path).resolve()
    if not db.exists():
        return f"Analytics database not found at {db}. Configure DATABASE_PATH."
    client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1",
)
    # Open read-only to prevent any data modification.
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        schema = schema_text(conn)
        # Step 1: translate question to SQL using only inspected schema.
        raw = client.chat.completions.create(
            model=settings.groq_model, temperature=0,
            messages=[
                {"role":"system","content":"Return one read-only SQLite SELECT query only. Use only tables claims and maintenance_tickets and their actual columns. No markdown."},
                {"role":"user","content":f"Schema:\n{schema}\nQuestion: {question}"}
            ],
        ).choices[0].message.content or ""
        # Step 2: extract and validate SQL.
        sql = extract_sql(raw)
        # Step 3: execute, then ask LLM to explain returned rows.
        cursor = conn.execute(sql)
        rows = cursor.fetchmany(500)
        result = {"columns":[d[0] for d in cursor.description or []], "rows":rows}
    finally:
        conn.close()
    answer = client.chat.completions.create(
        model=settings.groq_model, temperature=0,
        messages=[
            {"role":"system","content":"Explain the SQL result accurately. Do not invent values. Mention if result is empty."},
            {"role":"user","content":f"Question: {question}\nSQL result: {result}"}
        ],
    )
    return answer.choices[0].message.content or str(result)
