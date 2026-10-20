from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .security import USERS, COLLECTIONS, ANALYTICAL_ROLES, create_token, current_user
from .schemas import LoginRequest, ChatRequest, ChatResponse, Source
from .rag import retrieve_and_rerank, generate_answer
from .sql_rag import sql_rag_chain

app = FastAPI(title="MediBot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/login")
def login(body: LoginRequest):
    if body.username not in USERS or body.password != settings.demo_password:
        raise HTTPException(401, "Invalid username or password")
    role, display_name = USERS[body.username]
    return {"access_token":create_token(body.username, role), "token_type":"bearer", "role":role, "username":body.username, "display_name":display_name, "collections":COLLECTIONS[role]}

@app.get("/collections/{role}")
def collections(role: str, user=Depends(current_user)):
    if role != user["role"] and user["role"] != "admin":
        raise HTTPException(403, "You may only inspect your own role's permissions")
    if role not in COLLECTIONS:
        raise HTTPException(404, "Unknown role")
    return {"role":role, "collections":COLLECTIONS[role]}

def is_analytical(question: str) -> bool:
    question_lower = question.lower()

    analytics_terms = (
     "how many",
    "count",
    "statistics",
    "total number",
    "total count",
    "average",
    "number of",
    "percentage",
    "percent",
    "trend",
    )

    database_entities = (
        "claim",
        "claims",
        "maintenance ticket",
        "maintenance tickets",
        "maintenance_ticket",
        "maintenance_tickets",
    )

    has_analytics_intent = any(
        term in question_lower for term in analytics_terms
    )

    has_database_entity = any(
        entity in question_lower for entity in database_entities
    )

    return has_analytics_intent and has_database_entity

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user=Depends(current_user)):
    role = user["role"]
    if is_analytical(body.question):
        if role not in ANALYTICAL_ROLES:
            raise HTTPException(403, detail={"code":"SQL_RAG_FORBIDDEN","message":"SQL analytics is available only to billing executives and admins.","role":role})
        return ChatResponse(answer=sql_rag_chain(body.question), sources=[], retrieval_type="sql_rag", role=role)
    chunks = retrieve_and_rerank(body.question, role)
    answer = generate_answer(body.question, chunks)
    sources, seen = [], set()
    for c in chunks:
        p = c["payload"]
        key = (p.get("source_document",""), p.get("section_title",""), p.get("collection",""))
        if key not in seen:
            seen.add(key)
            sources.append(Source(source_document=key[0], section_title=key[1], collection=key[2]))
    return ChatResponse(answer=answer, sources=sources, retrieval_type="hybrid_rag", role=role)
