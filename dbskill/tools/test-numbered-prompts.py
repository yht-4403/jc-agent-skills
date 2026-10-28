#!/usr/bin/env python3
"""Exercise dynamic numbered-prompt retrieval without network access."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


script = Path(__file__).resolve().parents[1] / "skills/dbs/scripts/numbered-prompts.py"
spec = importlib.util.spec_from_file_location("numbered_runtime", script)
assert spec and spec.loader
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

prompt = (
    "# 007｜做出示例结果\n\n来源：公开视频\n\n"
    "## 用户要完成的事\n得到一个结果\n\n"
    "## 需要的输入\n用户材料\n\n"
    "## 执行步骤\n分析材料\n\n"
    "## 交付结果\n可执行结果\n\n"
    "## 验收标准\n能使用\n\n"
    "## 适用边界\n只处理当前材料\n"
).encode("utf-8")
entry = {
    "id": "007",
    "title": "做出示例结果",
    "purpose": "得到一个结果",
    "sha256": hashlib.sha256(prompt).hexdigest(),
}
catalog = json.dumps({"schema_version": 1, "items": [entry]}, ensure_ascii=False).encode("utf-8")


def good_remote(path: str, limit: int) -> bytes:
    return catalog if path == "catalog.json" else prompt


with patch.object(runtime, "read_remote", side_effect=good_remote):
    assert runtime.catalog() == ([entry], True)
    assert runtime.get_prompt("007") == prompt.decode("utf-8")
    try:
        runtime.get_prompt("008")
    except runtime.CatalogError as error:
        assert "尚未" in str(error)
    else:
        raise AssertionError("unpublished code unexpectedly resolved")

with patch.object(runtime, "read_remote", side_effect=lambda path, limit: catalog if path == "catalog.json" else b"changed"):
    try:
        runtime.get_prompt("007")
    except runtime.CatalogError as error:
        assert "校验值" in str(error)
    else:
        raise AssertionError("mismatched content was executed")

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "catalog.json").write_bytes(catalog)
    bundled = root / "007"
    bundled.mkdir()
    (bundled / "PROMPT.md").write_bytes(prompt)
    with patch.object(runtime, "ROOT", root), patch.object(
        runtime, "read_remote", side_effect=runtime.CatalogError("network unavailable")
    ):
        assert runtime.catalog() == ([entry], False)
        assert runtime.get_prompt("007") == prompt.decode("utf-8")

print("PASS: 远端编号读取、未发布编号、哈希不匹配与离线旧版回退")
