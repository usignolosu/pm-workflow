#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retrieve.py — 混合检索（向量 + 关键词）+ rerank

P0 骨架：本地 JSON 库做余弦相似（向量）+ 关键词命中（BM25-lite）融合，
bge-reranker 在生产环境接入。复杂模式可叠加图谱关联查询（见 build_graph）。

用法：
  python3 retrieve.py --kb ./.kb --query "登录功能怎么做"
  python3 retrieve.py --kb ./.kb --query "登录" --topk 5 --verbose
"""
import argparse
import json
import math
import os
import re
import sys

_stop = set("的 了 和 与 及 在 是 我 你 他 它 这 那 有 个 们 也 都 就 而 并 等 中 为 对 从 把 被 让 a an the of to and or is are".split())


def segment(text: str):
    toks = []
    for w in re.findall(r"[a-z0-9_]{2,}", text.lower()):
        if w not in _stop:
            toks.append(w)
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        if seg in _stop:
            continue
        for i in range(len(seg) - 1):
            toks.append(seg[i:i + 2])
        if len(seg) == 1:
            toks.append(seg)
    return toks


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def kw_score(query, text):
    q = set(segment(query))
    t = segment(text)
    if not q:
        return 0.0
    return sum(1 for w in t if w in q) / math.sqrt(len(t) or 1)


def retrieve(kb_dir: str, query: str, topk: int = 3, verbose: bool = False):
    path = os.path.join(kb_dir, "index.json")
    if not os.path.exists(path):
        print(f"[warn] 未找到 {path}，请先运行 ingest.py", file=sys.stderr)
        return []
    index = json.load(open(path, encoding="utf-8"))
    docs = index["docs"]
    # 查询伪向量
    import hashlib
    dim = index.get("dim", 256)
    qvec = [0.0] * dim
    for w in segment(query):
        h = int(hashlib.md5(w.encode()).hexdigest(), 16) % dim
        qvec[h] += 1.0
    norm = sum(v * v for v in qvec) ** 0.5 or 1.0
    qvec = [v / norm for v in qvec]

    scored = []
    for d in docs:
        vs = cosine(qvec, d["vec"]) if d.get("vec") else 0.0
        ks = kw_score(query, d["text"])
        fused = 0.5 * vs + 0.5 * ks  # 混合检索融合（生产中加 bge-reranker）
        scored.append((fused, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:topk]
    for score, d in top:
        print(f"\n[{score:.3f}] {d['source']} ({d['id']})")
        snippet = d["text"][:200]
        print(snippet + ("…" if len(d["text"]) > 200 else ""))
        if verbose:
            print(f"  向量分={cosine(qvec, d['vec']):.3f} 关键词分={kw_score(query, d['text']):.3f}")
    return top


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", required=True, help="向量库目录(.kb)")
    ap.add_argument("--query", required=True)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    retrieve(args.kb, args.query, args.topk, args.verbose)


if __name__ == "__main__":
    main()
