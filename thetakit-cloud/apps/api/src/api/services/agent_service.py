"""LangGraph rule-authoring session (spec 7.6).

Implements the state machine:

  gather_requirements → draft_rule → validate_rule
    (fail) ↺ draft_rule with error context
    (pass) → smoke_eval → review_smoke
      (tweaks) ↺ draft_rule
      (commit) → full_eval_prompt [INTERRUPT]
        → full_eval [INTERRUPT until complete]
        → review_full
          (tweaks) ↺ draft_rule
          (commit) → save_rule [INTERRUPT for approval]
          → end

This implementation is framework-complete (all nodes + routing) but
LLM-free: each node is a pure function that can be exercised in tests.
The LLM hooks are single functions at the top of the file (`_propose_draft`,
`_narrate_smoke`, `_narrate_full`) that default to deterministic stubs.
Production wires these to the Anthropic SDK via an injected callable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver  # type: ignore[import-not-found]
from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

from thetakit.dsl import StrategyLoadError, ValidationError, validate_strategy


# ---- State ------------------------------------------------------------------


class RuleAuthoringState(TypedDict, total=False):
    # User intent
    requirements: dict[str, Any]
    # Working rule
    current_yaml: str
    validation_errors: list[dict[str, Any]]
    # Eval handles + results
    smoke_eval_handle: str | None
    smoke_eval_summary: dict[str, Any] | None
    smoke_user_decision: Literal["tweak", "commit", "abort"] | None
    full_eval_handle: str | None
    full_eval_summary: dict[str, Any] | None
    full_user_decision: Literal["tweak", "commit", "abort"] | None
    # Meta
    iteration_count: int
    saved_rule_id: str | None
    messages: list[dict[str, str]]  # conversational log


# ---- LLM hooks (deterministic stubs; override in prod) ----------------------


DraftFn = Callable[[dict[str, Any], list[dict[str, Any]] | None], str]
NarrateFn = Callable[[dict[str, Any]], str]


def _default_draft(reqs: dict[str, Any], prior_errors: list[dict[str, Any]] | None) -> str:
    """Deterministic draft stub — produces a minimal CSP rule from requirements."""
    symbols = reqs.get("symbols", ["SPY"])
    delta = reqs.get("delta_target", 0.30)
    dte = reqs.get("dte_target", 45)
    return f"""name: drafted-rule
entry:
  strategy: CSP
  delta_target: {delta}
  dte_target: {dte}
  symbols: {symbols}
sizing:
  mode: fixed_contracts
  contracts: 1
rolls:
  - trigger: dte_threshold
    dte_threshold: 21
    target_dte: {dte}
    target_delta: {delta}
exits:
  - profit_target_pct: 0.5
"""


def _default_narrate(summary: dict[str, Any]) -> str:
    med = summary.get("return_median", 0)
    p05 = summary.get("return_p05", 0)
    dd = summary.get("drawdown_p95", 0)
    return (
        f"Median path returned {med:+.2f}%; 5th-pctile tail is {p05:+.2f}%. "
        f"Worst 5% drawdown averages {dd:.2f}%. "
        + ("Concerning tail — consider tightening." if p05 < -10 else "Tail looks acceptable.")
    )


# ---- Nodes ------------------------------------------------------------------


@dataclass
class AgentHooks:
    draft: DraftFn = field(default_factory=lambda: _default_draft)
    narrate_smoke: NarrateFn = field(default_factory=lambda: _default_narrate)
    narrate_full: NarrateFn = field(default_factory=lambda: _default_narrate)


def _append_message(state: RuleAuthoringState, role: str, content: str) -> list[dict[str, str]]:
    msgs = list(state.get("messages", []))
    msgs.append({"role": role, "content": content})
    return msgs


def build_graph(hooks: AgentHooks | None = None):
    hooks = hooks or AgentHooks()

    def gather_requirements(state: RuleAuthoringState) -> RuleAuthoringState:
        return {
            "iteration_count": 0,
            "messages": _append_message(state, "system", "Let's build your strategy together."),
        }

    def draft_rule(state: RuleAuthoringState) -> RuleAuthoringState:
        prior = state.get("validation_errors")
        yaml_text = hooks.draft(state.get("requirements", {}), prior)
        return {
            "current_yaml": yaml_text,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "messages": _append_message(
                state, "assistant", f"Drafted a rule (iteration {state.get('iteration_count', 0) + 1})."
            ),
        }

    def validate_rule_node(state: RuleAuthoringState) -> RuleAuthoringState:
        yaml_text = state.get("current_yaml", "")
        try:
            validate_strategy(yaml_text)
            return {
                "validation_errors": [],
                "messages": _append_message(state, "assistant", "Rule validates cleanly."),
            }
        except ValidationError as e:
            errors = [
                {"path": i.path, "message": i.message, "severity": i.severity}
                for i in e.issues
            ]
            return {
                "validation_errors": errors,
                "messages": _append_message(
                    state, "assistant", f"Validation failed ({len(errors)} issues). Re-drafting."
                ),
            }
        except StrategyLoadError as e:
            return {
                "validation_errors": [{"path": "<root>", "message": str(e), "severity": "error"}],
                "messages": _append_message(state, "assistant", f"Parse error: {e}"),
            }

    def smoke_eval_node(state: RuleAuthoringState) -> RuleAuthoringState:
        # Real impl: submit a smoke eval; wait for completion via checkpoint/resume.
        # For this scaffold, we stamp a stub summary so the downstream nodes have data.
        summary = {
            "return_median": 5.2, "return_p05": -3.1, "return_p95": 14.8,
            "drawdown_p95": -4.2, "cvar_05": -6.1,
        }
        return {
            "smoke_eval_handle": "stub-smoke-" + str(state.get("iteration_count", 0)),
            "smoke_eval_summary": summary,
            "messages": _append_message(state, "assistant", "Smoke eval queued."),
        }

    def review_smoke(state: RuleAuthoringState) -> RuleAuthoringState:
        summary = state.get("smoke_eval_summary", {}) or {}
        narration = hooks.narrate_smoke(summary)
        return {"messages": _append_message(state, "assistant", narration)}

    def full_eval_prompt(state: RuleAuthoringState) -> RuleAuthoringState:
        return {
            "messages": _append_message(
                state, "assistant",
                "A full eval costs 20 credits. Approve? (set full_user_decision=commit/abort)",
            )
        }

    def full_eval_node(state: RuleAuthoringState) -> RuleAuthoringState:
        summary = {
            "return_median": 4.9, "return_p05": -6.2, "return_p95": 15.1,
            "drawdown_p95": -8.0, "cvar_05": -11.4, "prob_ruin_25pct": 0.04,
            "stress_results": {"covid_crash_mar_2020": -18.0, "feb_2018_vol_spike": -5.2},
        }
        return {
            "full_eval_handle": "stub-full-" + str(state.get("iteration_count", 0)),
            "full_eval_summary": summary,
            "messages": _append_message(state, "assistant", "Full eval complete."),
        }

    def review_full(state: RuleAuthoringState) -> RuleAuthoringState:
        summary = state.get("full_eval_summary", {}) or {}
        narration = hooks.narrate_full(summary)
        return {"messages": _append_message(state, "assistant", narration)}

    def save_rule_node(state: RuleAuthoringState) -> RuleAuthoringState:
        return {
            "saved_rule_id": "saved-" + str(state.get("iteration_count", 0)),
            "messages": _append_message(state, "assistant", "Saved to your rule library."),
        }

    # ---- Routing functions -------------------------------------------------

    def route_after_validate(state: RuleAuthoringState) -> str:
        errors = state.get("validation_errors") or []
        if errors:
            if state.get("iteration_count", 0) >= 5:
                return END  # Circuit breaker
            return "draft_rule"
        return "smoke_eval"

    def route_after_review_smoke(state: RuleAuthoringState) -> str:
        decision = state.get("smoke_user_decision")
        if decision == "tweak":
            return "draft_rule"
        if decision == "commit":
            return "full_eval_prompt"
        return END

    def route_after_full_prompt(state: RuleAuthoringState) -> str:
        decision = state.get("full_user_decision")
        if decision == "commit":
            return "full_eval"
        # abort / decline → end. User can restart a session if they change their mind.
        return END

    def route_after_review_full(state: RuleAuthoringState) -> str:
        decision = state.get("full_user_decision")
        if decision == "tweak":
            return "draft_rule"
        if decision == "commit":
            return "save_rule"
        return END

    # ---- Graph --------------------------------------------------------------

    graph = StateGraph(RuleAuthoringState)
    graph.add_node("gather_requirements", gather_requirements)
    graph.add_node("draft_rule", draft_rule)
    graph.add_node("validate_rule", validate_rule_node)
    graph.add_node("smoke_eval", smoke_eval_node)
    graph.add_node("review_smoke", review_smoke)
    graph.add_node("full_eval_prompt", full_eval_prompt)
    graph.add_node("full_eval", full_eval_node)
    graph.add_node("review_full", review_full)
    graph.add_node("save_rule", save_rule_node)

    graph.set_entry_point("gather_requirements")
    graph.add_edge("gather_requirements", "draft_rule")
    graph.add_edge("draft_rule", "validate_rule")
    graph.add_conditional_edges("validate_rule", route_after_validate)
    graph.add_edge("smoke_eval", "review_smoke")
    graph.add_conditional_edges("review_smoke", route_after_review_smoke)
    graph.add_conditional_edges("full_eval_prompt", route_after_full_prompt)
    graph.add_edge("full_eval", "review_full")
    graph.add_conditional_edges("review_full", route_after_review_full)
    graph.add_edge("save_rule", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
