"""Optional local embeddings. Install scripts/requirements_embeddings.txt, then run this file."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
ROOT = Path(__file__).resolve().parents[1]


def build(root, embedder):
    papers = {}
    for name in ('agent-index.json', 'priorroot-index.json'):
        for paper in json.loads((root / name).read_text())['papers']:
            papers[paper['id']] = paper
    ids = sorted(papers)
    vectors = embedder.encode([papers[i]['title'] + '\n' + papers[i].get('abstract', '') for i in ids]) if ids else []
    vectors = [[float(x) for x in vector] for vector in vectors]
    if len(vectors) != len(ids) or any(not v or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Invalid embedding output')
    dims = len(vectors[0]) if vectors else 0
    if any(len(v) != dims for v in vectors):
        raise ValueError('Inconsistent dimensions')
    return dict(model=MODEL, dims=dims, generated_at=datetime.now(timezone.utc).isoformat(), papers=dict(zip(ids, vectors)))


def top_k(vector, path=ROOT / '_data/embeddings.json', k=5):
    """Return closest paper IDs; missing optional data returns no candidates."""
    if not Path(path).exists() or k <= 0:
        return []
    data = json.loads(Path(path).read_text())
    norm = math.sqrt(sum(x*x for x in vector))
    if not norm:
        return []
    scores = []
    for pid, other in data['papers'].items():
        if len(other) != len(vector):
            continue
        denominator = norm * math.sqrt(sum(x*x for x in other))
        if denominator:
            scores.append((sum(x*y for x, y in zip(vector, other))/denominator, pid))
    return [pid for _, pid in sorted(scores, key=lambda item: (-item[0], item[1]))[:k]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    from sentence_transformers import SentenceTransformer
    data = build(args.root, SentenceTransformer(MODEL, device='cpu'))
    output = args.root / '_data/embeddings.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
