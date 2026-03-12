# Design: OAuth Authentication — `minilegion auth login <provider>`

**Date:** 2026-03-12
**Status:** Approved
**Scope:** GitHub Copilot (Device Flow) first; architecture extensible to Anthropic and OpenAI

---

## Goal

Add a `minilegion auth login <provider>` command so users can authenticate with supported LLM providers without manually creating and copying API keys. GitHub Copilot is implemented first using GitHub Device Flow OAuth (pure Python stdlib). The command structure and provider registry are designed to accept Anthropic and OpenAI providers later with zero changes to existing code.

---

## Architecture

```
minilegion/
├── auth/
│   ├── __init__.py          # exports: login, logout, get_token
│   ├── base.py              # AuthProvider abstract base class + TokenData
│   ├── store.py             # CredentialStore (~/.minilegion/credentials.json)
│   ├── registry.py          # provider name → class mapping
│   └── providers/
│       ├── __init__.py
│       └── copilot.py       # CopilotAuthProvider (GitHub Device Flow)
├── cli/
│   └── auth_commands.py     # minilegion auth login/logout/status Typer commands
```

**Data flow:**
```
CLI command
  → registry.get("copilot") → CopilotAuthProvider
  → Device Flow OAuth        → GitHub API
  → CredentialStore.save()   → ~/.minilegion/credentials.json (mode 600)
  → adapter factory reads    → CopilotAuthProvider.get_token()
```

**Key principle:** The adapter factory gains one new non-breaking code path — if provider is `"copilot"` and no `api_key_env` is set, it asks `CredentialStore` for the token instead. All existing providers are unaffected.

---

## Data Model & Credential Store

**File:** `~/.minilegion/credentials.json`
**Permissions:** `600` (owner read/write only; on Windows NTFS ACLs provide per-user isolation)

```json
{
  "copilot": {
    "access_token": "ghu_xxxxxxxxxxxx",
    "token_type": "bearer",
    "expires_at": "2026-03-12T22:00:00Z",
    "refresh_token": null,
    "scopes": ["copilot"]
  }
}
```

**`CredentialStore` methods:**
- `save(provider, token_data)` — write entry, set file permissions to `600`
- `load(provider)` — read entry, return `None` if missing
- `delete(provider)` — remove entry (used by `logout`)
- `is_expired(provider)` — check `expires_at` against `datetime.utcnow()`

**`AuthProvider` abstract base class:**
```python
class AuthProvider(ABC):
    @abstractmethod
    def login(self) -> TokenData: ...
    @abstractmethod
    def logout(self) -> None: ...
    @abstractmethod
    def get_token(self) -> str: ...
    @abstractmethod
    def is_authenticated(self) -> bool: ...
```

**`TokenData` dataclass:**
```python
@dataclass
class TokenData:
    access_token: str
    token_type: str
    expires_at: datetime | None
    refresh_token: str | None
    scopes: list[str]
```

---

## GitHub Copilot — Device Flow OAuth

Pure Python stdlib (`urllib`) — no new dependencies.

**Steps:**
1. `POST https://github.com/login/device/code` with `client_id` + `scope=copilot`
   - Returns: `device_code`, `user_code`, `verification_uri`, `expires_in`, `interval`
2. Print URL and short code to terminal
3. Poll `POST https://github.com/login/oauth/access_token` every `interval` seconds
   - `authorization_pending` → keep polling
   - `slow_down` → increase interval by 5s
   - `expired_token` → fail with message to retry
   - `access_token` → done, store credentials

**UX:**
```
$ minilegion auth login copilot

! Open this URL in your browser:
  https://github.com/login/device

! Enter this code when prompted:
  8F43-6FCF

⠋ Waiting for authorization...
✓ Authenticated as @username — GitHub Copilot access confirmed.
```

**Client ID:** Public constant in `copilot.py` (same one used by Zed, OpenCode, and other editors).

**Token expiry:** Copilot tokens expire in ~8 hours. No refresh token is issued. `get_token()` detects expiry via `is_expired()` and silently re-runs Device Flow when interactive. In non-interactive mode (piped stdout) it raises `AuthExpiredError` instead.

**Error conditions:**

| Condition | Behaviour |
|---|---|
| No internet | "Could not reach GitHub" |
| User cancels (Ctrl+C) | Graceful exit, no partial credentials saved |
| Code expires (15 min) | "Code expired — run `minilegion auth login copilot` again" |
| No Copilot subscription | "Your GitHub account does not have an active Copilot subscription" |

---

## CLI Commands

```
minilegion auth login <provider>    # runs OAuth flow, stores credentials
minilegion auth logout <provider>   # clears stored credentials
minilegion auth status              # shows auth state for all known providers
```

**`auth status` output:**
```
$ minilegion auth status

  copilot     ✓ authenticated   expires in 6h 32m   @username
  anthropic   ✗ not logged in
  openai      ✗ not logged in
```

**Wiring into Typer app** (`cli/__init__.py`):
```python
from minilegion.cli.auth_commands import auth_app
app.add_typer(auth_app, name="auth")
```

**`config init` changes:** When user selects `copilot`, skip the "enter API key env var" prompt. Print: `"Run minilegion auth login copilot to authenticate"`.

**Error when not authenticated:**
```
$ minilegion run "fix the bug"
✗ Not authenticated with GitHub Copilot.
  Run: minilegion auth login copilot
```

---

## Adapter Factory Integration

Minimal, non-breaking addition to `adapters/factory.py`:

```python
def _resolve_api_key(config):
    if config.api_key_env:
        return os.environ[config.api_key_env]   # existing path
    if config.provider == "copilot":
        from minilegion.auth import get_token
        return get_token("copilot")              # new path
    raise ConfigError("No API key configured")
```

---

## Error Hierarchy

```python
class AuthError(Exception): ...            # base
class AuthExpiredError(AuthError): ...     # token expired, re-login needed
class AuthProviderError(AuthError): ...    # OAuth flow failure
class AuthNotConfiguredError(AuthError):   # no credentials found
```

Tokens are never logged or printed after initial confirmation. Error messages never expose raw token data.

---

## Security

- `credentials.json` created with `os.chmod(path, 0o600)` immediately after first write
- On Windows: NTFS ACLs provide per-user isolation (no `chmod` call needed)
- Tokens never appear in logs, tracebacks, or error messages
- `AuthExpiredError` carries no token data

---

## Testing Strategy

| Layer | Approach |
|---|---|
| `CredentialStore` | Unit tests with `tmp_path` fixture — real file I/O, temp dir |
| `CopilotAuthProvider` | Mock `urllib` HTTP calls — happy path, `authorization_pending`, `expired_token`, `slow_down`, `access_denied` |
| `auth_commands.py` | Typer `CliRunner` tests — assert exit codes and output |
| Adapter factory | Unit test `_resolve_api_key` fallback with mocked `get_token` |

Tests live in `tests/auth/`. No integration tests hitting real GitHub — all network calls mocked.

---

## Out of Scope (Future)

- OS keychain / system credential store integration
- Token encryption at rest
- Anthropic OAuth provider
- OpenAI OAuth provider

---

## Registry Design (Extensibility)

```python
# registry.py
PROVIDERS: dict[str, type[AuthProvider]] = {
    "copilot": CopilotAuthProvider,
    # "anthropic": AnthropicAuthProvider,  # future
    # "openai": OpenAIAuthProvider,        # future
}
```

Adding a new provider = create a file in `providers/`, subclass `AuthProvider`, register in `PROVIDERS`. No changes to CLI, factory, or store.
