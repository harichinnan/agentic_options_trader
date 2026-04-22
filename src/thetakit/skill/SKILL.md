# thetakit conversational skill

This skill teaches an MCP host how to sequence thetakit tools to help a
premium-selling trader author, validate, and backtest a strategy.

## When to invoke

The user asks you to:
- validate or fix a rule file
- backtest a strategy (bundled template or their own YAML)
- compare two rule variants
- explain why a rule failed validation

## Typical flow

1. **Validate first.** If the user mentions editing or writing a rule, call
   `validate_rule(rule_yaml)` before suggesting edits. If errors come back,
   report them with paths and quote the offending YAML lines.
2. **Offer templates.** When a user says "I want to try the Wheel" or
   "give me a covered call on SPY", call `list_templates()` and pick the
   best match. Show the template YAML (via `get_template`) before
   running anything — the user should see exactly what's being tested.
3. **Backtest.** Call `run_backtest(rule_yaml, universe, start, end)` with
   a sensible default window (last 3 years if the user does not specify).
   The tool returns a `handle` synchronously in Phase 1.
4. **Summarize.** Always follow up with `summarize_backtest(handle)`. The
   `summary_text` field is written for LLM consumption — quote it back
   directly and add one sentence of context.
5. **Drill down if asked.** Use `get_trade_log(handle, kind='close')` or
   filter by symbol when the user wants specifics.
6. **Calendar context.** For questions like "did this strategy stand up
   around FOMC?" call `get_calendar_events` and correlate dates against
   `get_trade_log`.

## Do not

- Invent backtest numbers. Always call the tool.
- Suggest changes without running `validate_rule` first.
- Present backtest returns as forecasts — these are historical simulations,
  not predictions.
- Recommend rule tweaks that weren't backtested in the same conversation.

## Caveats to surface

If a user runs a backtest and the total return is implausibly high (e.g.,
over 50% annualized for a premium-selling strategy), flag it as likely
caused by the synthetic data adapter used when vendor credentials are not
configured, and suggest re-running with a real data adapter.
