"""承認付き学習ログ保存のテスト。APIキー不要。"""

import json

import pytest
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path)
    return tmp_path


def request_save():
    model = TestModel(call_tools=["save_learning_log"])
    result = agent.run_sync("今日の学習内容を保存して", model=model)
    assert isinstance(result.output, DeferredToolRequests)
    assert len(result.output.approvals) == 1
    call = result.output.approvals[0]
    assert call.tool_name == "save_learning_log"
    return result, call, model


def test_approval_is_required(log_dir):
    result, call, model = request_save()
    assert list(log_dir.iterdir()) == []


def test_denial_does_not_save(log_dir):
    pending, call, model = request_save()
    decision = DeferredToolResults(
        approvals={call.tool_call_id: False}
    )
    agent.run_sync(
        message_history=pending.all_messages(),
        deferred_tool_results=decision,
        model=model,
    )
    assert list(log_dir.iterdir()) == []


def test_approval_saves_once(log_dir):
    pending, call, model = request_save()
    assert list(log_dir.iterdir()) == []

    decision = DeferredToolResults(
        approvals={call.tool_call_id: True}
    )
    agent.run_sync(
        message_history=pending.all_messages(),
        deferred_tool_results=decision,
        model=model,
    )

    files = list(log_dir.glob("*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert "topic" in saved
    assert "notes" in saved
    assert "created_at" in saved
