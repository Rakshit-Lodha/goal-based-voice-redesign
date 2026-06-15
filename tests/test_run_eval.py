from core.run_eval import evaluate_transcript


def _message(role, text="ok"):
    return {"type": "message", "role": role, "text": text}


def _tool_call(name, arguments=None):
    return {"type": "tool_call", "name": name, "arguments": arguments or {}}


def _tool_result(name, result=None):
    return {"type": "tool_result", "name": name, "result": result or {}}


def test_run_eval_passes_valid_transcript_contract():
    transcript = {
        "events": [
            _message("assistant"),
            _message("user"),
            _tool_call("assess_risk_profile"),
            _tool_result("assess_risk_profile"),
            _tool_call("add_family"),
            _tool_result("add_family"),
            _tool_call(
                "pull_mf_central",
                {"user_confirmed_consent": True, "consent_context": "User agreed."},
            ),
            _tool_result("pull_mf_central"),
            _tool_call(
                "pull_account_aggregator",
                {"user_confirmed_consent": True, "consent_context": "User agreed."},
            ),
            _tool_result("pull_account_aggregator"),
            _tool_call("confirm_financial_snapshot"),
            _tool_result("confirm_financial_snapshot", {"financial_snapshot_confirmed": True}),
            _tool_call("add_goal"),
            _tool_result("add_goal"),
            _tool_call("project_existing_corpus"),
            _tool_result("project_existing_corpus"),
            _tool_call("compute_gap_and_sip"),
            _tool_result("compute_gap_and_sip"),
            _tool_call("build_goal_portfolio"),
            _tool_result("build_goal_portfolio"),
            _tool_call("generate_plan_pdf"),
            _tool_result("generate_plan_pdf", {"url": "/output/plan.pdf"}),
        ]
    }

    result = evaluate_transcript(transcript)

    assert result.passed is True
    assert all(check.passed for check in result.checks)


def test_run_eval_fails_when_goal_starts_before_financial_confirmation():
    transcript = {
        "events": [
            _message("assistant"),
            _message("user"),
            _tool_call("add_goal"),
            _tool_result("add_goal"),
            _tool_call("generate_plan_pdf"),
            _tool_result("generate_plan_pdf", {"url": "/output/plan.pdf"}),
        ]
    }

    result = evaluate_transcript(transcript)

    assert result.passed is False
    failed = {check.name for check in result.checks if not check.passed}
    assert "financial_snapshot_confirmed_before_goals" in failed


def test_run_eval_fails_when_provider_pull_order_is_invalid():
    transcript = {
        "events": [
            _message("assistant"),
            _message("user"),
            _tool_call(
                "pull_account_aggregator",
                {"user_confirmed_consent": True, "consent_context": "User agreed."},
            ),
            _tool_result("pull_account_aggregator"),
            _tool_call("generate_plan_pdf"),
            _tool_result("generate_plan_pdf", {"url": "/output/plan.pdf"}),
        ]
    }

    result = evaluate_transcript(transcript)

    failed = {check.name for check in result.checks if not check.passed}
    assert "tool_order_is_allowed" in failed
