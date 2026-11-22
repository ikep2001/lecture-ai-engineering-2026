"""Day5 Graph融合の決定的テスト。ネットワークとAPIキーは不要。"""
from app.graph_fusion import select_pages, search_fused
from app import retrieval


def page(pid, content, hops=1):
    return {'page_id': pid, 'title': pid, 'content': content, 'hops': hops}


def test_vector_hits_never_disappear_and_graph_junk_is_dropped():
    vector = [page('p39', 'コンパクション セッション'), page('p13', 'メモリ')]
    graph = {'expanded': [page('p40', '日々のメモを選別'), page('p41', '別のSkillを解説')]}
    out = select_pages('コンパクション セッション メモリ 日々のメモ', vector, graph, max_pages=3)
    assert [p['page_id'] for p in out['results']] == ['p39', 'p13', 'p40']
    assert out['graph_added_ids'] == ['p40']
    assert 'p41' in out['graph_rejected_ids']


def test_no_unnecessary_expansion_and_cap():
    vector = [page('p52', 'LoRA QLoRA 固定 学習')]
    graph = {'expanded': [page('junk', '関係ない資料'), page('p53', 'QLoRA')]}
    out = select_pages('LoRA QLoRA 固定 学習', vector, graph, max_pages=2)
    assert out['vector_ids'] == ['p52']
    assert out['graph_added_ids'] == []


def test_embedding_search_called_once(monkeypatch):
    calls = []
    def fake_search(query):
        calls.append(('search', query))
        return [page('p13', 'メモリ')]
    def fake_graph(query, *, vector_hits):
        assert vector_hits[0]['page_id'] == 'p13'
        calls.append(('graph', query))
        return {'expanded': [page('p40', '長期メモリ')]}
    monkeypatch.setattr(retrieval, 'search', fake_search)
    monkeypatch.setattr(retrieval, 'search_graph', fake_graph)
    out = search_fused('メモリ 長期メモリ')
    assert len(calls) == 2 and calls[0][0] == 'search'
    assert out['graph_added_ids'] == ['p40']
