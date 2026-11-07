"""Day3: Human-in-the-loop approval demonstration.

Usage:
    uv run python -m scripts.day3_approval_cli
    uv run python -m scripts.day3_approval_cli --live
"""

import argparse
import json

from pydantic_ai import DeferredToolRequests, DeferredToolResults
from pydantic_ai.models.test import TestModel

from app.agent import agent, build_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live", action="store_true",
        help="Gemini APIを使う（省略時はTestModel）",
    )
    args = parser.parse_args()

    model = (
        build_model() if args.live
        else TestModel(call_tools=["save_learning_log"])
    )

    question = (
        "学習ログに、テーマ『Day3 AIエージェント』、"
        "内容『ツールはハーネスが実行する』を保存してください。"
    )
    result = agent.run_sync(question, model=model)

    for _ in range(3):
        if not isinstance(result.output, DeferredToolRequests):
            print("エージェントの回答:", result.output)
            return

        requests = result.output
        if requests.calls or not requests.approvals:
            raise RuntimeError("予期しない保留ツールがあります")

        approvals = {}
        for call in requests.approvals:
            if call.tool_name != "save_learning_log":
                raise RuntimeError(
                    f"想定外の承認対象: {call.tool_name}"
                )

            print("\n===== 保存前の確認 =====")
            print("ツール:", call.tool_name)
            print(json.dumps(
                call.args, ensure_ascii=False, indent=2
            ))

            try:
                answer = input(
                    "この内容を保存しますか？ [y/N]: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""

            approvals[call.tool_call_id] = answer in ("y", "yes")

        result = agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(
                approvals=approvals
            ),
            model=model,
        )

    raise RuntimeError("承認ループの上限に達しました")


if __name__ == "__main__":
    main()
