"""MiniLegion CLI application."""

import typer
from typing import Annotated

app = typer.Typer(
    name="minilegion",
    no_args_is_help=True,
    help="MiniLegion — AI-assisted work protocol",
)

# Global state for --verbose
state = {"verbose": False}


@app.callback()
def main(
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Enable verbose output")
    ] = False,
) -> None:
    """MiniLegion — AI-assisted work protocol."""
    if verbose:
        state["verbose"] = True


# Import commands module to register all @app.command() decorators.
# This import MUST come after app creation to avoid circular imports.
from minilegion.cli import commands  # noqa: F401, E402
