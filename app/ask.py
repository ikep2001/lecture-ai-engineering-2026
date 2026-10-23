"""第1回：Gemini API に質問する。単発質問と会話モードに対応。

単発質問（従来と同じ）:
    uv run python -m app.ask "LoRAとは何ですか？"

会話履歴を保った連続質問（宿題・実装レベル）:
    uv run python -m app.ask --chat

会話モードでは同じ Chat オブジェクトを使い続けるため、会話履歴が
次の質問に渡される。終了すると履歴は保存されない。
"""

import argparse

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def print_token_usage(response) -> None:
    """API が返したトークン数を表示する（演習 TODO に対応）。"""
    usage = response.usage_metadata
    if usage is None:
        print("[トークン数] 取得できませんでした")
        return
    input_tokens = usage.prompt_token_count
    output_tokens = usage.candidates_token_count
    print(
        f"[トークン数] 入力: {input_tokens if input_tokens is not None else '不明'}"
        f" / 出力: {output_tokens if output_tokens is not None else '不明'}"
    )


def ask(question: str) -> str:
    """従来通り、履歴を持たない単発の質問を行う。"""
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
    print_token_usage(response)
    return response.text or ""


def chat() -> None:
    """同じセッション内の履歴を利用して、複数回質問する。"""
    client = genai.Client(api_key=get_api_key())
    session = client.chats.create(model=MODEL)
    print(f"[model] {MODEL}")
    print("会話モード：質問を入力してください。終了するには「終了」または exit を入力。")

    while True:
        try:
            question = input("質問> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[会話終了]")
            return

        if question.lower() in {"exit", "quit"} or question == "終了":
            print("[会話終了]")
            return
        if not question:
            continue

        try:
            response = session.send_message(question)
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            continue

        print(f"回答> {response.text or '（テキスト応答なし）'}")
        print_token_usage(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini API に質問する")
    parser.add_argument("question", nargs="?", default=None)
    parser.add_argument(
        "--chat", action="store_true", help="会話履歴を保持し、続けて質問する"
    )
    args = parser.parse_args()

    if args.chat:
        if args.question is not None:
            parser.error("--chat と質問文の指定は併用できません")
        chat()
        return

    question = args.question or DEFAULT_QUESTION
    print(f"[model] {MODEL}")
    print(f"[質問] {question}\n")
    try:
        print(ask(question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
