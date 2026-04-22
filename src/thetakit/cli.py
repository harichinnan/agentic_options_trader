"""thetakit CLI — typer-based entry points."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from thetakit import __version__
from thetakit.dsl import (
    StrategyLoadError,
    ValidationError,
    get_template,
    list_templates,
    validate_strategy,
)
from thetakit.mcp_server import tools as mcp_tools

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    invoke_without_command=True,
    help="thetakit — open source premium-selling backtest toolkit",
)
console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"thetakit {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Print version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    if ctx.invoked_subcommand is None and not version:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command("validate")
def validate_cmd(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Rule YAML file"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
) -> None:
    """Validate a strategy rule file. Non-zero exit on errors."""
    try:
        strategy = validate_strategy(path, warnings_as_errors=strict)
    except ValidationError as e:
        err_console.print(f"[red]✗[/red] {path}: validation failed")
        for issue in e.issues:
            colour = "red" if issue.severity == "error" else "yellow"
            err_console.print(
                f"  [{colour}]{issue.severity}[/{colour}] "
                f"[bold]{issue.path}[/bold]: {issue.message}"
            )
        raise typer.Exit(code=1) from e
    except StrategyLoadError as e:
        err_console.print(f"[red]✗[/red] {path}: {e}")
        raise typer.Exit(code=1) from e

    console.print(f"[green]✓[/green] {path}: [bold]{strategy.name}[/bold] is valid")
    console.print(
        f"  strategy={strategy.entry.strategy.value}, "
        f"delta={strategy.entry.delta_target}, dte={strategy.entry.dte_target}"
    )


@app.command("templates")
def templates_cmd() -> None:
    """List bundled strategy templates."""
    names = list_templates()
    if not names:
        console.print("[yellow]No templates bundled.[/yellow]")
        return

    table = Table(title="Bundled templates")
    table.add_column("Name", style="cyan")
    table.add_column("Strategy", style="magenta")
    table.add_column("Description")

    for name in names:
        try:
            strat = validate_strategy(get_template(name))
        except (ValidationError, StrategyLoadError) as e:  # pragma: no cover
            table.add_row(name, "?", f"[red]load error: {e}[/red]")
            continue
        desc = (strat.description or "").strip().replace("\n", " ")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        table.add_row(name, strat.entry.strategy.value, desc)

    console.print(table)


@app.command("show")
def show_cmd(
    handle_or_name: str = typer.Argument(
        ..., help="Template name (e.g., wheel) or a backtest handle"
    ),
) -> None:
    """Print a template's YAML, or a backtest summary for a handle."""
    # Try as backtest handle first
    status = mcp_tools.get_backtest_status(handle_or_name)
    if status.get("status") == "complete":
        summary = mcp_tools.summarize_backtest(handle_or_name)
        console.print(summary["summary_text"])
        return

    # Otherwise treat as template name
    try:
        yaml_text = get_template(handle_or_name)
    except StrategyLoadError as e:
        err_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1) from e
    console.print(yaml_text)


@app.command("backtest")
def backtest_cmd(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Rule YAML file"),
    universe: str = typer.Option(
        ..., "--universe", "-u", help="Comma-separated tickers (e.g., SPY,QQQ,IWM)"
    ),
    from_date: str = typer.Option(
        ..., "--from", help="Start date YYYY-MM-DD"
    ),
    to_date: str = typer.Option(
        None, "--to", help="End date YYYY-MM-DD (default: today)"
    ),
    report: Path = typer.Option(
        None, "--report", help="Write an HTML report to this path"
    ),
) -> None:
    """Run a backtest and print a summary."""
    syms = [s.strip().upper() for s in universe.split(",") if s.strip()]
    end_str = to_date or date.today().isoformat()
    yaml_text = path.read_text(encoding="utf-8")

    try:
        result = mcp_tools.run_backtest_tool(
            yaml_text, syms, from_date, end_str, options=None
        )
    except ValidationError as e:
        err_console.print(f"[red]✗[/red] validation failed before backtest:")
        for issue in e.issues:
            err_console.print(f"  [red]{issue.path}[/red]: {issue.message}")
        raise typer.Exit(code=1) from e
    except StrategyLoadError as e:
        err_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1) from e

    handle = result["handle"]
    summary = mcp_tools.summarize_backtest(handle)
    console.print(summary["summary_text"])
    console.print(f"\n[dim]handle:[/dim] [cyan]{handle}[/cyan]")

    if report is not None:
        from thetakit.mcp_server.tools import _CACHE  # noqa: PLC0415
        from thetakit.reporting.report import render_html_report

        results = _CACHE[handle]
        out = render_html_report(results, report)
        console.print(f"[green]report:[/green] {out}")


@app.command("plot")
def plot_cmd(
    handle: str = typer.Argument(..., help="Backtest handle from `thetakit backtest`"),
    output: Path = typer.Option(
        Path("equity.html"), "--output", "-o", help="Output HTML path"
    ),
    greeks: bool = typer.Option(
        False, "--greeks", help="Plot greeks over time instead of equity"
    ),
) -> None:
    """Render an interactive plot for a backtest handle."""
    from thetakit.mcp_server.tools import _CACHE  # noqa: PLC0415
    from thetakit.reporting.plots import render_equity_curve, render_greeks_over_time

    if handle not in _CACHE:
        err_console.print(
            f"[red]✗[/red] unknown handle '{handle}'. Re-run `thetakit backtest` "
            "(handles are in-memory and do not persist across CLI invocations)."
        )
        raise typer.Exit(code=1)

    results = _CACHE[handle]
    if greeks:
        path = render_greeks_over_time(results, output)
    else:
        path = render_equity_curve(results, output)
    console.print(f"[green]wrote:[/green] {path}")


if __name__ == "__main__":
    app()
