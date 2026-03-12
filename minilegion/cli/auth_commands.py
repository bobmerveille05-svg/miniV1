"""MiniLegion auth sub-commands.

Commands:
    minilegion auth login <provider>   — run OAuth flow, store credentials
    minilegion auth logout <provider>  — clear stored credentials
    minilegion auth status             — show auth state for all providers
"""

from __future__ import annotations

import typer

from minilegion.auth.store import CredentialStore
from minilegion.core.exceptions import AuthError

auth_app = typer.Typer(
    name="auth",
    help="Authenticate with LLM providers.",
    no_args_is_help=True,
)

# Known providers to display in status (registry + future ones)
_STATUS_PROVIDERS = ["copilot", "anthropic", "openai"]


# ---------------------------------------------------------------------------
# Helpers (thin wrappers — easy to mock in tests)
# ---------------------------------------------------------------------------


def auth_login_provider(provider: str) -> None:
    """Run login for the given provider. Raises ValueError or AuthError."""
    from minilegion.auth.registry import get_provider

    get_provider(provider).login()


def auth_logout_provider(provider: str) -> None:
    """Run logout for the given provider."""
    from minilegion.auth.registry import get_provider

    get_provider(provider).logout()


def get_auth_status(store: CredentialStore | None = None) -> dict[str, bool]:
    """Return {provider: is_authenticated} for all known providers."""
    _store = store or CredentialStore()
    result: dict[str, bool] = {}
    for p in _STATUS_PROVIDERS:
        token = _store.load(p)
        result[p] = token is not None and not _store.is_expired(p)
    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@auth_app.command("login")
def auth_login(
    provider: str = typer.Argument(
        ..., help="Provider to authenticate with (e.g. copilot)"
    ),
) -> None:
    """Authenticate with an LLM provider using OAuth."""
    try:
        auth_login_provider(provider)
    except ValueError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
    except AuthError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@auth_app.command("logout")
def auth_logout(
    provider: str = typer.Argument(..., help="Provider to log out from (e.g. copilot)"),
) -> None:
    """Remove stored credentials for a provider."""
    try:
        auth_logout_provider(provider)
        typer.echo(typer.style(f"Logged out from {provider}.", fg=typer.colors.GREEN))
    except ValueError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@auth_app.command("status")
def auth_status() -> None:
    """Show authentication status for all known providers."""
    status = get_auth_status()
    typer.echo("")
    for provider, authenticated in status.items():
        if authenticated:
            mark = typer.style("✓ authenticated", fg=typer.colors.GREEN)
        else:
            mark = typer.style("✗ not logged in", fg=typer.colors.RED)
        typer.echo(f"  {provider:<12} {mark}")
    typer.echo("")
