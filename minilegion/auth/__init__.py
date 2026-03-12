"""MiniLegion auth package.

Public API:
    login(provider)           — run OAuth flow and store credentials
    logout(provider)          — clear stored credentials
    get_token(provider)       -> str  — return usable token (refreshes if needed)
    is_authenticated(provider) -> bool
"""
