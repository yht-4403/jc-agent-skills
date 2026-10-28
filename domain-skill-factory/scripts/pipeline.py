#!/usr/bin/env python3
"""领域 Skill 工厂的确定性流水线：登记、切块、校验、覆盖率与脚手架。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".html", ".htm", ".json", ".jsonl", ".csv"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".epub"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS
ATOM_TYPES = {"principle", "definition", "signal", "diagnosis", "action", "script", "case", "counterexample", "metric", "boundary"}
ATOM_STATUS = {"verified", "inferred", "conflicted", "needs-review"}
CHUNK_STATUS = {"pending", "in_progress", "extracted", "reviewed", "skipped"}
SOURCE_TIERS = {"primary", "secondary", "external"}
SOURCE_TYPES = {"book", "course", "article", "paper", "report", "standard", "job-material", "notes", "transcript", "data"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(prefix: str, value: str, length: int = 12) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:length].upper()}"


def read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        binary = shutil.which("pdftotext")
        if not binary:
            raise RuntimeError("处理 PDF 需要本地 pdftotext（Poppler）")
        result = subprocess.run([binary, "-layout", str(path), "-"], check=True, capture_output=True)
        pages = result.stdout.decode("utf-8", errors="replace").split("\f")
        return "\n\n".join(f"<!-- page: {i} -->\n{page.strip()}" for i, page in enumerate(pages, start=1) if page.strip())
    if suffix in {".docx", ".epub"}:
        binary = shutil.which("pandoc")
        if not binary:
            raise RuntimeError(f"处理 {suffix} 需要本地 pandoc")
        result = subprocess.run([binary, str(path), "-t", "gfm", "--wrap=none"], check=True, capture_output=True)
        return result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw)
        raw = re.sub(r"(?s)<[^>]+>", "\n", raw)
        raw = html.unescape(raw)
    elif suffix == ".json":
        try:
            raw = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    elif suffix == ".csv":
        rows = []
        for row in csv.reader(raw.splitlines()):
            rows.append(" | ".join(cell.strip() for cell in row))
        raw = "\n".join(rows)
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def discover_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        candidates = [input_path]
    else:
        candidates = [p for p in input_path.rglob("*") if p.is_file()]
    return sorted(p for p in candidates if p.suffix.lower() in SUPPORTED_EXTENSIONS and not any(part.startswith(".") for part in p.parts))


def classify_source(path: Path) -> tuple[str, str]:
    name = path.name.lower()
    secondary_markers = ("拆解", "摘要", "笔记", "路线图", "summary", "notes")
    tier = "secondary" if any(marker in name for marker in secondary_markers) else "primary"
    source_type = "notes" if tier == "secondary" else "book"
    return tier, source_type


def count_embedded_media(path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix in {".docx", ".epub"}:
        unzip = shutil.which("unzip")
        if not unzip:
            return 0
        result = subprocess.run([unzip, "-Z1", str(path)], capture_output=True, text=True)
        return sum(1 for line in result.stdout.splitlines() if "/media/" in line.lower() or "images/" in line.lower())
    if suffix == ".pdf":
        pdfimages = shutil.which("pdfimages")
        if not pdfimages:
            return 0
        result = subprocess.run([pdfimages, "-list", str(path)], capture_output=True, text=True)
        return max(0, len([line for line in result.stdout.splitlines() if re.match(r"^\s*\d+\s+\d+", line)]))
    return 0


def ensure_project(project: Path, name: str) -> None:
    for relative in (
        "corpus/chunks", "atoms", "maps", "scenes", "references", "skills",
        "evals", "reports", "state"
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    config = project / "project.json"
    if not config.exists():
        config.write_text(json.dumps({
            "name": name,
            "created_at": now_iso(),
            "schema_version": "1.0",
            "primary_user": "待补充",
            "target_tasks": [],
            "publication": "private"
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    truth = project / "SOURCE_OF_TRUTH.md"
    if not truth.exists():
        truth.write_text(
            f"# {name}：事实来源与边界\n\n"
            "- 一级证据：原始书籍、课程原稿、逐字稿或原始数据。\n"
            "- 二级线索：拆解稿、摘要、路线图和评论，不计入一级来源覆盖率。\n"
            "- 模型推断：必须标记 `inferred`，不能冒充来源观点。\n"
            "- 原始资料保持不变；本工程使用哈希、定位与最小必要证据短引。\n",
            encoding="utf-8"
        )
    for relative in ("atoms/atoms.jsonl", "atoms/relations.jsonl", "scenes/scenes.jsonl", "evals/cases.jsonl"):
        target = project / relative
        if not target.exists():
            target.touch()
    route = project / "maps/domain-map.md"
    if not route.exists():
        template = Path(__file__).resolve().parent.parent / "assets" / "learning-map-template.md"
        if template.exists():
            route.write_text(template.read_text(encoding="utf-8").replace("{领域}", name), encoding="utf-8")
        else:
            route.write_text(
                f"# {name}知识地图\n\n"
                "> 说明这张地图服务谁、依据哪些资料、目前完成到什么程度。\n\n"
                "## 这个领域在解决什么\n\n"
                "## 全局结构\n\n"
                "## 核心方法\n\n"
                "## 常见问题与卡点\n\n"
                "## 学习与实践\n\n"
                "## 来源与待验证内容\n",
                encoding="utf-8"
            )


def paragraph_units(text: str) -> list[tuple[int, int, str, str]]:
    lines = text.splitlines()
    units: list[tuple[int, int, str, str]] = []
    start = 1
    buffer: list[str] = []
    heading = ""
    active_heading = ""
    for index, line in enumerate(lines, start=1):
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            if buffer:
                units.append((start, index - 1, active_heading, "\n".join(buffer).strip()))
                buffer = []
            active_heading = match.group(1).strip()
            heading = active_heading
            start = index
            buffer.append(line)
        elif not line.strip() and buffer:
            units.append((start, index, active_heading or heading, "\n".join(buffer).strip()))
            buffer = []
            start = index + 1
        else:
            if not buffer:
                start = index
            buffer.append(line)
    if buffer:
        units.append((start, len(lines), active_heading or heading, "\n".join(buffer).strip()))
    return [unit for unit in units if unit[3]]


def make_chunks(text: str, source_id: str, target_chars: int, max_chars: int) -> list[dict]:
    units = paragraph_units(text)
    chunks: list[dict] = []
    current: list[tuple[int, int, str, str]] = []
    current_chars = 0

    def flush() -> None:
        nonlocal current, current_chars
        if not current:
            return
        order = len(chunks) + 1
        body = "\n\n".join(item[3] for item in current)
        heading = next((item[2] for item in reversed(current) if item[2]), "")
        chunk_id = stable_id("CHK", f"{source_id}:{order}:{current[0][0]}:{current[-1][1]}")
        chunks.append({
            "chunk_id": chunk_id, "source_id": source_id, "order": order,
            "heading": heading, "line_start": current[0][0], "line_end": current[-1][1],
            "chars": len(body), "text": body
        })
        current, current_chars = [], 0

    for unit in units:
        unit_chars = len(unit[3])
        if current and current_chars + unit_chars > max_chars:
            flush()
        if unit_chars > max_chars:
            flush()
            lines = unit[3].splitlines()
            segment: list[str] = []
            seg_start = unit[0]
            for offset, line in enumerate(lines):
                segment.append(line)
                if len("\n".join(segment)) >= target_chars:
                    seg_text = "\n".join(segment)
                    seg_end = unit[0] + offset
                    current = [(seg_start, seg_end, unit[2], seg_text)]
                    current_chars = len(seg_text)
                    flush()
                    segment, seg_start = [], seg_end + 1
            if segment:
                current = [(seg_start, unit[1], unit[2], "\n".join(segment))]
                current_chars = len(current[0][3])
            continue
        current.append(unit)
        current_chars += unit_chars + 2
    flush()
    return chunks


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    if not path.exists():
        return records, [f"缺少文件：{path}"]
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                errors.append(f"{path}:{number} 不是 JSON 对象")
            else:
                records.append(value)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{number} JSON 错误：{exc.msg}")
    return records, errors


def load_manifest(path_value: str | None) -> dict[str, dict]:
    if not path_value:
        return {}
    records, errors = load_jsonl(Path(path_value).resolve())
    if errors:
        raise ValueError("；".join(errors))
    result = {}
    for record in records:
        if "path" not in record:
            raise ValueError("来源清单每行必须包含 path")
        result[str(Path(record["path"]).expanduser().resolve())] = record
    return result


def prepare(args: argparse.Namespace) -> int:
    input_path, project = Path(args.input).resolve(), Path(args.project).resolve()
    if not input_path.exists():
        print(f"输入不存在：{input_path}", file=sys.stderr)
        return 2
    ensure_project(project, args.name)
    try:
        manifest = load_manifest(args.source_manifest)
    except ValueError as exc:
        print(f"来源清单错误：{exc}", file=sys.stderr)
        return 2
    files = discover_files(input_path)
    if not files:
        print("没有发现支持的文本文件。PDF/DOCX/EPUB 请先转换为可定位文本。", file=sys.stderr)
        return 2
    old_sources, _ = load_jsonl(project / "corpus" / "sources.jsonl")
    old_chunks, _ = load_jsonl(project / "corpus" / "chunks.jsonl")
    old_statuses, _ = load_jsonl(project / "state" / "chunk-status.jsonl")
    old_source_hashes = {item.get("sha256") for item in old_sources}
    old_chunk_ids = {item.get("chunk_id") for item in old_chunks}
    status_by_chunk = {item.get("chunk_id"): item for item in old_statuses}
    sources, chunk_index = [], []
    media_warnings: list[str] = []
    seen_hashes: dict[str, str] = {}
    duplicate_paths: list[tuple[str, str]] = []
    for path in files:
        digest = sha256_file(path)
        source_id = stable_id("SRC", digest)
        try:
            text = read_text(path)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"无法读取 {path}：{exc}", file=sys.stderr)
            return 2
        if len(text.strip()) < 100:
            print(f"来源几乎没有可抽取文本，疑似扫描件或转换失败：{path}", file=sys.stderr)
            return 2
        media_count = count_embedded_media(path)
        if media_count:
            media_warnings.append(f"{path} 含 {media_count} 个图片/媒体对象，需检查图表信息或建立 OCR 待办。")
        tier, source_type = classify_source(path)
        meta = manifest.get(str(path.resolve()), {})
        tier = meta.get("source_tier", tier)
        source_type = meta.get("source_type", source_type)
        relative = str(path.relative_to(input_path)) if input_path.is_dir() else path.name
        if digest in seen_hashes:
            duplicate_paths.append((str(path), seen_hashes[digest]))
            continue
        seen_hashes[digest] = str(path)
        source = {
            "source_id": source_id, "path": str(path), "relative_path": relative,
            "sha256": digest, "bytes": path.stat().st_size, "chars": len(text),
            "source_tier": tier, "source_type": source_type, "title": meta.get("title", path.stem),
            "collected_at": meta.get("collected_at"), "valid_until": meta.get("valid_until"),
            "license": meta.get("license", "private-user-provided"), "media_assets": media_count,
            "registered_at": now_iso()
        }
        sources.append(source)
        for chunk in make_chunks(text, source_id, args.target_chars, args.max_chars):
            chunk_path = project / "corpus" / "chunks" / f"{chunk['chunk_id']}.md"
            front = (
                f"---\nchunk_id: {chunk['chunk_id']}\nsource_id: {source_id}\n"
                f"line_start: {chunk['line_start']}\nline_end: {chunk['line_end']}\n---\n\n"
            )
            chunk_path.write_text(front + chunk.pop("text") + "\n", encoding="utf-8")
            chunk["chunk_path"] = str(chunk_path.relative_to(project))
            chunk_index.append(chunk)
    write_jsonl(project / "corpus" / "sources.jsonl", sources)
    write_jsonl(project / "corpus" / "chunks.jsonl", chunk_index)
    statuses = []
    for chunk in chunk_index:
        previous = status_by_chunk.get(chunk["chunk_id"])
        statuses.append(previous or {
            "chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"],
            "status": "pending", "updated_at": now_iso(), "batch_id": None, "note": ""
        })
    write_jsonl(project / "state" / "chunk-status.jsonl", statuses)
    stats = Counter(source["source_tier"] for source in sources)
    report = [
        f"# {args.name}：来源审计", "", f"生成时间：{now_iso()}", "",
        f"- 文件：{len(sources)}", f"- 文本块：{len(chunk_index)}",
        f"- 总字符：{sum(s['chars'] for s in sources):,}",
        f"- 一级来源：{stats['primary']}", f"- 二级线索：{stats['secondary']}",
        f"- 完全重复文件：{len(duplicate_paths)}", "",
        "## 风险", ""
    ]
    if stats["primary"] == 0:
        report.append("- 没有识别到一级来源，不能宣称完成原文蒸馏。")
    if stats["secondary"]:
        report.append("- 存在拆解稿/摘要/路线图；它们只作线索，不计入一级覆盖率。")
    report.extend(f"- {warning}" for warning in media_warnings)
    unmatched_manifest = sorted(set(manifest) - {str(path.resolve()) for path in files})
    if unmatched_manifest:
        report.append(f"- 来源清单有 {len(unmatched_manifest)} 条未匹配实际文件：{unmatched_manifest}")
    unsupported = [p for p in (input_path.rglob("*") if input_path.is_dir() else []) if p.is_file() and p.suffix.lower() not in SUPPORTED_EXTENSIONS]
    if unsupported:
        counts = Counter(p.suffix.lower() or "无扩展名" for p in unsupported)
        report.append(f"- 未处理文件：{len(unsupported)}（{dict(counts)}）；需转换后重新 prepare。")
    if duplicate_paths:
        report.extend(["", "## 重复文件", ""] + [f"- `{a}` = `{b}`" for a, b in duplicate_paths])
    (project / "reports" / "source-audit.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    state = {
        "phase": "prepared", "updated_at": now_iso(), "source_count": len(sources),
        "chunk_count": len(chunk_index),
        "atom_count": len(load_jsonl(project / "atoms" / "atoms.jsonl")[0]),
        "scene_count": len(load_jsonl(project / "scenes" / "scenes.jsonl")[0]),
        "new_source_hashes": sorted({s["sha256"] for s in sources} - old_source_hashes),
        "removed_source_hashes": sorted(old_source_hashes - {s["sha256"] for s in sources}),
        "new_chunk_count": len({c["chunk_id"] for c in chunk_index} - old_chunk_ids),
        "next": "运行 next-batch 领取样本块，完成原子抽取后用 mark-chunks 更新处理状态"
    }
    (project / "state" / "pipeline.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已准备工程：{project}\n来源 {len(sources)}，文本块 {len(chunk_index)}，审计见 reports/source-audit.md")
    return 0


def validate_atoms(args: argparse.Namespace, quiet: bool = False) -> tuple[int, list[str]]:
    project = Path(args.project).resolve()
    atoms, errors = load_jsonl(project / "atoms" / "atoms.jsonl")
    sources, source_errors = load_jsonl(project / "corpus" / "sources.jsonl")
    chunks, chunk_errors = load_jsonl(project / "corpus" / "chunks.jsonl")
    errors.extend(source_errors + chunk_errors)
    source_ids = {item.get("source_id") for item in sources}
    chunk_ids = {item.get("chunk_id") for item in chunks}
    chunk_by_id = {item.get("chunk_id"): item for item in chunks}
    for field, records in (("source_id", sources), ("chunk_id", chunks)):
        counts = Counter(item.get(field) for item in records)
        for value, count in counts.items():
            if not value or count > 1:
                errors.append(f"{field} 缺失或重复：{value}（{count} 次）")
    for index, source in enumerate(sources, start=1):
        if source.get("source_tier") not in SOURCE_TIERS:
            errors.append(f"sources.jsonl:{index} 非法 source_tier：{source.get('source_tier')}")
        if source.get("source_type") not in SOURCE_TYPES:
            errors.append(f"sources.jsonl:{index} 非法 source_type：{source.get('source_type')}")
        if not source.get("license"):
            errors.append(f"sources.jsonl:{index} 缺 license")
    seen: set[str] = set()
    required = {"atom_id", "statement", "atom_type", "conditions", "stage_ids", "scene_ids", "evidence", "confidence", "status"}
    for index, atom in enumerate(atoms, start=1):
        label = f"atoms.jsonl:{index}"
        missing = required - atom.keys()
        if missing:
            errors.append(f"{label} 缺字段：{sorted(missing)}")
            continue
        atom_id = atom["atom_id"]
        if atom_id in seen:
            errors.append(f"{label} 重复 atom_id：{atom_id}")
        seen.add(atom_id)
        if atom["atom_type"] not in ATOM_TYPES:
            errors.append(f"{label} 非法 atom_type：{atom['atom_type']}")
        if atom["status"] not in ATOM_STATUS:
            errors.append(f"{label} 非法 status：{atom['status']}")
        if not isinstance(atom["confidence"], (int, float)) or not 0 <= atom["confidence"] <= 1:
            errors.append(f"{label} confidence 必须在 0–1")
        evidence = atom.get("evidence") or {}
        if evidence.get("source_id") not in source_ids:
            errors.append(f"{label} source_id 不存在：{evidence.get('source_id')}")
        if evidence.get("chunk_id") not in chunk_ids:
            errors.append(f"{label} chunk_id 不存在：{evidence.get('chunk_id')}")
        elif chunk_by_id[evidence["chunk_id"]].get("source_id") != evidence.get("source_id"):
            errors.append(f"{label} source_id 与 chunk 所属来源不一致")
        else:
            chunk = chunk_by_id[evidence["chunk_id"]]
            line_start, line_end = evidence.get("line_start"), evidence.get("line_end")
            if not isinstance(line_start, int) or not isinstance(line_end, int) or line_start > line_end:
                errors.append(f"{label} 证据行号无效")
            elif line_start < chunk.get("line_start", 0) or line_end > chunk.get("line_end", 0):
                errors.append(f"{label} 证据行号超出对应文本块范围")
        if atom["status"] == "verified" and not evidence.get("quote"):
            errors.append(f"{label} verified 原子缺证据短引")
        if atom["status"] == "verified" and evidence.get("chunk_id") in chunk_by_id and evidence.get("quote"):
            chunk_path = project / chunk_by_id[evidence["chunk_id"]]["chunk_path"]
            chunk_text = chunk_path.read_text(encoding="utf-8") if chunk_path.exists() else ""
            compact = lambda value: re.sub(r"\s+", "", value)
            if compact(evidence["quote"]) not in compact(chunk_text):
                errors.append(f"{label} 证据短引未在对应文本块中找到")
    if not quiet:
        if errors:
            print("原子校验失败：\n- " + "\n- ".join(errors), file=sys.stderr)
        else:
            print(f"原子校验通过：{len(atoms)} 条")
    return (1 if errors else 0), errors


def coverage(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    sources, errors = load_jsonl(project / "corpus" / "sources.jsonl")
    chunks, more = load_jsonl(project / "corpus" / "chunks.jsonl")
    atoms, atom_errors = load_jsonl(project / "atoms" / "atoms.jsonl")
    scenes, scene_errors = load_jsonl(project / "scenes" / "scenes.jsonl")
    statuses, status_errors = load_jsonl(project / "state" / "chunk-status.jsonl")
    errors += more + atom_errors + scene_errors + status_errors
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    chunk_to_source = {c.get("chunk_id"): c.get("source_id") for c in chunks}
    covered_chunks = {a.get("evidence", {}).get("chunk_id") for a in atoms}
    primary_sources = {s["source_id"] for s in sources if s.get("source_tier") == "primary"}
    primary_chunks = {c["chunk_id"] for c in chunks if c.get("source_id") in primary_sources}
    covered_primary = covered_chunks & primary_chunks
    reviewed_chunks = {item.get("chunk_id") for item in statuses if item.get("status") == "reviewed"}
    extracted_chunks = {item.get("chunk_id") for item in statuses if item.get("status") in {"extracted", "reviewed"}}
    atom_ids = {a.get("atom_id") for a in atoms}
    used_atoms = {atom_id for scene in scenes for atom_id in scene.get("atom_ids", [])}
    scene_ids = {s.get("scene_id") for s in scenes}
    linked_scene_ids = {scene_id for atom in atoms for scene_id in atom.get("scene_ids", [])}
    pct = lambda a, b: (100 * a / b) if b else 0.0
    report = [
        "# 覆盖率报告", "", f"生成时间：{now_iso()}", "",
        f"- 一级来源完整复核覆盖：{len(reviewed_chunks & primary_chunks)}/{len(primary_chunks)}（{pct(len(reviewed_chunks & primary_chunks), len(primary_chunks)):.1f}%）",
        f"- 已抽取未必复核：{len(extracted_chunks)}/{len(chunks)}（{pct(len(extracted_chunks), len(chunks)):.1f}%）",
        f"- 原子触达文本块：{len(covered_chunks)}/{len(chunks)}（{pct(len(covered_chunks), len(chunks)):.1f}%；不能等同完整覆盖）",
        f"- 原子进入场景：{len(atom_ids & used_atoms)}/{len(atom_ids)}（{pct(len(atom_ids & used_atoms), len(atom_ids)):.1f}%）",
        f"- 场景被原子反向链接：{len(scene_ids & linked_scene_ids)}/{len(scene_ids)}（{pct(len(scene_ids & linked_scene_ids), len(scene_ids)):.1f}%）",
        "", "## 待处理", "",
        f"- 未完整复核一级文本块：{len(primary_chunks - reviewed_chunks)}",
        f"- 未进入任何场景的原子：{len(atom_ids - used_atoms)}",
        f"- 没有原子反向链接的场景：{len(scene_ids - linked_scene_ids)}",
    ]
    (project / "reports" / "coverage.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[4:8]))
    return 0


def next_batch(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    statuses, errors = load_jsonl(project / "state" / "chunk-status.jsonl")
    chunks, chunk_errors = load_jsonl(project / "corpus" / "chunks.jsonl")
    if errors or chunk_errors:
        print("\n".join(errors + chunk_errors), file=sys.stderr)
        return 1
    chunk_by_id = {item["chunk_id"]: item for item in chunks}
    selected = [item for item in statuses if item.get("status") == "pending"][:args.limit]
    if not selected:
        print("没有 pending 文本块。")
        return 0
    batch_id = f"BAT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    selected_ids = {item["chunk_id"] for item in selected}
    for item in statuses:
        if item["chunk_id"] in selected_ids:
            item.update({"status": "in_progress", "batch_id": batch_id, "updated_at": now_iso()})
    write_jsonl(project / "state" / "chunk-status.jsonl", statuses)
    batch = {
        "batch_id": batch_id, "created_at": now_iso(), "status": "in_progress",
        "chunk_ids": [item["chunk_id"] for item in selected]
    }
    with (project / "state" / "batches.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(batch, ensure_ascii=False) + "\n")
    print(json.dumps({"batch_id": batch_id, "chunks": [chunk_by_id[item["chunk_id"]] for item in selected]}, ensure_ascii=False, indent=2))
    return 0


def sync_status(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    chunks, errors = load_jsonl(project / "corpus" / "chunks.jsonl")
    old, old_errors = load_jsonl(project / "state" / "chunk-status.jsonl") if (project / "state" / "chunk-status.jsonl").exists() else ([], [])
    if errors or old_errors:
        print("\n".join(errors + old_errors), file=sys.stderr)
        return 1
    old_by_id = {item.get("chunk_id"): item for item in old}
    statuses = [old_by_id.get(chunk["chunk_id"]) or {
        "chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"], "status": "pending",
        "updated_at": now_iso(), "batch_id": None, "note": ""
    } for chunk in chunks]
    write_jsonl(project / "state" / "chunk-status.jsonl", statuses)
    print(f"已同步 {len(statuses)} 个文本块状态。")
    return 0


def mark_chunks(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    statuses, errors = load_jsonl(project / "state" / "chunk-status.jsonl")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    wanted = set(args.chunk_ids)
    known = {item.get("chunk_id") for item in statuses}
    if wanted - known:
        print(f"未知 chunk_id：{sorted(wanted - known)}", file=sys.stderr)
        return 1
    atoms, atom_errors = load_jsonl(project / "atoms" / "atoms.jsonl")
    if atom_errors:
        print("\n".join(atom_errors), file=sys.stderr)
        return 1
    chunks_with_atoms = {atom.get("evidence", {}).get("chunk_id") for atom in atoms}
    transitions = {
        "pending": {"in_progress", "skipped"},
        "in_progress": {"pending", "extracted", "skipped"},
        "extracted": {"in_progress", "reviewed"},
        "reviewed": {"in_progress"},
        "skipped": {"in_progress"},
    }
    for item in statuses:
        if item.get("chunk_id") in wanted:
            current = item.get("status")
            if args.status not in transitions.get(current, set()):
                print(f"不允许状态跳转：{item['chunk_id']} {current} → {args.status}", file=sys.stderr)
                return 1
            if args.status == "extracted" and item["chunk_id"] not in chunks_with_atoms and not args.note:
                print(f"{item['chunk_id']} 没有知识原子；标记 extracted 时必须说明无可抽取内容的原因。", file=sys.stderr)
                return 1
            if args.status == "reviewed" and (not args.reviewer or not args.note):
                print("标记 reviewed 必须同时提供 --reviewer 和 --note。", file=sys.stderr)
                return 1
            item.update({"status": args.status, "updated_at": now_iso(), "note": args.note or item.get("note", "")})
            if args.status == "reviewed":
                item.update({"reviewer": args.reviewer, "reviewed_at": now_iso()})
    write_jsonl(project / "state" / "chunk-status.jsonl", statuses)
    batches_path = project / "state" / "batches.jsonl"
    batches, batch_errors = load_jsonl(batches_path) if batches_path.exists() else ([], [])
    if not batch_errors and batches:
        status_by_id = {item["chunk_id"]: item["status"] for item in statuses}
        for batch in batches:
            if all(status_by_id.get(chunk_id) in {"reviewed", "skipped"} for chunk_id in batch.get("chunk_ids", [])):
                batch.update({"status": "completed", "completed_at": now_iso()})
        write_jsonl(batches_path, batches)
    print(f"已把 {len(wanted)} 个文本块标记为 {args.status}。")
    return 0


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def scaffold(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    scenes, errors = load_jsonl(project / "scenes" / "scenes.jsonl")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if not scenes:
        print("场景库为空；先完成 scenes/scenes.jsonl。", file=sys.stderr)
        return 2
    grouped: dict[str, list[dict]] = defaultdict(list)
    for scene in scenes:
        required = {
            "scene_id", "name", "stage_id", "trigger", "goal", "required_inputs", "decisions",
            "workflow", "pitfalls", "output_contract", "atom_ids", "skill"
        }
        missing = required - scene.keys()
        if missing:
            print(f"场景 {scene.get('scene_id', '?')} 缺字段：{sorted(missing)}", file=sys.stderr)
            return 1
        grouped[scene["skill"]].append(scene)
    for skill_name, skill_scenes in grouped.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
            print(f"非法 skill 名称：{skill_name}", file=sys.stderr)
            return 1
        skill_dir = project / "skills" / skill_name
        refs_dir = skill_dir / "references"
        agents_dir = skill_dir / "agents"
        refs_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)
        index_lines = ["## 场景与方法", ""]
        for scene in skill_scenes:
            safe_scene_name = re.sub(r'[/\\:*?"<>|]', '-', scene["name"])
            ref_name = f"{scene['scene_id']}-{safe_scene_name}.md"
            ref_path = refs_dir / ref_name
            content = [
                f"# {scene['name']}", "", f"场景 ID：`{scene['scene_id']}`", "",
                "## 什么时候使用", ""
            ] + [f"- {x}" for x in scene.get("trigger", [])] + [
                "", "## 要解决的问题", "", scene["goal"],
                "", "## 核心判断", ""
            ] + [f"- {x}" for x in scene.get("decisions", [])] + [
                "", "## 大体方法", ""
            ] + [f"{i}. {x}" for i, x in enumerate(scene["workflow"], start=1)] + [
                "", "## 常见误区", ""
            ] + [f"- {x}" for x in scene["pitfalls"]] + [
                "", "## 结果形态", ""
            ] + [f"- {x}" for x in scene["output_contract"]] + [
                "", "## 证据原子", "", ", ".join(f"`{x}`" for x in scene["atom_ids"]), ""
            ]
            practice = scene.get("minimum_practice") or scene.get("practice")
            if practice:
                content.extend(["", "## 实践与反馈", ""])
                if isinstance(practice, dict):
                    for key, value in practice.items():
                        if isinstance(value, list):
                            content.append(f"- {key}：{'；'.join(str(x) for x in value)}")
                        else:
                            content.append(f"- {key}：{value}")
                elif isinstance(practice, list):
                    content.extend(f"- {x}" for x in practice)
            ref_path.write_text("\n".join(content), encoding="utf-8")
            index_lines.append(f"- [{scene['name']}](references/{ref_name}) — `{scene['scene_id']}`")
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists() or args.force:
            description = f"处理 {', '.join(s['name'] for s in skill_scenes[:3])} 等场景。用户出现这些触发信号或要求完成相应任务时使用。"
            skill_md.write_text(
                f"---\nname: {skill_name}\ndescription: {description}\n---\n\n"
                f"# {skill_name}\n\n这个 Skill 负责处理下列一组相关问题。先理解用户真正想解决什么，再读取最接近的 Reference；把其中的方法用于当前材料，不要机械复述。\n\n"
                + "\n".join(index_lines) + "\n\n"
                "## 工作方式\n\n"
                "1. 先使用当前对话和用户已经提供的材料。\n"
                "2. 根据场景选择方法；无法区分时，只追问会改变判断的信息。\n"
                "3. 说明当前判断及其依据，并完成该任务自然需要的产物。\n"
                "4. 对不确定、越界或需要外部验证的部分明确说明。\n"
                "5. 如果用户带着新结果回来，根据结果继续判断，不预设固定长链。\n",
                encoding="utf-8"
            )
        display = skill_name.replace("-", " ").title()
        (agents_dir / "openai.yaml").write_text(
            "interface:\n"
            f"  display_name: {yaml_quote(display)}\n"
            f"  short_description: {yaml_quote('使用该领域的方法处理相关问题')}\n"
            f"  default_prompt: {yaml_quote(f'使用 ${skill_name} 处理这个问题。')}\n",
            encoding="utf-8"
        )
    prefixes = {name.split("-", 1)[0] for name in grouped}
    router_name = f"{next(iter(prefixes))}-router" if len(prefixes) == 1 else "domain-router"
    router_dir = project / "skills" / router_name
    (router_dir / "agents").mkdir(parents=True, exist_ok=True)
    routes = ["| 触发场景 | 执行 Skill | 场景 ID |", "|---|---|---|"]
    for skill_name, skill_scenes in sorted(grouped.items()):
        for scene in skill_scenes:
            routes.append(f"| {scene['name']} | `${skill_name}` | `{scene['scene_id']}` |")
    router_skill = router_dir / "SKILL.md"
    if not router_skill.exists() or args.force:
        router_skill.write_text(
            f"---\nname: {router_name}\ndescription: 识别用户在该领域想解决的问题，并路由到合适的执行 Skill；用户不知道该用哪个 Skill，或完成一次任务后想判断下一步时使用。\n---\n\n"
            "# 领域路由\n\n"
            "先读当前对话。用户的问题已经明确时，直接选择最相关的执行 Skill；问题仍然模糊时，只问一个有助于区分方向的问题。不要在路由层复制所有专业知识。\n\n"
            "## 路由表\n\n" + "\n".join(routes) + "\n\n"
            "## 任务后导航\n\n"
            "读取上一个 Skill 的实际结论和用户的新反馈，再推荐当前最相关的下一步。用户已经明确想做什么时，优先尊重他的选择。\n\n"
            "## 无法路由时\n\n1. 只追问一个会改变路由的目标、事实或期望产物。\n2. 如果没有匹配场景，明确标记知识缺口。\n3. 不把相邻场景的答案强行套用。\n",
            encoding="utf-8"
        )
    (router_dir / "agents" / "openai.yaml").write_text(
        "interface:\n"
        f"  display_name: {yaml_quote('领域任务路由')}\n"
        f"  short_description: {yaml_quote('理解问题并调用合适的领域 Skill')}\n"
        f"  default_prompt: {yaml_quote(f'使用 ${router_name} 判断这个问题应该调用哪个执行 Skill。')}\n",
        encoding="utf-8"
    )
    print(f"已生成/更新 {len(grouped)} 个执行 Skill 骨架和 1 个路由 Skill。")
    return 0


def validate_project(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    required = [
        "project.json", "SOURCE_OF_TRUTH.md", "corpus/sources.jsonl", "corpus/chunks.jsonl",
        "atoms/atoms.jsonl", "maps/domain-map.md", "scenes/scenes.jsonl", "evals/cases.jsonl",
        "reports/source-audit.md", "state/pipeline.json", "state/chunk-status.jsonl"
    ]
    errors = [f"缺少 {path}" for path in required if not (project / path).exists()]
    atom_code, atom_errors = validate_atoms(args, quiet=True)
    errors.extend(atom_errors)
    scenes, scene_errors = load_jsonl(project / "scenes" / "scenes.jsonl")
    atoms, _ = load_jsonl(project / "atoms" / "atoms.jsonl")
    evals, eval_errors = load_jsonl(project / "evals" / "cases.jsonl")
    statuses, status_errors = load_jsonl(project / "state" / "chunk-status.jsonl")
    errors.extend(scene_errors + eval_errors)
    errors.extend(status_errors)
    atom_ids = {a.get("atom_id") for a in atoms}
    seen_scenes: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        required_scene = {
            "scene_id", "name", "stage_id", "trigger", "goal", "required_inputs", "decisions",
            "workflow", "pitfalls", "output_contract", "atom_ids", "skill"
        }
        if required_scene - scene.keys():
            errors.append(f"scenes.jsonl:{index} 缺字段：{sorted(required_scene - scene.keys())}")
        scene_id = scene.get("scene_id")
        if not scene_id:
            errors.append(f"scenes.jsonl:{index} 缺 scene_id")
        elif scene_id in seen_scenes:
            errors.append(f"scenes.jsonl:{index} 重复 scene_id：{scene_id}")
        seen_scenes.add(scene_id)
        for atom_id in scene.get("atom_ids", []):
            if atom_id not in atom_ids:
                errors.append(f"场景 {scene_id} 引用了不存在的原子 {atom_id}")
        skill_name = scene.get("skill")
        if skill_name and not (project / "skills" / skill_name / "SKILL.md").exists():
            errors.append(f"场景 {scene_id} 的执行 Skill 尚未生成：{skill_name}")
    for index, case in enumerate(evals, start=1):
        required_eval = {
            "case_id", "user_prompt", "expected_skill", "expected_scene_ids", "must_ask",
            "must_include", "must_not", "evidence_required", "severity"
        }
        if required_eval - case.keys():
            errors.append(f"evals/cases.jsonl:{index} 缺字段：{sorted(required_eval - case.keys())}")
        for scene_id in case.get("expected_scene_ids", []):
            if scene_id not in seen_scenes:
                errors.append(f"evals/cases.jsonl:{index} 引用了不存在的场景 {scene_id}")
        expected_skill = case.get("expected_skill")
        if expected_skill and not (project / "skills" / expected_skill / "SKILL.md").exists():
            errors.append(f"evals/cases.jsonl:{index} 引用了未生成的 Skill {expected_skill}")
    known_chunks = {item.get("chunk_id") for item in load_jsonl(project / "corpus" / "chunks.jsonl")[0]}
    for index, status in enumerate(statuses, start=1):
        if status.get("chunk_id") not in known_chunks:
            errors.append(f"chunk-status.jsonl:{index} 引用了不存在的文本块")
        if status.get("status") not in CHUNK_STATUS:
            errors.append(f"chunk-status.jsonl:{index} 非法状态：{status.get('status')}")
    skill_dirs = [path for path in (project / "skills").iterdir() if path.is_dir() and (path / "SKILL.md").exists()] if (project / "skills").exists() else []
    router_dirs = [path for path in skill_dirs if path.name.endswith("-router")]
    execution_dirs = [path for path in skill_dirs if not path.name.endswith("-router")]
    if not atoms:
        errors.append("发布校验要求 atoms/atoms.jsonl 非空")
    if not scenes:
        errors.append("发布校验要求 scenes/scenes.jsonl 非空")
    if not evals:
        errors.append("发布校验要求 evals/cases.jsonl 非空")
    if not router_dirs:
        errors.append("发布校验要求至少一个路由 Skill")
    if not execution_dirs:
        errors.append("发布校验要求至少一个执行 Skill")
    map_path = project / "maps" / "domain-map.md"
    if map_path.exists():
        map_text = map_path.read_text(encoding="utf-8")
        if len(map_text.strip()) < 200:
            errors.append("知识地图内容过少；至少说明领域结构、核心方法或主要问题")
    if errors:
        print("工程校验失败：\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    print(f"工程结构校验通过：{len(atoms)} 条原子，{len(scenes)} 个场景。语义质量仍需按 quality-gates.md 复核。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把原始资料加工为可追溯的领域 Skill 工程")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare", help="发现来源、切块并初始化工程")
    prepare_parser.add_argument("--input", required=True)
    prepare_parser.add_argument("--project", required=True)
    prepare_parser.add_argument("--name", required=True)
    prepare_parser.add_argument("--target-chars", type=int, default=4500)
    prepare_parser.add_argument("--max-chars", type=int, default=7000)
    prepare_parser.add_argument("--source-manifest", help="可选 JSONL；按绝对 path 覆盖来源层级、类型、标题、日期和许可")
    prepare_parser.set_defaults(func=prepare)
    for command, function, help_text in (
        ("validate-atoms", lambda a: validate_atoms(a)[0], "校验知识原子及证据引用"),
        ("coverage", coverage, "生成覆盖率报告"),
        ("scaffold", scaffold, "从场景库生成执行 Skill 骨架"),
        ("validate-project", validate_project, "校验工程引用完整性"),
        ("next-batch", next_batch, "领取下一批待处理文本块并写入批次账本"),
        ("mark-chunks", mark_chunks, "更新文本块抽取/复核状态"),
        ("sync-status", sync_status, "根据当前文本块索引初始化或同步处理状态"),
    ):
        child = sub.add_parser(command, help=help_text)
        child.add_argument("--project", required=True)
        if command == "scaffold":
            child.add_argument("--force", action="store_true")
        if command == "next-batch":
            child.add_argument("--limit", type=int, default=8)
        if command == "mark-chunks":
            child.add_argument("--status", required=True, choices=sorted(CHUNK_STATUS))
            child.add_argument("--chunk-ids", required=True, nargs="+")
            child.add_argument("--note")
            child.add_argument("--reviewer")
        child.set_defaults(func=function)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
