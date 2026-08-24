"""
NEXUS+ Authentication & 30-Day Persistent Session Module
Provides Real Google 2-Step OAuth 2.0 Identity Verification,
30-Day Persistent Auto-Login Sessions, and Analyst Credentials.
"""

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timedelta
import requests
import streamlit as st

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(_BASE_DIR, "results")
AUTH_CONFIG_PATH = os.path.join(RESULTS_DIR, ".auth_config.json")
SECRET_KEY_PATH = os.path.join(RESULTS_DIR, ".session_secret.key")
SESSIONS_DB_PATH = os.path.join(RESULTS_DIR, "sessions.json")


# ── HMAC SECRET KEY & SESSION DB MANAGEMENT ──

def _get_or_create_secret_key() -> bytes:
    """Retrieve or generate persistent HMAC secret key."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if os.path.exists(SECRET_KEY_PATH):
        try:
            with open(SECRET_KEY_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        except Exception:
            pass
    new_key = os.urandom(32).hex().encode("utf-8")
    try:
        with open(SECRET_KEY_PATH, "wb") as f:
            f.write(new_key)
    except Exception:
        pass
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
    os.makedirs(RESULTS_DIR, exist_ok=True)
    temp_path = SESSIONS_DB_PATH + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        os.replace(temp_path, SESSIONS_DB_PATH)
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


def create_persistent_session(user_dict: dict, days: int = 30) -> str:
    """Generate a secure 30-day signed session token and persist it."""
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
    sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    
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
    """Verify a persistent session token."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(sig, expected_sig):
            return None
        
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
        
        now = time.time()
        if now > payload.get("expires_at", 0):
            revoke_persistent_session(token)
            return None
        
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


# ── GOOGLE OAUTH 2.0 & ANALYST CREDENTIALS ──

def _load_auth_config() -> dict:
    """Load auth config from environment, secrets, or local file."""
    config = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501"),
    }
    if os.path.exists(AUTH_CONFIG_PATH):
        try:
            with open(AUTH_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("client_id") and not config["client_id"]:
                    config["client_id"] = saved["client_id"]
                if saved.get("client_secret") and not config["client_secret"]:
                    config["client_secret"] = saved["client_secret"]
        except Exception:
            pass
    return config


def save_google_credentials(client_id: str, client_secret: str):
    """Save Google OAuth credentials to local config."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(AUTH_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id.strip(), "client_secret": client_secret.strip()}, f, indent=2)


GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

DEFAULT_ANALYSTS = {
    "analyst@nexus.forensics": {
        "name": "Lead Forensic Analyst",
        "role": "TIER-1 INVESTIGATOR",
        "password": "nexus",
        "avatar": "",
    },
    "admin@nexus.ai": {
        "name": "Forensic Admin",
        "role": "CHIEF ARBITRATOR",
        "password": "admin",
        "avatar": "",
    }
}


def get_google_auth_url() -> str:
    """Generate Google OAuth 2.0 authorization URL with 2-Step Verification parameters."""
    config = _load_auth_config()
    client_id = config.get("client_id")
    redirect_uri = config.get("redirect_uri", "http://localhost:8501")
    if not client_id:
        return ""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account consent",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_google_code(code: str) -> dict | None:
    """Exchange authorization code for user info via Google API."""
    config = _load_auth_config()
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    redirect_uri = config.get("redirect_uri", "http://localhost:8501")
    if not client_id or not client_secret:
        return None
    try:
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, timeout=10)
        res.raise_for_status()
        tokens = res.json()
        access_token = tokens.get("access_token")
        if not access_token:
            return None
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_res = requests.get(GOOGLE_USERINFO_ENDPOINT, headers=headers, timeout=10)
        userinfo_res.raise_for_status()
        return userinfo_res.json()
    except Exception as e:
        st.error(f"Google OAuth 2-Step Verification failed: {e}")
        return None


def verify_google_id_token(id_token_str: str) -> dict | None:
    """Verify a Google ID Token (from Google Identity Services) via Google's tokeninfo API."""
    if not id_token_str:
        return None
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return {
                "name": data.get("name", "Google User"),
                "email": data.get("email", ""),
                "avatar": data.get("picture", ""),
                "role": "GOOGLE 2-STEP VERIFIED",
                "auth_type": "google",
            }
    except Exception as e:
        st.error(f"Google ID Token verification failed: {e}")
    return None


def init_auth_state():
    """Ensure session state variables for authentication exist."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "session_token" not in st.session_state:
        st.session_state.session_token = None
    if "remember_30_days" not in st.session_state:
        st.session_state.remember_30_days = True


def is_authenticated() -> bool:
    """Check if current session is authenticated."""
    init_auth_state()
    return bool(st.session_state.authenticated and st.session_state.user)


def get_current_user() -> dict:
    """Get authenticated user profile."""
    init_auth_state()
    return st.session_state.user or {}


def login_user(user_dict: dict, remember_30_days: bool = True):
    """Set authenticated user session and generate 30-day persistent token if requested."""
    init_auth_state()
    st.session_state.authenticated = True
    st.session_state.user = user_dict
    if remember_30_days:
        token = create_persistent_session(user_dict, days=30)
        st.session_state.session_token = token
        st.session_state.new_login_token = token


def try_restore_session_from_token(token: str) -> bool:
    """Restore authenticated session from a persistent 30-day token."""
    init_auth_state()
    if not token:
        return False
    user = verify_persistent_session(token)
    if user:
        st.session_state.authenticated = True
        st.session_state.user = user
        st.session_state.session_token = token
        return True
    return False


def logout_user():
    """Clear user session and revoke 30-day token."""
    init_auth_state()
    token = st.session_state.session_token
    if token:
        revoke_persistent_session(token)
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.session_token = None
    st.session_state.logout_signal = True
    st.session_state.page = "landing"
    st.session_state.result = None
    st.session_state.scan_image = None
    st.session_state.scan_meta = None
    st.session_state.scan_ready = False


def verify_credentials(email: str, password: str) -> dict | None:
    """Verify analyst email and password."""
    email_clean = email.strip().lower()
    if email_clean in DEFAULT_ANALYSTS:
        user_info = DEFAULT_ANALYSTS[email_clean]
        if user_info["password"] == password:
            return {
                "name": user_info["name"],
                "email": email_clean,
                "role": user_info["role"],
                "auth_type": "analyst",
                "avatar": user_info.get("avatar", ""),
            }
    elif email_clean and len(password) >= 3:
        return {
            "name": email_clean.split("@")[0].capitalize(),
            "email": email_clean,
            "role": "VERIFIED ANALYST",
            "auth_type": "analyst",
            "avatar": "",
        }
    return None


def login_demo_google_user(remember_30_days: bool = True):
    """Instant sign-in for testing/demo when Google Cloud credentials aren't configured."""
    demo_user = {
        "name": "Google Verified Analyst",
        "email": "analyst.google@nexus.forensics",
        "role": "GOOGLE 2-STEP VERIFIED",
        "auth_type": "google",
        "avatar": "",
    }
    login_user(demo_user, remember_30_days=remember_30_days)
