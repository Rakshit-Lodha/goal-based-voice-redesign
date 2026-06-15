import json

from core.run_transcript import RunTranscriptRecorder


def test_run_transcript_saves_messages_and_tool_calls(tmp_path):
    recorder = RunTranscriptRecorder(output_dir=str(tmp_path))

    recorder.add_user_transcript("I want to plan retirement.")
    recorder.start_assistant_response()
    recorder.add_assistant_text("Sure, ")
    recorder.add_assistant_text("let's do that.")
    recorder.end_assistant_response()
    recorder.add_tool_call("add_goal", {"name": "Retirement", "priority": 1})
    recorder.add_tool_result("add_goal", {"progress": {"goals": True}})

    path = recorder.save_once()
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    assert [event["type"] for event in payload["events"]] == [
        "message",
        "message",
        "tool_call",
        "tool_result",
    ]
    assert payload["events"][0]["role"] == "user"
    assert payload["events"][0]["text"] == "I want to plan retirement."
    assert payload["events"][1]["role"] == "assistant"
    assert payload["events"][1]["text"] == "Sure, let's do that."
    assert payload["events"][2]["name"] == "add_goal"
    assert payload["events"][2]["arguments"]["name"] == "Retirement"
    assert payload["events"][3]["result"]["progress"]["goals"] is True
    assert recorder.save_once() == path
