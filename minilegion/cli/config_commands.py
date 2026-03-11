"""MiniLegion config sub-commands.

Commands:
    minilegion config init   — interactive setup: provider + API key env var + model
    minilegion config model  — show current model and change it interactively
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from minilegion.core.config import MiniLegionConfig, ModelCatalogEntry, load_config
from minilegion.core.exceptions import ConfigError
from minilegion.core.file_io import write_atomic
from minilegion.core.provider_health import fetch_ollama_models

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


def _load_existing_config(project_dir: Path) -> MiniLegionConfig:
    try:
        return load_config(project_dir.parent)
    except ConfigError:
        raise


def _get_catalog(
    config: MiniLegionConfig, provider: str, source: str
) -> list[ModelCatalogEntry]:
    if source == "recommended":
        return list(config.recommended_models.get(provider, []))
    if source == "all":
        return list(config.all_models.get(provider, []))
    raise ConfigError(f"Unknown model catalog source '{source}'.")


def _require_catalog(
    config: MiniLegionConfig, provider: str, source: str
) -> list[ModelCatalogEntry]:
    models = _get_catalog(config, provider, source)
    if models:
        return models
    raise ConfigError(
        f"No configured models available for provider '{provider}' in {source}_models."
    )


def _prompt_model_source() -> str:
    typer.echo(typer.style("Choose model source:", bold=True))
    source_options = [
        "Recommended models (default)",
        "All configured models",
        "Enter alias or model ID",
    ]
    source_idx = _prompt_choice("Source number", source_options)
    return ["recommended", "all", "manual"][source_idx]


def _prompt_catalog_selection(title: str, models: list[ModelCatalogEntry]) -> str:
    typer.echo(typer.style(title, bold=True))
    model_labels = [f"{entry.id}  ({entry.description})" for entry in models]
    model_idx = _prompt_choice("Model number", model_labels)
    return models[model_idx].id


def _resolve_model_input(
    config: MiniLegionConfig, provider: str, raw_value: str, allowed_model_ids: set[str]
) -> str:
    typed = raw_value.strip()
    aliases = config.model_aliases.get(provider, {})
    canonical = aliases.get(typed, typed)
    if canonical != typed:
        typer.echo(
            typer.style(
                f"Alias resolved: {typed} -> {canonical}", fg=typer.colors.GREEN
            )
        )

    if canonical not in allowed_model_ids:
        raise ConfigError(
            f"Unknown model or alias '{typed}' for provider '{provider}'."
        )

    return canonical


def _fetch_ollama_catalog(
    base_url: str | None = None,
) -> list[ModelCatalogEntry] | None:
    """Fetch installed Ollama models as a catalog. Returns None if Ollama unreachable."""
    names = fetch_ollama_models(base_url=base_url)
    if not names:
        return None
    return [
        ModelCatalogEntry(id=name, description="installed") for name in sorted(names)
    ]


def _choose_model(config: MiniLegionConfig, provider: str) -> str:
    # For Ollama: try to fetch live installed models first
    if provider == "ollama":
        live_models = _fetch_ollama_catalog(base_url=config.base_url)
        if live_models:
            typer.echo(typer.style("Installed Ollama models:", bold=True))
            labels = [f"{m.id}" for m in live_models]
            idx = _prompt_choice("Model number", labels)
            return live_models[idx].id
        else:
            typer.echo(
                typer.style(
                    "Ollama not reachable — showing default catalog (models may not be installed).",
                    fg=typer.colors.YELLOW,
                )
            )

    if not _get_catalog(config, provider, "recommended") and not _get_catalog(
        config, provider, "all"
    ):
        raise ConfigError(f"No configured models available for provider '{provider}'.")

    source = _prompt_model_source()
    if source == "recommended":
        return _prompt_catalog_selection(
            "Recommended models:", _require_catalog(config, provider, "recommended")
        )
    if source == "all":
        return _prompt_catalog_selection(
            "All configured models:", _require_catalog(config, provider, "all")
        )

    all_models = _require_catalog(config, provider, "all")
    allowed_model_ids = {entry.id for entry in all_models}
    raw_value = typer.prompt("Model alias or ID")
    return _resolve_model_input(config, provider, raw_value, allowed_model_ids)


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
        existing = _load_existing_config(project_dir)
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
    try:
        model_id = _choose_model(existing, provider)
    except ConfigError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)

    typer.echo(typer.style(f"\nSelected: {model_id}", fg=typer.colors.GREEN))

    # --- Write config ---
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
        config = _load_existing_config(project_dir)
    except ConfigError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)

    provider = config.provider
    current_model = config.model

    # Show current state
    typer.echo("")
    typer.echo(typer.style("Current configuration:", bold=True))
    typer.echo(f"  Provider : {PROVIDERS.get(provider, provider)}")
    typer.echo(f"  Model    : {typer.style(current_model, fg=typer.colors.CYAN)}")
    typer.echo("")

    try:
        model_id = _choose_model(config, provider)
    except ConfigError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)

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
