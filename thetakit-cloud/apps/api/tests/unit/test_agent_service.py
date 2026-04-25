"""LangGraph rule-authoring agent tests."""

from __future__ import annotations

import pytest

from api.services.agent_service import build_graph


def _invoke(graph, inputs: dict, config: dict):
    # Walk the graph to completion (no interrupt handling needed for stubs)
    return graph.invoke(inputs, config=config)


class TestAgentGraph:
    def test_happy_path_to_save(self) -> None:
        graph = build_graph()
        config = {"configurable": {"thread_id": "test-happy"}}
        final = _invoke(
            graph,
            {
                "requirements": {"symbols": ["SPY"], "delta_target": 0.30, "dte_target": 45},
                "smoke_user_decision": "commit",
                "full_user_decision": "commit",
            },
            config,
        )
        assert final.get("saved_rule_id", "").startswith("saved-")
        assert final.get("current_yaml", "").startswith("name: drafted-rule")

    def test_abort_at_smoke(self) -> None:
        graph = build_graph()
        config = {"configurable": {"thread_id": "test-abort-smoke"}}
        final = _invoke(
            graph,
            {"requirements": {"symbols": ["SPY"]}, "smoke_user_decision": "abort"},
            config,
        )
        # Did not reach save
        assert "saved_rule_id" not in final

    def test_full_decline_returns_to_smoke_review(self) -> None:
        graph = build_graph()
        config = {"configurable": {"thread_id": "test-full-decline"}}
        final = _invoke(
            graph,
            {
                "requirements": {"symbols": ["SPY"]},
                "smoke_user_decision": "commit",
                "full_user_decision": "abort",
            },
            config,
        )
        assert "saved_rule_id" not in final
        # Still ran smoke eval
        assert final.get("smoke_eval_handle") is not None
