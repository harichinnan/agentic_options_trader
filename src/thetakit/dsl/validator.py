"""Cross-field semantic validation for Strategy objects.

The Pydantic schema handles shape and range validation. This module catches
strategy-level contradictions that depend on relationships between fields
(e.g., "don't use a 0.6 delta target with a CSP", "a CC needs a delta
target that makes sense for the short call side").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import ValidationError as PydanticValidationError

from thetakit.dsl.loader import StrategyLoadError, load_strategy
from thetakit.dsl.schema import Strategy, StrategyType

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ValidationIssue:
    """A single validation issue. `path` uses dotted notation (e.g., 'entry.delta_target')."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def format(self, source: str | None = None) -> str:
        prefix = f"{source}: " if source else ""
        return f"{prefix}[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationError(Exception):
    """Raised when one or more validation issues are found."""

    issues: list[ValidationIssue] = field(default_factory=list)
    source: str | None = None

    def __str__(self) -> str:  # pragma: no cover - formatting
        if not self.issues:
            return "validation failed (no issues recorded)"
        return "\n".join(i.format(self.source) for i in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def _semantic_checks(strategy: Strategy) -> list[ValidationIssue]:
    """Run semantic cross-field checks. Returns a list of issues (possibly empty)."""
    issues: list[ValidationIssue] = []
    s = strategy
    e = s.entry

    # 1. Delta target sanity per strategy type
    #    Premium-selling strategies live in the 0.10-0.40 delta band by convention.
    #    A 0.5 delta is at-the-money and defeats the purpose.
    if e.delta_target >= 0.5:
        issues.append(
            ValidationIssue(
                path="entry.delta_target",
                message=(
                    f"delta_target={e.delta_target} is at/above 0.50 which is ATM or ITM "
                    "and inconsistent with premium selling"
                ),
            )
        )

    # 2. Covered Call specific: delta_target is on the short call; > 0.40 is aggressive
    if e.strategy is StrategyType.CC and e.delta_target > 0.40:
        issues.append(
            ValidationIssue(
                path="entry.delta_target",
                message=(
                    f"covered calls with delta_target={e.delta_target} risk assignment; "
                    "0.20-0.35 is typical"
                ),
                severity="warning",
            )
        )

    # 3. Iron condor delta is per-side; should stay low
    if e.strategy is StrategyType.IRON_CONDOR and e.delta_target > 0.25:
        issues.append(
            ValidationIssue(
                path="entry.delta_target",
                message=(
                    f"iron condor with delta_target={e.delta_target} per side is aggressive; "
                    "0.10-0.20 is typical"
                ),
                severity="warning",
            )
        )

    # 4. Exit: profit_target_pct must be sensible for short-premium
    for i, ex in enumerate(s.exits):
        if ex.profit_target_pct is not None and ex.profit_target_pct >= 1.0:
            issues.append(
                ValidationIssue(
                    path=f"exits[{i}].profit_target_pct",
                    message=(
                        f"profit_target_pct={ex.profit_target_pct} means >=100% of max profit; "
                        "use a value in (0, 1), e.g., 0.5 for 50%"
                    ),
                )
            )

    # 5. Roll rule consistency: target_delta should be at or below entry delta_target
    for i, r in enumerate(s.rolls):
        if r.target_delta > e.delta_target + 0.05:
            issues.append(
                ValidationIssue(
                    path=f"rolls[{i}].target_delta",
                    message=(
                        f"roll target_delta={r.target_delta} is higher than entry "
                        f"delta_target={e.delta_target}; rolls typically reset to the "
                        "entry delta or lower"
                    ),
                    severity="warning",
                )
            )

    # 6. DTE close vs entry DTE: closing earlier than you open is fine, but warn if inverted
    for i, ex in enumerate(s.exits):
        if ex.dte_close is not None and ex.dte_close >= e.dte_target:
            issues.append(
                ValidationIssue(
                    path=f"exits[{i}].dte_close",
                    message=(
                        f"exit dte_close={ex.dte_close} >= entry dte_target={e.dte_target}; "
                        "positions would close before or at open"
                    ),
                )
            )

    # 7. Sizing: pct_bp of 1.0 means full buying power in one position — catch with warning
    if s.sizing.pct_bp is not None and s.sizing.pct_bp > 0.5:
        issues.append(
            ValidationIssue(
                path="sizing.pct_bp",
                message=(
                    f"sizing.pct_bp={s.sizing.pct_bp} allocates over 50% of buying power "
                    "to a single position"
                ),
                severity="warning",
            )
        )

    # 8. Risk: max_capital_per_symbol_pct should be <= 1.0 but also sensible
    if s.risk.max_capital_per_symbol_pct > 0.5:
        issues.append(
            ValidationIssue(
                path="risk.max_capital_per_symbol_pct",
                message=(
                    f"max_capital_per_symbol_pct={s.risk.max_capital_per_symbol_pct} "
                    "means >50% capital on a single underlying"
                ),
                severity="warning",
            )
        )

    # 9. Symbol list sanity
    if isinstance(e.symbols, list) and len(e.symbols) == 0:
        issues.append(
            ValidationIssue(
                path="entry.symbols",
                message="symbols list is empty; strategy will never open a position",
            )
        )

    return issues


def validate_strategy(
    source: str | "Path" | Strategy,
    *,
    warnings_as_errors: bool = False,
) -> Strategy:
    """Load (if needed) and validate a strategy, raising ValidationError on failure.

    Args:
        source: A path, raw YAML text, or an already-loaded Strategy.
        warnings_as_errors: if True, warnings cause a failure too.

    Returns:
        The validated Strategy.

    Raises:
        ValidationError: when schema or semantic validation fails.
        StrategyLoadError: when the input cannot be parsed at all.
    """
    if isinstance(source, Strategy):
        strategy = source
        source_label = None
    else:
        source_text = _read_source(source)
        source_label = str(source) if not _looks_like_yaml(source) else None
        try:
            strategy = load_strategy(source_text, source=source_label)
        except PydanticValidationError as e:
            issues = _pydantic_to_issues(e)
            raise ValidationError(issues=issues, source=source_label) from e
        except StrategyLoadError as e:
            raise ValidationError(
                issues=[ValidationIssue(path="<root>", message=str(e))],
                source=source_label,
            ) from e

    issues = _semantic_checks(strategy)

    if issues:
        has_errors = any(i.severity == "error" for i in issues)
        if has_errors or warnings_as_errors:
            raise ValidationError(issues=issues, source=source_label)

    return strategy


def _read_source(source: str | "Path") -> str:
    """Return YAML text from either a file path or a raw string."""
    from pathlib import Path as _Path

    if isinstance(source, _Path):
        return source.read_text(encoding="utf-8")
    # Heuristic: strings containing newlines or ':' are treated as raw YAML
    if _looks_like_yaml(source):
        return source
    p = _Path(source)
    if p.exists():
        return p.read_text(encoding="utf-8")
    # Fall back to treating as YAML content so a bad path still produces a parse error
    return source


def _looks_like_yaml(s: str | "Path") -> bool:
    if not isinstance(s, str):
        return False
    return "\n" in s or s.lstrip().startswith(("name:", "entry:", "---"))


def _pydantic_to_issues(e: PydanticValidationError) -> list[ValidationIssue]:
    """Convert a pydantic ValidationError into our ValidationIssue list with dotted paths."""
    issues: list[ValidationIssue] = []
    for err in e.errors():
        loc = ".".join(str(p) for p in err["loc"])
        issues.append(
            ValidationIssue(
                path=loc or "<root>",
                message=f"{err['msg']} (type={err['type']})",
            )
        )
    return issues
