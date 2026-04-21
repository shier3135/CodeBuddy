from codex_buddy.events import ApprovalRequest, AgentOutput, TokenUsage, TurnState
from codex_buddy.reducer import BuddyStateReducer


def test_turn_lifecycle_and_entries_are_projected_into_snapshot():
    reducer = BuddyStateReducer()

    reducer.apply(TurnState(thread_id="thr_1", turn_id="turn_1", active=True))
    reducer.apply(AgentOutput(thread_id="thr_1", text="Thinking about tests"))
    reducer.apply(TokenUsage(thread_id="thr_1", total_tokens=120, tokens_today=45))

    snapshot = reducer.snapshot()

    assert snapshot.total == 1
    assert snapshot.running == 1
    assert snapshot.waiting == 0
    assert snapshot.msg == "Thinking about tests"
    assert snapshot.entries == ["Thinking about tests"]
    assert snapshot.tokens == 120
    assert snapshot.tokens_today == 45

    reducer.apply(TurnState(thread_id="thr_1", turn_id="turn_1", active=False))

    stopped = reducer.snapshot()

    assert stopped.running == 0
    assert stopped.total == 0


def test_approval_request_populates_prompt_and_waiting_state():
    reducer = BuddyStateReducer()

    reducer.apply(TurnState(thread_id="thr_1", turn_id="turn_1", active=True))
    reducer.apply(
        ApprovalRequest(
            thread_id="thr_1",
            turn_id="turn_1",
            request_id="req_1",
            command="rm -rf /tmp/foo",
            cwd="/tmp/project",
            reason="Needs approval",
        )
    )

    snapshot = reducer.snapshot()

    assert snapshot.running == 0
    assert snapshot.waiting == 1
    assert snapshot.msg == "approve: rm -rf /tmp/foo"
    assert snapshot.prompt == {
        "id": "req_1",
        "tool": "Bash",
        "hint": "rm -rf /tmp/foo",
    }

    reducer.resolve_approval("req_1")

    resolved = reducer.snapshot()

    assert resolved.waiting == 0
    assert resolved.running == 1
    assert resolved.prompt is None


def test_approval_request_clips_cjk_prompt_hint_by_display_width():
    reducer = BuddyStateReducer()
    command = "你" * 25

    reducer.apply(TurnState(thread_id="thr_1", turn_id="turn_1", active=True))
    reducer.apply(
        ApprovalRequest(
            thread_id="thr_1",
            turn_id="turn_1",
            request_id="req_1",
            command=command,
            cwd="/tmp/project",
            reason="Needs approval",
        )
    )

    snapshot = reducer.snapshot()

    assert snapshot.prompt == {
        "id": "req_1",
        "tool": "Bash",
        "hint": command,
    }


def test_reducer_clips_cjk_entries_by_display_width():
    reducer = BuddyStateReducer()

    reducer.apply(TurnState(thread_id="thr_1", turn_id="turn_1", active=True))
    reducer.apply(AgentOutput(thread_id="thr_1", text="你" * 50))

    snapshot = reducer.snapshot()

    assert snapshot.msg == ("你" * 21) + "…"
    assert snapshot.entries == ["你" * 50]
