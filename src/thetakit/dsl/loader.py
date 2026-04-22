"""Load and resolve strategy YAML files, including template inheritance."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from thetakit.dsl.schema import Strategy


TEMPLATES_PACKAGE = "thetakit.templates"


class StrategyLoadError(Exception):
    """Raised when a strategy file cannot be loaded or parsed."""

    def __init__(self, message: str, source: str | None = None, errors: list[Any] | None = None):
        super().__init__(message)
        self.source = source
        self.errors = errors or []


def list_templates() -> list[str]:
    """Return names of all bundled strategy templates (without .yaml suffix)."""
    try:
        files = resources.files(TEMPLATES_PACKAGE)
    except (ModuleNotFoundError, FileNotFoundError):
        return []
    return sorted(
        f.name.removesuffix(".yaml")
        for f in files.iterdir()
        if f.name.endswith(".yaml")
    )


def get_template(name: str) -> str:
    """Return raw YAML text for a bundled template by name."""
    filename = f"{name}.yaml" if not name.endswith(".yaml") else name
    try:
        return resources.files(TEMPLATES_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as e:
        available = list_templates()
        raise StrategyLoadError(
            f"template '{name}' not found. Available: {', '.join(available) or '(none)'}",
            source=filename,
        ) from e


def _load_template_dict(name: str) -> dict[str, Any]:
    """Load a template's YAML as a plain dict, without validation."""
    raw = get_template(name)
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise StrategyLoadError(
            f"template '{name}' must be a YAML mapping at the top level",
            source=f"{name}.yaml",
        )
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base. Lists and scalars in override replace base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_extends(data: dict[str, Any], _seen: set[str] | None = None) -> dict[str, Any]:
    """Recursively resolve the `extends` chain into a single flattened dict."""
    if _seen is None:
        _seen = set()

    extends = data.get("extends")
    if not extends:
        return data

    if extends in _seen:
        chain = " -> ".join([*_seen, extends])
        raise StrategyLoadError(f"circular template inheritance: {chain}")
    _seen.add(extends)

    parent = _load_template_dict(extends)
    parent = _resolve_extends(parent, _seen)

    # Child overrides parent, but strip the child's `extends` so we don't re-resolve
    child = {k: v for k, v in data.items() if k != "extends"}
    merged = _deep_merge(parent, child)
    merged.pop("extends", None)
    return merged


def load_strategy(yaml_text: str, source: str | None = None) -> Strategy:
    """Parse YAML text into a validated Strategy, resolving template inheritance.

    Args:
        yaml_text: Raw YAML source.
        source: Optional label for error messages (e.g., filename).

    Raises:
        StrategyLoadError: on YAML parse errors or inheritance resolution failures.
        pydantic.ValidationError: on schema validation failures (surfaced unwrapped
            so callers can format field-level errors with paths).
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise StrategyLoadError(f"YAML parse error: {e}", source=source) from e

    if data is None:
        raise StrategyLoadError("strategy file is empty", source=source)
    if not isinstance(data, dict):
        raise StrategyLoadError(
            "strategy file must be a YAML mapping at the top level", source=source
        )

    resolved = _resolve_extends(data)

    try:
        return Strategy.model_validate(resolved)
    except PydanticValidationError:
        # Re-raise unwrapped so CLI/MCP can format with paths
        raise


def load_strategy_file(path: str | Path) -> Strategy:
    """Load a strategy from a filesystem path."""
    p = Path(path)
    if not p.exists():
        raise StrategyLoadError(f"file not found: {p}", source=str(p))
    return load_strategy(p.read_text(encoding="utf-8"), source=str(p))
