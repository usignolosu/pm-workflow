#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest.py — 本地文档抓取 → 解析 → 向量化（本地文件库，后端可插拔）

P0 骨架：默认使用纯标准库的关键词索引（本地 JSON 库，零依赖、可离线）。
生产环境可将 STORAGE_BACKEND 切换为 Qdrant(embedded) / LanceDB，
embedding 默认 bge-m3（如已安装 sentence-transformers），否则退化为关键词向量。

用法：
  python3 ingest.py --src ./docs --out ./.kb
  python3 ingest.py --src ./docs --out ./.kb --backend qdrant   # 需安装 qdrant-client
"""
import argparse
import json
import os
import re
import sys

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
SUPPORTED_EXT = {".md", ".txt", ".markdown"}

_stop = set("的 了 和 与 及 在 是 我 你 他 它 这 那 有 个 们 也 都 就 而 并 等 中 为 对 从 把 被 让 a an the of to and or is are "
             .split())


def read_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in SUPPORTED_EXT:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    # PDF 需要 pypdf；未安装则跳过并提示
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            r = PdfReader(path)
            return "\n".join(p.extract_text() or "" for p in r.pages)
        except Exception as e:
            print(f"[skip] {path} 需 pypdf：{e}", file=sys.stderr)
            return ""
    return ""


def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += max(1, size - overlap)
    return chunks


def segment(text: str):
    """分词：CJK 切字符 bigram，拉丁切词；去停用词。供伪向量与关键词检索共用。"""
    toks = []
    # 拉丁词
    for w in re.findall(r"[a-z0-9_]{2,}", text.lower()):
        if w not in _stop:
            toks.append(w)
    # CJK 字符 bigram
    cjk = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in cjk:
        if seg in _stop:
            continue
        for i in range(len(seg) - 1):
            toks.append(seg[i:i + 2])
        if len(seg) == 1:
            toks.append(seg)
    return toks


def pseudo_embed(text: str, dim=256):
    """无依赖的伪向量（关键词哈希），仅用于演示；生产用 bge-m3 真实向量。"""
    import hashlib
    vec = [0.0] * dim
    for t in segment(text):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def build(src: str, out: str):
    os.makedirs(out, exist_ok=True)
    docs, cid = [], 0
    for root, _, files in os.walk(src):
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in SUPPORTED_EXT and \
               os.path.splitext(fn)[1].lower() != ".pdf":
                continue
            full = os.path.join(root, fn)
            text = read_text(full)
            for ch in chunk_text(text):
                docs.append({
                    "id": f"c{cid}",
                    "source": os.path.relpath(full, src),
                    "text": ch,
                    "vec": pseudo_embed(ch),
                })
                cid += 1
    index = {"backend": "local-json", "dim": len(docs[0]["vec"]) if docs else 0,
             "count": len(docs), "docs": docs}
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    print(f"✓ 已索引 {len(docs)} 个片段 → {out}/index.json")
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="本地文档目录")
    ap.add_argument("--out", required=True, help="向量库输出目录")
    ap.add_argument("--backend", default="local-json", help="local-json / qdrant / lancedb")
    args = ap.parse_args()
    if args.backend != "local-json":
        print(f"[info] 当前骨架仅实现 local-json；{args.backend} 需在生产环境接入对应客户端。")
    build(args.src, args.out)


if __name__ == "__main__":
    main()
