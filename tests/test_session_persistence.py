import json

import pytest

from core import session
from core.session import Goal, STATE


def test_default_export_is_schema_versioned_and_json_safe():
    payload = session.export_state()

    assert payload["schema_version"] == session.STATE_SCHEMA_VERSION
    json.dumps(payload)
    assert "is_returning_session" not in payload["state"]
    assert "resume_confirmed" not in payload["state"]
    assert "restored_financial_data" not in payload["state"]
    assert "is_simulator_session" not in payload["state"]
    assert "simulator_choice" not in payload["state"]
    assert "last_simulation" not in payload["state"]


def test_populated_state_round_trip_preserves_persistent_values(tmp_path):
    plan_path = tmp_path / "plan.pdf"
    plan_path.write_bytes(b"pdf")
    STATE.risk_profile = "balanced"
    STATE.risk_answers = ["hold", "balanced growth"]
    STATE.family = {"spouse_age": 28, "children": [{"age": 4}], "dependents_count": 1}
    STATE.monthly_income = 150_000
    STATE.portfolio = {"total_value": 1_000_000, "holdings": []}
    STATE.aa_assets = {"epf": 450_000}
    STATE.additional_assets = [{"name": "PPF", "asset_type": "ppf", "value": 100_000}]
    STATE.goals = [
        Goal("Emergency fund", 600_000, 1, 1, 600_000, 200_000, 35_000, True),
        Goal("Home", 8_000_000, 8, 2, 12_000_000, 1_000_000, 55_000, False),
    ]
    STATE.gap_result = {"goal": "Home", "gap": 11_000_000}
    STATE.proposed_portfolios = {"Emergency fund": {"phases": []}}
    STATE.plan_pdf_path = str(plan_path)
    STATE.financial_snapshot_observed_at = "2026-07-26T05:00:00+00:00"
    STATE.is_returning_session = True
    STATE.resume_confirmed = True
    STATE.is_simulator_session = True
    STATE.simulator_choice = "simulator"
    STATE.last_simulation = {"event_type": "career_break"}

    exported = session.export_state()
    session.reset()
    restored = session.restore_state(exported)

    assert session.export_state() == exported
    assert all(isinstance(goal, Goal) for goal in restored.goals)
    assert [goal.name for goal in restored.goals] == ["Emergency fund", "Home"]
    assert [goal.priority for goal in restored.goals] == [1, 2]
    assert restored.goals[1].funded is False
    assert restored.is_returning_session is False
    assert restored.resume_confirmed is False
    assert restored.is_simulator_session is False
    assert restored.simulator_choice is None
    assert restored.last_simulation is None


def test_unknown_fields_are_ignored_and_missing_optional_fields_use_defaults():
    payload = {
        "schema_version": session.STATE_SCHEMA_VERSION,
        "state": {
            "name": "Rakshit",
            "age": 28,
            "future_field": "ignored",
        },
    }

    session.restore_state(payload)

    assert STATE.name == "Rakshit"
    assert STATE.risk_answers == []
    assert not hasattr(STATE, "future_field")


def test_invalid_payload_does_not_partially_mutate_state():
    STATE.risk_profile = "balanced"
    before = session.export_state()
    payload = {
        "schema_version": session.STATE_SCHEMA_VERSION,
        "state": {"name": "Changed", "goals": "not-a-list"},
    }

    with pytest.raises(ValueError):
        session.restore_state(payload)

    assert session.export_state() == before


def test_invalid_goal_field_types_are_rejected():
    payload = {
        "schema_version": session.STATE_SCHEMA_VERSION,
        "state": {
            "goals": [{
                "name": "Home",
                "target_amount_today": "not-a-number",
                "horizon_years": 8,
                "priority": 1,
                "funded": True,
            }],
        },
    }

    with pytest.raises(ValueError):
        session.restore_state(payload)


def test_reset_after_restore_clears_planning_and_transient_state():
    session.restore_state({
        "schema_version": session.STATE_SCHEMA_VERSION,
        "state": {
            "name": "Saved name",
            "age": 40,
            "risk_profile": "aggressive",
            "goals": [],
        },
    })
    STATE.is_returning_session = True
    STATE.resume_confirmed = True
    STATE.is_simulator_session = True
    STATE.simulator_choice = "simulator"
    STATE.last_simulation = {"event_type": "career_break"}

    session.reset()

    assert STATE.name == session.KYC_NAME
    assert STATE.age == session.KYC_AGE
    assert STATE.risk_profile is None
    assert STATE.is_returning_session is False
    assert STATE.resume_confirmed is False
    assert STATE.is_simulator_session is False
    assert STATE.simulator_choice is None
    assert STATE.last_simulation is None
