"""第3回: エージェントに持たせるツール。

ここに書いた関数の docstring と型ヒントが、そのままモデルへの「ツールの説明文」になる。
説明文を書き換えると、モデルがツールを使うかどうか・どんな引数で呼ぶかが変わる。
"""

import json
from datetime import datetime, timezone
from uuid import uuid4
import random
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_RESULTS = 3


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """講座の用語集から用語を検索し、定義と、どの回で扱うかを返す。

    AIエンジニアリングの用語や、この講座（AIE2026）に固有の言葉について
    答える前に使うこと。query には調べたい用語を1つだけ入れる（例: "LoRA"）。
    """
    q = _normalize(query)
    if not q:
        return "検索語が空です。調べたい用語を1つ指定してください。"
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # 「r」のような短い別名が何にでも当たらないよう、名前側が短いものは除く
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"用語集に「{query}」は見つかりませんでした。"
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """指定した回（1始まりの整数）の講義の要点を返す。

    「第3回では何を学ぶ？」のように、回の内容や関係を聞かれたときに使う。
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"第{lecture}回の要点はまだありません。用意されている回: {', '.join(available)}"
    return path.read_text(encoding="utf-8")

def make_quiz(lecture: int) -> str:
    """指定した回の用語から確認問題と解答を1問返す。

    「第2回の確認問題を出して」のように、
    講義内容の復習問題を求められたときに使う。
    lecture には講義の回番号を指定する。
    """
    entries = [
        e for e in load_glossary()
        if e["lecture"] == lecture
    ]
    if not entries:
        return json.dumps(
            {"error": f"第{lecture}回の用語がありません。"},
            ensure_ascii=False,
        )

    entry = random.choice(entries)
    return json.dumps(
        {
            "question": f"「{entry['term']}」の意味は？",
            "answer": entry["definition"],
        },
        ensure_ascii=False,
    )


# 個人の学習ログ。リポジトリの .gitignore で共有対象から除外。
LEARNING_LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"


def save_learning_log(topic: str, notes: str) -> str:
    """学習した内容をローカルの learning_log/ に保存する。

    学習内容の記録・保存を利用者が求めたときに使う。
    ファイルの書き込みを伴うため、実行前に承認が必要。
    topic は学習テーマ、notes は学習内容。
    """
    now = datetime.now(timezone.utc)
    record = {
        "topic": topic,
        "notes": notes,
        "created_at": now.isoformat(),
    }

    LEARNING_LOG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{now:%Y%m%dT%H%M%S}_{uuid4().hex[:12]}.json"
    path = LEARNING_LOG_DIR / name

    # 同名ファイルを上書きしない
    with path.open("x", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return f"学習ログを保存しました: {name}"
