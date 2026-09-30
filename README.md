# MediBot — Advanced RAG + RBAC

MediBot is a full-stack healthcare assistant with role-based access control (RBAC), document RAG, hybrid retrieval, reranking, and restricted SQL RAG.

## 1. Technologies

### Backend

- Python 3.11+
- FastAPI — REST API
- Uvicorn — API server
- Qdrant — vector database and hybrid retrieval
- Docling — document/PDF parsing
- FastEmbed — sparse/BM25 retrieval
- Sentence Transformers — embeddings and cross-encoder reranking
- OpenAI API — cloud LLM
- SQLite — claims and maintenance-ticket data
- JWT — authentication
- Pydantic Settings — configuration
- Pytest — testing

### Frontend

- Next.js
- React
- TypeScript
- CSS

### Infrastructure

- Docker Desktop
- Docker Compose
- Qdrant

---

## 2. Prerequisites

Install:

- Git
- Python 3.11+
- Node.js 18+
- npm
- Docker Desktop

Make sure Docker Desktop is running.

---

## 3. Clone the Repository

```bash
git clone https://github.com/SaurabhTakru/MediChatBot.git
cd medibot
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the GitHub repository URL.

---

## 4. Project Structure

```text
medibot/
├── backend/
├── frontend/
├── data/
│   ├── general/
│   ├── clinical/
│   ├── nursing/
│   ├── billing/
│   ├── equipment/
│   └── mediassist.db
├── docker-compose.yml
└── README.md
```

The supplied documents should be available under the `data` collection folders, and `mediassist.db` should be available under `data/`.

---

# Backend

## 5. Start Qdrant

From the project root:

```bash
docker compose up -d
```

Check that Qdrant is running:

```bash
docker compose ps
```

Qdrant runs on:

```text
http://localhost:6333
```

---

## 6. Backend Setup

Open a new terminal.

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## 7. Backend Environment

Open:

```text
backend/.env
```

Configure:

```env
SECRET_KEY=your-local-secret
DEMO_PASSWORD=demo123

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=mediassist_docs

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

DATABASE_PATH=../data/mediassist.db
```

Do not commit `backend/.env` to GitHub.

---

## 8. Database

Make sure the supplied database exists at:

```text
data/mediassist.db
```

The database contains:

- `claims`
- `maintenance_tickets`

SQL RAG is restricted to:

- `billing_executive`
- `admin`

---

## 9. Document Ingestion

Make sure the document folders are populated:

```text
data/
├── general/
├── clinical/
├── nursing/
├── billing/
└── equipment/
```

From the `backend` directory, run:

```bash
python ingest.py ..\data
```

This parses the documents and indexes them in Qdrant.

---

## 10. Run the Backend

From:

```text
medibot/backend
```

with the virtual environment activated:s

```bash
uvicorn app.main:app --reload --port 8000
```

Backend URL:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

Keep this terminal running.

---

## 11. Backend API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/login` | User authentication |
| POST | `/chat` | Ask MediBot a question |
| GET | `/collections/{role}` | View role collections |
| GET | `/health` | Health check |

---

# Frontend

## 12. Frontend Setup

Open a **new terminal**.

### Windows PowerShell

```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
```

### macOS / Linux

```bash
cd frontend
cp .env.local.example .env.local
npm install
```

Make sure `frontend/.env.local` contains:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 13. Run the Frontend

From:

```text
medibot/frontend
```

run:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

Open the URL in a browser.

Keep this terminal running.

---

# Running the Complete Application

Three components should be running.

### Terminal 1 — Qdrant

From the project root:

```bash
docker compose up -d
```

### Terminal 2 — Backend

```bash
cd backend
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then:

```bash
uvicorn app.main:app --reload --port 8000
```

### Terminal 3 — Frontend

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

# Demo Accounts

| Role | Username | Password |
|---|---|---|
| Doctor | `dr.mehta` | `demo123` |
| Nurse | `nurse.priya` | `demo123` |
| Billing Executive | `billing.ravi` | `demo123` |
| Technician | `tech.anand` | `demo123` |
| Admin | `admin.sys` | `demo123` |

The password can be changed using `DEMO_PASSWORD` in `backend/.env`.

---

# Role Permissions

| Role | Accessible Collections |
|---|---|
| Doctor | `general`, `clinical` |
| Nurse | `general`, `nursing` |
| Billing Executive | `general`, `billing` |
| Technician | `general`, `equipment` |
| Admin | All collections |

---

# Testing

Backend tests:

```bash
cd backend
pytest -q
```

Basic checks:

1. Open `http://localhost:8000/health`
2. Open `http://localhost:8000/docs`
3. Open `http://localhost:3000`
4. Test login with each demo account
5. Test authorized document questions
6. Test unauthorized document questions
7. Test SQL questions with `billing.ravi` and `admin.sys`

---

# Important Files

```text
backend/.env.example
frontend/.env.local.example
docker-compose.yml
backend/requirements.txt
```

Do not commit:

```text
backend/.env
frontend/.env.local
```

Do not commit API keys, passwords, or other private credentials.

---

# Stop the Application

Stop the backend and frontend with:

```text
Ctrl + C
```

Stop Qdrant from the project root:

```bash
docker compose down
```
