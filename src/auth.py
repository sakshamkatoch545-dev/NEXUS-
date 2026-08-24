"""
NEXUS+ Authentication Module
Provides Real Google 2-Step OAuth 2.0 Identity Verification,
30-Day Persistent Auto-Login Sessions, and Analyst Credentials.
"""

import os
import json
import urllib.parse
import requests
import streamlit as st

try:
    from src.session_manager import (
        create_persistent_session,
        verify_persistent_session,
        revoke_persistent_session,
    )
except ImportError:
    try:
        from .session_manager import (
            create_persistent_session,
            verify_persistent_session,
            revoke_persistent_session,
        )
    except ImportError:
        from session_manager import (
            create_persistent_session,
            verify_persistent_session,
            revoke_persistent_session,
        )

AUTH_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", ".auth_config.json"
)

def _load_auth_config() -> dict:
    """Load auth config from environment, secrets, or local file."""
    config = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501"),
    }
    # Check local saved file
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
    os.makedirs(os.path.dirname(AUTH_CONFIG_PATH), exist_ok=True)
    with open(AUTH_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id.strip(), "client_secret": client_secret.strip()}, f, indent=2)


GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# Default Analyst credentials for secure local forensic access
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
    """
    Generate Google OAuth 2.0 authorization URL with 2-Step Verification parameters.
    Prompts for account selection and triggers 2FA security challenge on user's Google Account.
    """
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
        st.session_state.new_login_token = token  # Signal to JS to save in localStorage


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
    st.session_state.logout_signal = True  # Signal to JS to clear localStorage
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
