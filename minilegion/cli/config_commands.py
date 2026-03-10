"""MiniLegion config sub-commands.

Commands:
    minilegion config init   — interactive setup: provider + API key env var + model
    minilegion config model  — show current model and change it interactively
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from minilegion.core.config import load_config
from minilegion.core.exceptions import ConfigError
from minilegion.core.file_io import write_atomic

# ---------------------------------------------------------------------------
# Provider catalogue
# ---------------------------------------------------------------------------

# Maps provider slug → human label
PROVIDERS: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "ollama": "Ollama",
    "openai-compatible": "OpenRouter / OpenAI-compatible",
}

# Maps provider slug → default API key env var name
DEFAULT_ENV_VAR: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": "",  # No key needed for local Ollama
    "openai-compatible": "OPENROUTER_API_KEY",
}

# Maps provider slug → list of (model_id, description)
RECOMMENDED_MODELS: dict[str, list[tuple[str, str]]] = {
    "openai": [
        ("gpt-4o", "GPT-4o — fast, multimodal flagship"),
        ("gpt-4o-mini", "GPT-4o mini — cheap, fast"),
        ("o3-mini", "o3-mini — reasoning model"),
    ],
    "anthropic": [
        ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet — best balance"),
        ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku — fast, cheap"),
        ("claude-3-opus-20240229", "Claude 3 Opus — most powerful"),
    ],
    "gemini": [
        ("gemini-2.0-flash", "Gemini 2.0 Flash — fast, cheap"),
        ("gemini-2.0-pro", "Gemini 2.0 Pro — most capable"),
        ("gemini-1.5-flash", "Gemini 1.5 Flash — stable"),
    ],
    "ollama": [
        ("llama3.2", "Llama 3.2 — default local model"),
        ("mistral", "Mistral 7B — fast local model"),
        ("deepseek-r1", "DeepSeek R1 — reasoning"),
        ("qwen2.5-coder", "Qwen 2.5 Coder — coding specialist"),
    ],
    "openai-compatible": [
        ("openrouter/auto", "OpenRouter auto — cheapest available"),
        ("anthropic/claude-3.7-sonnet", "Claude 3.7 Sonnet via OpenRouter"),
        ("openai/gpt-4o-mini", "GPT-4o mini via OpenRouter"),
        ("google/gemini-2.0-flash", "Gemini 2.0 Flash via OpenRouter"),
        ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B via OpenRouter"),
    ],
}

# ---------------------------------------------------------------------------
# Sub-app
# ---------------------------------------------------------------------------

config_app = typer.Typer(
    name="config",
    help="Configure MiniLegion provider, API key and model.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_project_dir() -> Path:
    """Return project-ai/ path or raise ConfigError."""
    project_dir = Path.cwd() / "project-ai"
    if not project_dir.is_dir():
        raise ConfigError(
            "No MiniLegion project found. Run `minilegion init <name>` first."
        )
    return project_dir


def _config_path(project_dir: Path) -> Path:
    return project_dir / "minilegion.config.json"


def _prompt_choice(prompt: str, options: list[str]) -> int:
    """Display a numbered menu and return the 0-based index of the chosen item.

    Keeps prompting until a valid number is entered.
    """
    for i, opt in enumerate(options, start=1):
        typer.echo(f"  {i}. {opt}")
    while True:
        raw = typer.prompt(prompt)
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        typer.echo(
            typer.style(
                f"Please enter a number between 1 and {len(options)}.",
                fg=typer.colors.YELLOW,
            )
        )


# ---------------------------------------------------------------------------
# `config init`
# ---------------------------------------------------------------------------


@config_app.command("init")
def config_init() -> None:
    """Interactive setup: choose provider, API key env var, and model.

    Writes project-ai/minilegion.config.json.
    """
    try:
        project_dir = _find_project_dir()
    except ConfigError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)

    # --- Step 1: choose provider ---
    typer.echo("")
    typer.echo(typer.style("Select provider:", bold=True))
    provider_slugs = list(PROVIDERS.keys())
    provider_labels = [f"{PROVIDERS[s]}" for s in provider_slugs]
    provider_idx = _prompt_choice("Provider number", provider_labels)
    provider = provider_slugs[provider_idx]
    typer.echo(typer.style(f"\nSelected: {PROVIDERS[provider]}", fg=typer.colors.GREEN))

    # --- Step 2: API key env var ---
    default_env = DEFAULT_ENV_VAR[provider]
    if provider == "ollama":
        # Ollama is local — no API key needed
        api_key_env = ""
        typer.echo(
            typer.style(
                "\nOllama is local — no API key required.", fg=typer.colors.CYAN
            )
        )
    else:
        typer.echo("")
        typer.echo(typer.style("API key environment variable:", bold=True))
        typer.echo(f"  Default: {default_env}")
        raw_env = typer.prompt(
            f"Env var name (press Enter to use '{default_env}')",
            default=default_env,
        )
        api_key_env = raw_env.strip() or default_env

        # Check if the env var is already set
        if os.environ.get(api_key_env):
            typer.echo(
                typer.style(
                    f"  ✓ {api_key_env} is already set in the environment.",
                    fg=typer.colors.GREEN,
                )
            )
        else:
            typer.echo(
                typer.style(
                    f"  ! {api_key_env} is not set. Remember to export it before running.",
                    fg=typer.colors.YELLOW,
                )
            )
            typer.echo(f"    Example:  export {api_key_env}=sk-...")

    # --- Step 3: choose model ---
    typer.echo("")
    typer.echo(typer.style("Select model:", bold=True))
    models = RECOMMENDED_MODELS[provider]
    model_labels = [f"{mid}  ({desc})" for mid, desc in models]
    model_idx = _prompt_choice("Model number", model_labels)
    model_id, _ = models[model_idx]
    typer.echo(typer.style(f"\nSelected: {model_id}", fg=typer.colors.GREEN))

    # --- Write config ---
    existing = load_config(project_dir.parent)
    updated = existing.model_copy(
        update={
            "provider": provider,
            "model": model_id,
            "api_key_env": api_key_env,
        }
    )
    write_atomic(_config_path(project_dir), updated.model_dump_json(indent=2))

    typer.echo(
        typer.style(
            "\nSaved to project-ai/minilegion.config.json",
            fg=typer.colors.GREEN,
            bold=True,
        )
    )


# ---------------------------------------------------------------------------
# `config model`
# ---------------------------------------------------------------------------


@config_app.command("model")
def config_model() -> None:
    """Show the current model and interactively select a new one."""
    try:
        project_dir = _find_project_dir()
    except ConfigError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)

    config = load_config(project_dir.parent)
    provider = config.provider
    current_model = config.model

    # Show current state
    typer.echo("")
    typer.echo(typer.style("Current configuration:", bold=True))
    typer.echo(f"  Provider : {PROVIDERS.get(provider, provider)}")
    typer.echo(f"  Model    : {typer.style(current_model, fg=typer.colors.CYAN)}")
    typer.echo("")

    # Build model list for this provider
    models = RECOMMENDED_MODELS.get(provider)
    if not models:
        typer.echo(
            typer.style(
                f"No recommended model list for provider '{provider}'.",
                fg=typer.colors.YELLOW,
            )
        )
        typer.echo(
            "Edit project-ai/minilegion.config.json directly to change the model."
        )
        raise typer.Exit(code=0)

    typer.echo(typer.style("Select model:", bold=True))
    model_labels = [f"{mid}  ({desc})" for mid, desc in models]
    model_idx = _prompt_choice("Model number", model_labels)
    model_id, _ = models[model_idx]

    if model_id == current_model:
        typer.echo(typer.style("\nModel unchanged.", fg=typer.colors.CYAN))
        raise typer.Exit(code=0)

    updated = config.model_copy(update={"model": model_id})
    write_atomic(_config_path(project_dir), updated.model_dump_json(indent=2))
    typer.echo(typer.style(f"\nModel updated: {model_id}", fg=typer.colors.GREEN))
    typer.echo(
        typer.style(
            "Saved to project-ai/minilegion.config.json",
            fg=typer.colors.GREEN,
        )
    )
