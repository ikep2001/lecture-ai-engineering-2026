import json

from app import tools


def test_make_quiz_lecture_2():
    result = json.loads(tools.make_quiz(2))
    assert set(result) == {"question", "answer"}

    entries = [
        e for e in tools.load_glossary()
        if e["lecture"] == 2
    ]
    assert any(
        result["question"] == f"「{e['term']}」の意味は？"
        and result["answer"] == e["definition"]
        for e in entries
    )


def test_make_quiz_unknown_lecture():
    result = json.loads(tools.make_quiz(0))
    assert "error" in result
