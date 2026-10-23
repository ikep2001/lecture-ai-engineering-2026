"""第1回・実装レベル：API キー不要のモックテスト。"""

import sys
from types import SimpleNamespace

import pytest

from app import ask as subject


def fake_response(text="モデルの回答", input_tokens=9, output_tokens=4):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
        ),
    )


def test_one_shot_uses_generate_content(monkeypatch, capsys):
    """単発モードを壊していないことを確認する。"""
    called = []

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-only-not-a-real-key"
            self.models = SimpleNamespace(generate_content=self.generate)

        def generate(self, model, contents):
            called.append((model, contents))
            return fake_response("LoRAの説明")

    monkeypatch.setattr(subject.genai, "Client", FakeClient)
    monkeypatch.setattr(subject, "get_api_key", lambda: "test-only-not-a-real-key")

    assert subject.ask("LoRAとは何ですか？") == "LoRAの説明"
    assert called == [(subject.MODEL, "LoRAとは何ですか？")]
    assert "[トークン数] 入力: 9 / 出力: 4" in capsys.readouterr().out


def test_chat_reuses_one_session_for_followup(monkeypatch, capsys):
    """追質問も同一の Chat オブジェクトに送ることを確認する。"""
    created_models = []
    sent_questions = []

    class FakeSession:
        def send_message(self, question):
            sent_questions.append(question)
            return fake_response(f"第{len(sent_questions)}回答")

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-only-not-a-real-key"
            self.chats = SimpleNamespace(create=self.create)

        def create(self, model):
            created_models.append(model)
            return FakeSession()

    monkeypatch.setattr(subject.genai, "Client", FakeClient)
    monkeypatch.setattr(subject, "get_api_key", lambda: "test-only-not-a-real-key")
    questions = iter(["私の名前はAdaです", "私の名前は何ですか？", "終了"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(questions))

    subject.chat()

    assert created_models == [subject.MODEL]  # Chat オブジェクトは1度だけ作成
    assert sent_questions == ["私の名前はAdaです", "私の名前は何ですか？"]
    out = capsys.readouterr().out
    assert "回答> 第1回答" in out
    assert "回答> 第2回答" in out
    assert "[会話終了]" in out


def test_chat_ignores_empty_question_and_exit(monkeypatch):
    sent_questions = []

    class FakeClient:
        def __init__(self, api_key):
            self.chats = SimpleNamespace(
                create=lambda model: SimpleNamespace(
                    send_message=lambda question: sent_questions.append(question)
                )
            )

    monkeypatch.setattr(subject.genai, "Client", FakeClient)
    monkeypatch.setattr(subject, "get_api_key", lambda: "test-only-not-a-real-key")
    questions = iter(["", "  ", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(questions))

    subject.chat()

    assert sent_questions == []


def test_missing_usage_is_reported(capsys):
    subject.print_token_usage(SimpleNamespace(usage_metadata=None))
    assert "取得できませんでした" in capsys.readouterr().out


def test_main_without_chat_preserves_default_question(monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(subject, "ask", lambda question: seen.append(question) or "ok")
    monkeypatch.setattr(sys, "argv", ["app.ask"])

    subject.main()

    assert seen == [subject.DEFAULT_QUESTION]
    assert "ok" in capsys.readouterr().out


def test_chat_and_positional_question_rejected(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["app.ask", "--chat", "質問"])
    with pytest.raises(SystemExit) as ex:
        subject.main()
    assert ex.value.code == 2
