"""Day5 発展: ベクトル検索を保持し、Graph の追加候補を質問語の新規カバーで選ぶ。

検索上位ページの欠落を防ぎ、説明できる選別規則で過剰取得を抑える。
「質問語を空白区切りのキーワードで渡す」ことを前提とした簡易法。
"""
import re
from app import retrieval


def query_terms(query: str) -> set[str]:
    """日本語・英語のキーワードを抽出する。形態素解析は行わない。"""
    return {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+_.-]*|[一-龯々ぁ-んァ-ンー]+", query)
        if len(word) >= 2
    }


def matched_terms(page: dict, terms: set[str]) -> set[str]:
    text = f"{page.get('title', '')} {page.get('content', '')}".casefold()
    return {term for term in terms if term in text}


def select_pages(query: str, vector_hits: list[dict], graph: dict, max_pages: int = 7) -> dict:
    """ベクトル上位を必ず保持し、未カバーの質問語を補う候補だけ選択する。"""
    terms = query_terms(query)
    base = [{**p, 'source': 'vector'} for p in vector_hits]
    ids = {p['page_id'] for p in base}
    covered = set().union(*(matched_terms(p, terms) for p in base)) if base else set()
    candidates = {p['page_id']: p for p in graph.get('expanded', []) if p['page_id'] not in ids}
    added = []
    remaining = max(0, max_pages - len(base))

    while len(added) < remaining and candidates:
        # 最も多くの「まだ見つかっていない質問語」を補うページを優先する。
        # 同点なら質問語の総数、hop数、IDで決め、順序を再現可能にする。
        ranked = sorted(
            candidates.values(),
            key=lambda p: (
                -len(matched_terms(p, terms) - covered),
                -len(matched_terms(p, terms)),
                p.get('hops', 999),
                p['page_id'],
            ),
        )
        best = ranked[0]
        new_terms = matched_terms(best, terms) - covered
        if not new_terms:
            break
        added.append({**best, 'source': 'graph', 'new_query_terms': sorted(new_terms)})
        ids.add(best['page_id'])
        covered.update(new_terms)
        candidates.pop(best['page_id'])

    return {
        'results': base + added,
        'vector_ids': [p['page_id'] for p in vector_hits],
        'graph_added_ids': [p['page_id'] for p in added],
        'graph_rejected_ids': sorted(candidates),
        'query_terms': sorted(terms),
        'max_pages': max_pages,
    }


def search_fused(query: str) -> dict:
    """質問の埋め込みは1回だけ取得し、Graph用に検索結果を再利用する。"""
    vector_hits = retrieval.search(query)
    graph = retrieval.search_graph(query, vector_hits=vector_hits)
    return select_pages(query, vector_hits, graph)
