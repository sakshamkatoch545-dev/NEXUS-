"""
NEXUS+ 30-Day Persistent Session Manager
Handles cryptographically signed 30-day session tokens and persistent local registry.
"""

import os
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime, timedelta

# Secret key for HMAC token signing (auto-generated or loaded from environment)
SECRET_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", ".session_secret.key")
SESSIONS_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sessions.json")


def _get_or_create_secret_key() -> bytes:
    """Retrieve or generate persistent HMAC secret key."""
    os.makedirs(os.path.dirname(SECRET_KEY_PATH), exist_ok=True)
    if os.path.exists(SECRET_KEY_PATH):
        try:
            with open(SECRET_KEY_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        except Exception:
            pass
    
    # Generate new random 256-bit key
    new_key = os.urandom(32).hex().encode("utf-8")
    with open(SECRET_KEY_PATH, "wb") as f:
        f.write(new_key)
    return new_key


SECRET_KEY = _get_or_create_secret_key()


def _load_sessions_db() -> dict:
    """Load persistent session store."""
    if not os.path.exists(SESSIONS_DB_PATH):
        return {}
    try:
        with open(SESSIONS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sessions_db(db: dict):
    """Save persistent session store safely."""
    os.makedirs(os.path.dirname(SESSIONS_DB_PATH), exist_ok=True)
    temp_path = SESSIONS_DB_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
    os.replace(temp_path, SESSIONS_DB_PATH)


def create_persistent_session(user_dict: dict, days: int = 30) -> str:
    """
    Generate a secure 30-day signed session token and persist it.
    Returns the token string to be stored in browser LocalStorage.
    """
    clean_expired_sessions()
    
    now = time.time()
    exp = now + (days * 86400)
    
    payload = {
        "email": user_dict.get("email", ""),
        "name": user_dict.get("name", "Analyst"),
        "role": user_dict.get("role", "TIER-1 INVESTIGATOR"),
        "auth_type": user_dict.get("auth_type", "analyst"),
        "avatar": user_dict.get("avatar", ""),
        "created_at": now,
        "expires_at": exp,
        "days_valid": days,
    }
    
    payload_json = json.dumps(payload, sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
    
    # Compute HMAC-SHA256 signature
    sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    
    # Store session in persistent registry
    db = _load_sessions_db()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db[token_hash] = {
        "user": user_dict,
        "created_at": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S"),
        "expires_ts": exp,
    }
    _save_sessions_db(db)
    
    return token


def verify_persistent_session(token: str) -> dict | None:
    """
    Verify a persistent session token.
    Checks signature, expiry timestamp, and presence in sessions database.
    """
    if not token or "." not in token:
        return None
    
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # Constant-time signature verification
        if not hmac.compare_digest(sig, expected_sig):
            return None
        
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
        
        # Check expiration
        now = time.time()
        if now > payload.get("expires_at", 0):
            revoke_persistent_session(token)
            return None
        
        # Verify token exists in database
        db = _load_sessions_db()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if token_hash not in db:
            return None
        
        return {
            "name": payload.get("name"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "auth_type": payload.get("auth_type"),
            "avatar": payload.get("avatar", ""),
            "is_persistent": True,
            "session_token": token,
            "days_remaining": max(0, int((payload.get("expires_at", 0) - now) / 86400)),
        }
    except Exception:
        return None


def revoke_persistent_session(token: str):
    """Revoke and delete a session token on logout."""
    if not token:
        return
    try:
        db = _load_sessions_db()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if token_hash in db:
            del db[token_hash]
            _save_sessions_db(db)
    except Exception:
        pass


def clean_expired_sessions():
    """Housekeeping to remove expired sessions."""
    try:
        db = _load_sessions_db()
        now = time.time()
        active = {k: v for k, v in db.items() if v.get("expires_ts", 0) > now}
        if len(active) != len(db):
            _save_sessions_db(active)
    except Exception:
        pass
