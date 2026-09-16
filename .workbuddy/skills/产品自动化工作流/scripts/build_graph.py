#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_graph.py — 实体关系抽取 → 知识图谱（本地 JSON 图，后端可插拔）

P0 骨架：基于 ingest 后的文本片段做"共现"式实体-关系抽取（轻量、零依赖）。
生产环境可替换为 Kuzu（可嵌入图库）或 LightRAG（轻量 GraphRAG），
用 LLM 抽取更精准的实体关系。

用法：
  python3 build_graph.py --kb ./.kb --out ./.kb/graph.json
"""
import argparse
import json
import os
import re

# 简单实体识别：连续中文词(2-6字)或英文词组，作为候选实体
ENTITY_RE = re.compile(r"[\u4e00-\u9fff]{2,6}|[A-Za-z][A-Za-z0-9_]{2,}")


def extract_entities(text: str):
    cands = ENTITY_RE.findall(text)
    # 过滤停用/泛化词
    stop = {"功能", "用户", "系统", "页面", "我们", "需要", "通过", "可以", "进行", "使用", "支持", "提供", "包括", "以下", "一个", "这个", "以及", "并且", "如果", "然后", "基于", "相关", "目前", "未来", "其他", "整体", "流程", "场景", "模块", "需求", "产品"}
    return [c for c in cands if c not in stop]


def build(kb_dir: str, out: str):
    path = os.path.join(kb_dir, "index.json")
    if not os.path.exists(path):
        print(f"[warn] 未找到 {path}，请先运行 ingest.py", file=sys.stderr)
        return
    index = json.load(open(path, encoding="utf-8"))
    nodes, edges = {}, {}
    for d in index["docs"]:
        ents = extract_entities(d["text"])
        for e in set(ents):
            nodes.setdefault(e, {"name": e, "mentions": 0, "sources": set()})
            nodes[e]["mentions"] += 1
            nodes[e]["sources"].add(d["source"])
        # 同片段内实体两两共现 → 关系
        seen = set(ents)
        for a in seen:
            for b in seen:
                if a >= b:
                    continue
                key = tuple(sorted((a, b)))
                edges[key] = edges.get(key, 0) + 1
    graph = {
        "backend": "local-json",
        "nodes": [{"id": n, **v, "sources": list(v["sources"])} for n, v in nodes.items()],
        "edges": [{"source": k[0], "target": k[1], "weight": w}
                  for k, w in edges.items() if w >= 2],
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"✓ 图谱：{len(graph['nodes'])} 节点 / {len(graph['edges'])} 边 → {out}")


import sys
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build(args.kb, args.out)
