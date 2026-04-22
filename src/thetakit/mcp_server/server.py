"""MCP server entry point.

The MCP SDK is an optional dependency. If it's not installed, importing
this module raises a clear error. The tool implementations in
`thetakit.mcp_server.tools` are framework-neutral and can be driven
directly without the MCP runtime.
"""

from __future__ import annotations


def _require_mcp() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "The 'mcp' package is not installed. Install with:\n"
            "  pip install 'thetakit[mcp]'\n"
            "Until then, use the tool functions in thetakit.mcp_server.tools directly."
        ) from e


def build_server():
    """Build an MCP Server exposing thetakit tools. Requires the mcp package."""
    _require_mcp()
    from mcp.server import Server  # type: ignore[import-not-found]

    from thetakit.mcp_server import tools

    server = Server("thetakit")

    @server.tool()  # type: ignore[misc]
    async def validate_rule(rule_yaml: str) -> dict:
        return tools.validate_rule(rule_yaml)

    @server.tool()  # type: ignore[misc]
    async def list_templates() -> list[dict]:
        return tools.list_templates_tool()

    @server.tool()  # type: ignore[misc]
    async def get_template(name: str) -> dict:
        return {"name": name, "yaml": tools.get_template_tool(name)}

    @server.tool()  # type: ignore[misc]
    async def run_backtest(
        rule_yaml: str,
        universe: list[str],
        start: str,
        end: str,
        options: dict | None = None,
    ) -> dict:
        return tools.run_backtest_tool(rule_yaml, universe, start, end, options)

    @server.tool()  # type: ignore[misc]
    async def get_backtest_status(handle: str) -> dict:
        return tools.get_backtest_status(handle)

    @server.tool()  # type: ignore[misc]
    async def get_backtest_results(handle: str) -> dict:
        return tools.get_backtest_results(handle)

    @server.tool()  # type: ignore[misc]
    async def summarize_backtest(handle: str) -> dict:
        return tools.summarize_backtest(handle)

    @server.tool()  # type: ignore[misc]
    async def get_trade_log(
        handle: str, kind: str | None = None, symbol: str | None = None, limit: int = 500
    ) -> list[dict]:
        return tools.get_trade_log(handle, kind=kind, symbol=symbol, limit=limit)

    @server.tool()  # type: ignore[misc]
    async def get_calendar_events(
        symbols: list[str] | None, start: str, end: str, event_types: list[str] | None = None
    ) -> list[dict]:
        return tools.get_calendar_events(symbols, start, end, event_types=event_types)

    return server


def main() -> None:  # pragma: no cover
    """Run the MCP server over stdio. Invoked by `thetakit-mcp` entry point."""
    _require_mcp()
    import asyncio

    from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]

    server = build_server()

    async def _run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    main()
