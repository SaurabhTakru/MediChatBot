from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)
USERS = {
    "dr.mehta": ("doctor", "Dr. Mehta"),
    "nurse.priya": ("nurse", "Priya"),
    "billing.ravi": ("billing_executive", "Ravi"),
    "tech.anand": ("technician", "Anand"),
    "admin.sys": ("admin", "System Admin"),
}
COLLECTIONS = {
    "doctor": ["general", "clinical"],
    "nurse": ["general", "nursing"],
    "billing_executive": ["general", "billing"],
    "technician": ["general", "equipment"],
    "admin": ["general", "clinical", "nursing", "billing", "equipment"],
}
ANALYTICAL_ROLES = {"billing_executive", "admin"}

def create_token(username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_exp_minutes)
    return jwt.encode({"sub": username, "role": role, "exp": exp}, settings.secret_key, algorithm=ALGORITHM)

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[ALGORITHM])
        username, role = payload["sub"], payload["role"]
        if username not in USERS or USERS[username][0] != role:
            raise ValueError("invalid role")
        return {"username": username, "role": role}
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired session")
