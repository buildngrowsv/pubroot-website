import json
from scripts.build_embeddings import build, top_k


def test_build_and_search(tmp_path):
    class Fake:
        def encode(self, texts):
            assert texts == ['Alpha\nabstract', 'Beta\n']
            return [[1, 0], [0, 1]]
    for name, papers in [('agent-index.json', [{'id': 'a', 'title': 'Alpha', 'abstract': 'abstract'}]), ('priorroot-index.json', [{'id': 'b', 'title': 'Beta'}])]:
        (tmp_path / name).write_text(json.dumps({'papers': papers}))
    data = build(tmp_path, Fake())
    assert data['dims'] == 2
    assert data['generated_at']
    path = tmp_path / 'vectors.json'
    path.write_text(json.dumps(data))
    assert top_k([1, 0], path, 1) == ['a']
    assert top_k([0, 0], path) == []
    assert top_k([1], path) == []
    assert top_k([1, 0], path, 0) == []
    assert top_k([1, 0], tmp_path / 'missing') == []


def test_invalid_vectors(tmp_path):
    import pytest
    class Fake:
        def encode(self, texts):
            return [[float('nan')]]
    for name in ('agent-index.json', 'priorroot-index.json'):
        (tmp_path / name).write_text(json.dumps({'papers': [{'id': 'a', 'title': 'A'}]}))
    with pytest.raises(ValueError):
        build(tmp_path, Fake())
