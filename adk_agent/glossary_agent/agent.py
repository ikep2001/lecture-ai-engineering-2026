"""Day3 Advanced: Pydantic AIと同じ読み取り系ツールをADKで使用。"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

# 比較するのは講義の演習範囲に含まれる3ツール。
# 承認付きの書き込み操作は、対応する指示とともに除外する。
READ_ONLY_INSTRUCTIONS = INSTRUCTIONS.replace(
    "- 学習ログの保存を求められたら save_learning_log を使う。\n",
    "",
)

root_agent = Agent(
    model=MODEL,
    name="glossary_agent",
    description="AIE2026の学習支援エージェント",
    instruction=READ_ONLY_INSTRUCTIONS,
    tools=[
        tools.search_glossary,
        tools.get_lecture_summary,
        tools.make_quiz,
    ],
)
