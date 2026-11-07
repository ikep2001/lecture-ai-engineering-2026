"""Day3 Advanced: Google ADK tool-call trace."""

import asyncio
import json

from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_agent.glossary_agent.agent import root_agent


QUESTIONS = [
    "AIE2026の講座の宿題にある「3レベル」とは何ですか？",
    "LoRAとQLoRAの違いは？",
]


async def main():
    app = App(name="glossary_compare", root_agent=root_agent)
    runner = InMemoryRunner(app=app)

    try:
        for number, question in enumerate(QUESTIONS, 1):
            session = await runner.session_service.create_session(
                app_name=app.name,
                user_id="day3_comparison",
            )

            calls = []
            returns = []

            print(f"\n===== QUESTION {number} =====")
            print(question)

            async for event in runner.run_async(
                user_id="day3_comparison",
                session_id=session.id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=question)],
                ),
            ):
                if not event.content:
                    continue

                for part in event.content.parts or []:
                    if part.function_call:
                        call = part.function_call
                        calls.append(call.name)
                        print(
                            "[tool call]",
                            call.name,
                            json.dumps(
                                call.args,
                                ensure_ascii=False,
                                default=str,
                            ),
                        )

                    if part.function_response:
                        response = part.function_response
                        returns.append(response.name)
                        print(
                            "[tool return]",
                            response.name,
                            str(response.response)[:400],
                        )

                    if part.text:
                        print("[response]", part.text)

            print("[summary] tool_calls =", len(calls))
            print("[summary] tool_returns =", len(returns))

            assert calls, "No tool calls recorded"
            assert len(calls) == len(returns), (
                "Tool call/return mismatch"
            )

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
