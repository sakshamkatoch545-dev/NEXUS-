"""
NEXUS+ Authentication Module
Provides Google OAuth 2.0 Identity Authentication, Analyst Credentials, and Session Management.
"""

import os
import json
import urllib.parse
import requests
import streamlit as st

# Configuration keys
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# Default Analyst credentials for secure local forensic access
DEFAULT_ANALYSTS = {
    "analyst@nexus.forensics": {
        "name": "Lead Forensic Analyst",
        "role": "TIER-1 INVESTIGATOR",
        "password": "nexus",  # default passcode
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
    """Generate Google OAuth 2.0 authorization URL."""
    if not GOOGLE_CLIENT_ID:
        return ""
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_google_code(code: str) -> dict | None:
    """Exchange authorization code for user info via Google API."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None

    try:
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, timeout=10)
        res.raise_for_status()
        tokens = res.json()
        access_token = tokens.get("access_token")

        if not access_token:
            return None

        # Fetch user profile
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_res = requests.get(GOOGLE_USERINFO_ENDPOINT, headers=headers, timeout=10)
        userinfo_res.raise_for_status()
        return userinfo_res.json()
    except Exception as e:
        st.error(f"Google OAuth verification failed: {e}")
        return None


def init_auth_state():
    """Ensure session state variables for authentication exist."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def is_authenticated() -> bool:
    """Check if current session is authenticated."""
    init_auth_state()
    return bool(st.session_state.authenticated and st.session_state.user)


def get_current_user() -> dict:
    """Get authenticated user profile."""
    init_auth_state()
    return st.session_state.user or {}


def login_user(user_dict: dict):
    """Set authenticated user session."""
    init_auth_state()
    st.session_state.authenticated = True
    st.session_state.user = user_dict


def logout_user():
    """Clear user session and reset app state."""
    init_auth_state()
    st.session_state.authenticated = False
    st.session_state.user = None
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
        # Flexible local analyst login for any email with 3+ char password
        return {
            "name": email_clean.split("@")[0].capitalize(),
            "email": email_clean,
            "role": "VERIFIED ANALYST",
            "auth_type": "analyst",
            "avatar": "",
        }
    return None


def login_demo_google_user():
    """Instant sign-in for testing/demo when Google Cloud credentials aren't configured."""
    demo_user = {
        "name": "Google Verified Analyst",
        "email": "analyst.google@nexus.forensics",
        "role": "GOOGLE OAUTH 2.0",
        "auth_type": "google",
        "avatar": "",
    }
    login_user(demo_user)
