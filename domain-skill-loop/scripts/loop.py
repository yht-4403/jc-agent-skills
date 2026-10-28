#!/usr/bin/env python3
"""领域 Skill 工程的有界批处理控制器。语义工作由 Agent 完成，本脚本控制状态与证据门。"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"缺少文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number} JSON 错误：{exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number} 不是 JSON 对象")
        result.append(value)
    return result


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")


def append_event(project: Path, event: str, **payload: object) -> None:
    record = {"event": event, "at": now_iso(), **payload}
    path = project / "state" / "loop-events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


@contextmanager
def project_lock(project: Path):
    lock_path = project / "state" / "domain-loop.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("另一个 Loop 进程正在修改此工程，请稍后重试。") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def factory_script() -> Path:
    path = Path(__file__).resolve().parents[2] / "domain-skill-factory" / "scripts" / "pipeline.py"
    if not path.exists():
        raise FileNotFoundError("缺少同级 domain-skill-factory；请先安装并启用它。")
    return path


def run_factory(project: Path, command: str, *extra: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(factory_script()), command, "--project", str(project), *extra]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"工厂命令失败：{command}"
        raise RuntimeError(message)
    if not capture and result.stdout.strip():
        print(result.stdout.strip())
    return result


def state_paths(project: Path) -> tuple[Path, Path, Path]:
    return (
        project / "state" / "loop.json",
        project / "state" / "chunk-status.jsonl",
        project / "state" / "batches.jsonl",
    )


def require_project(project: Path) -> None:
    required = ["corpus/chunks.jsonl", "state/chunk-status.jsonl", "atoms/atoms.jsonl"]
    missing = [item for item in required if not (project / item).exists()]
    if missing:
        raise FileNotFoundError(f"不是已准备的领域工程，缺少：{missing}")


def batch_status(batch: dict, status_by_id: dict[str, str]) -> str:
    values = [status_by_id.get(chunk_id, "missing") for chunk_id in batch.get("chunk_ids", [])]
    if values and all(value in {"reviewed", "skipped"} for value in values):
        return "completed"
    if any(value == "in_progress" for value in values):
        return "in_progress"
    if values and all(value == "extracted" for value in values):
        return "extracted"
    if "missing" in values:
        return "invalid"
    return "mixed"


def snapshot(project: Path, loop: dict | None = None) -> dict:
    loop_path, statuses_path, batches_path = state_paths(project)
    loop = loop or load_json(loop_path)
    statuses = load_jsonl(statuses_path)
    batches = load_jsonl(batches_path)
    counts = Counter(item.get("status", "missing") for item in statuses)
    status_by_id = {item["chunk_id"]: item.get("status", "missing") for item in statuses}
    active = []
    for batch in batches:
        current = batch_status(batch, status_by_id)
        if current not in {"completed"}:
            active.append({"batch_id": batch.get("batch_id"), "status": current, "chunk_ids": batch.get("chunk_ids", [])})
    total = len(statuses)
    reviewed = counts.get("reviewed", 0)
    return {
        "loop_status": loop.get("status"),
        "goal": loop.get("goal"),
        "counts": dict(counts),
        "total_chunks": total,
        "reviewed_ratio": round(reviewed / total, 4) if total else 0,
        "active_batches": active,
        "batches_started": loop.get("batches_started", 0),
        "acknowledged_gates": loop.get("acknowledged_gates", []),
        "last_stop_reason": loop.get("last_stop_reason"),
    }


def save_loop(project: Path, loop: dict) -> None:
    loop["updated_at"] = now_iso()
    write_json(project / "state" / "loop.json", loop)


def current_gate(loop: dict, snap: dict, batches: list[dict], statuses: list[dict]) -> str | None:
    configured = set(loop.get("gates", []))
    acknowledged = set(loop.get("acknowledged_gates", []))
    status_by_id = {item["chunk_id"]: item.get("status") for item in statuses}
    completed_batches = sum(batch_status(batch, status_by_id) == "completed" for batch in batches)
    if "sample" in configured and "sample" not in acknowledged and completed_batches >= 1:
        return "sample"
    if "80" in configured and "80" not in acknowledged and snap["reviewed_ratio"] >= 0.8:
        return "80"
    unfinished = sum(snap["counts"].get(key, 0) for key in ("pending", "in_progress", "extracted"))
    if "100" in configured and "100" not in acknowledged and unfinished == 0:
        return "100"
    return None


def cmd_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    require_project(project)
    loop_path, statuses_path, batches_path = state_paths(project)
    with project_lock(project):
        if loop_path.exists() and not args.force:
            print("Loop 已初始化；使用 status 查看，或明确传入 --force 更新配置。")
            return 0
        statuses = load_jsonl(statuses_path)
        batches = load_jsonl(batches_path)
        active_ids = [item["chunk_id"] for item in statuses if item.get("status") in {"in_progress", "extracted"}]
        if active_ids and not any(set(active_ids) & set(batch.get("chunk_ids", [])) for batch in batches):
            batch_id = f"BAT-ADOPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            for item in statuses:
                if item["chunk_id"] in active_ids:
                    item["batch_id"] = batch_id
            batches.append({
                "batch_id": batch_id, "created_at": now_iso(), "status": "in_progress",
                "chunk_ids": active_ids, "adopted": True
            })
            write_jsonl(statuses_path, statuses)
            write_jsonl(batches_path, batches)
        loop = {
            "version": 1, "project": str(project), "goal": args.goal,
            "status": "ready", "batch_size": args.batch_size,
            "max_retries": args.max_retries, "max_batches": args.max_batches,
            "gates": [item for item in args.gates.split(",") if item],
            "review_mode": "independent", "acknowledged_gates": [],
            "batches_started": len(batches), "retry_counts": {},
            "workers": {}, "created_at": now_iso(), "updated_at": now_iso(),
            "last_stop_reason": None
        }
        write_json(loop_path, loop)
        append_event(project, "loop_initialized", goal=args.goal, batch_size=args.batch_size)
    print(json.dumps(snapshot(project), ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    print(json.dumps(snapshot(project), ensure_ascii=False, indent=2))
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    require_project(project)
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        if loop.get("status") in {"paused", "stopped", "complete"}:
            print(json.dumps({"action": loop["status"], "reason": loop.get("last_stop_reason")}, ensure_ascii=False))
            return 0
        statuses = load_jsonl(project / "state" / "chunk-status.jsonl")
        batches = load_jsonl(project / "state" / "batches.jsonl")
        snap = snapshot(project, loop)
        gate = current_gate(loop, snap, batches, statuses)
        if gate:
            loop.update({"status": "gate", "current_gate": gate, "last_stop_reason": f"等待确认质量门 {gate}"})
            save_loop(project, loop)
            append_event(project, "gate_reached", gate=gate)
            print(json.dumps({"action": "gate", "gate": gate, "snapshot": snap}, ensure_ascii=False, indent=2))
            return 0
        active = snap["active_batches"]
        if active:
            invalid = [item for item in active if item["status"] in {"invalid", "mixed"}]
            if invalid:
                loop.update({"status": "stopped", "last_stop_reason": f"批次状态异常：{invalid}"})
                save_loop(project, loop)
                print(json.dumps({"action": "stopped", "reason": loop["last_stop_reason"]}, ensure_ascii=False, indent=2))
                return 1
            action = "work" if any(item["status"] == "in_progress" for item in active) else "review"
            loop["status"] = "running"
            save_loop(project, loop)
            print(json.dumps({"action": action, "batches": active}, ensure_ascii=False, indent=2))
            return 0
        unfinished = sum(snap["counts"].get(key, 0) for key in ("pending", "in_progress", "extracted"))
        if unfinished == 0:
            loop.update({"status": "synthesis", "last_stop_reason": "全部目标块已终结，进入路线/场景/Skill 合成"})
            save_loop(project, loop)
            append_event(project, "extraction_complete")
            print(json.dumps({"action": "synthesize", "snapshot": snap}, ensure_ascii=False, indent=2))
            return 0
        if loop.get("batches_started", 0) >= loop.get("max_batches", 0):
            loop.update({"status": "stopped", "last_stop_reason": "达到 max_batches"})
            save_loop(project, loop)
            print(json.dumps({"action": "stopped", "reason": "达到 max_batches"}, ensure_ascii=False))
            return 0
        result = run_factory(project, "next-batch", "--limit", str(loop["batch_size"]), capture=True)
        payload = json.loads(result.stdout)
        loop.update({"status": "running", "batches_started": loop.get("batches_started", 0) + 1, "last_stop_reason": None})
        save_loop(project, loop)
        append_event(project, "batch_claimed", batch_id=payload["batch_id"], chunk_ids=[item["chunk_id"] for item in payload["chunks"]])
        print(json.dumps({"action": "claim", **payload}, ensure_ascii=False, indent=2))
    return 0


def find_batch(project: Path, batch_id: str) -> tuple[dict, list[dict]]:
    batches = load_jsonl(project / "state" / "batches.jsonl")
    batch = next((item for item in batches if item.get("batch_id") == batch_id), None)
    if not batch:
        raise ValueError(f"找不到批次：{batch_id}")
    return batch, batches


def cmd_submit(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        batch, _ = find_batch(project, args.batch_id)
        statuses = load_jsonl(project / "state" / "chunk-status.jsonl")
        selected = [item for item in statuses if item.get("chunk_id") in batch["chunk_ids"]]
        if not selected or any(item.get("status") != "in_progress" for item in selected):
            raise ValueError("submit 只接受全部处于 in_progress 的批次")
        run_factory(project, "validate-atoms")
        run_factory(project, "mark-chunks", "--status", "extracted", "--chunk-ids", *batch["chunk_ids"], "--note", args.note)
        loop.setdefault("workers", {})[args.batch_id] = args.worker
        save_loop(project, loop)
        append_event(project, "batch_submitted", batch_id=args.batch_id, worker=args.worker, note=args.note)
    print(json.dumps({"action": "review", "batch_id": args.batch_id, "worker": args.worker}, ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        batch, _ = find_batch(project, args.batch_id)
        worker = loop.get("workers", {}).get(args.batch_id)
        if loop.get("review_mode") == "independent" and worker and worker == args.reviewer:
            raise ValueError("独立复核模式下 Reviewer 不能与 Worker 相同")
        statuses = load_jsonl(project / "state" / "chunk-status.jsonl")
        selected = [item for item in statuses if item.get("chunk_id") in batch["chunk_ids"]]
        if not selected or any(item.get("status") != "extracted" for item in selected):
            raise ValueError("review 只接受全部处于 extracted 的批次")
        if args.result == "pass":
            run_factory(project, "mark-chunks", "--status", "reviewed", "--chunk-ids", *batch["chunk_ids"], "--reviewer", args.reviewer, "--note", args.note)
            append_event(project, "batch_review_passed", batch_id=args.batch_id, reviewer=args.reviewer, note=args.note)
            loop["status"] = "ready"
        else:
            retry_counts = loop.setdefault("retry_counts", {})
            retry_counts[args.batch_id] = retry_counts.get(args.batch_id, 0) + 1
            run_factory(project, "mark-chunks", "--status", "in_progress", "--chunk-ids", *batch["chunk_ids"], "--note", args.note)
            append_event(project, "batch_review_failed", batch_id=args.batch_id, reviewer=args.reviewer, note=args.note, retry=retry_counts[args.batch_id])
            if retry_counts[args.batch_id] > loop.get("max_retries", 0):
                loop.update({"status": "stopped", "last_stop_reason": f"批次 {args.batch_id} 超过最大返工次数"})
            else:
                loop["status"] = "running"
        save_loop(project, loop)
    print(json.dumps({"action": loop["status"], "batch_id": args.batch_id, "result": args.result}, ensure_ascii=False, indent=2))
    return 0


def cmd_ack_gate(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        if args.gate not in loop.get("gates", []):
            raise ValueError(f"未配置质量门：{args.gate}")
        if loop.get("current_gate") != args.gate:
            raise ValueError(f"当前并未停在 {args.gate} 门")
        acknowledged = loop.setdefault("acknowledged_gates", [])
        if args.gate not in acknowledged:
            acknowledged.append(args.gate)
        loop.update({"status": "ready", "current_gate": None, "last_stop_reason": None})
        save_loop(project, loop)
        append_event(project, "gate_acknowledged", gate=args.gate, reviewer=args.reviewer, note=args.note)
    print(json.dumps({"action": "ready", "acknowledged_gate": args.gate}, ensure_ascii=False, indent=2))
    return 0


def cmd_release_check(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        snap = snapshot(project, loop)
        unfinished = sum(snap["counts"].get(key, 0) for key in ("pending", "in_progress", "extracted"))
        if unfinished:
            raise ValueError(f"还有 {unfinished} 个未终结文本块，不能发布")
        if "100" in loop.get("gates", []) and "100" not in loop.get("acknowledged_gates", []):
            raise ValueError("100% 质量门尚未确认")
        run_factory(project, "coverage")
        run_factory(project, "validate-project")
        loop.update({"status": "complete", "completed_at": now_iso(), "last_stop_reason": None})
        save_loop(project, loop)
        append_event(project, "release_check_passed")
    print(json.dumps({"action": "complete", "project": str(project)}, ensure_ascii=False, indent=2))
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        loop.update({"status": "paused", "last_stop_reason": args.reason})
        save_loop(project, loop)
        append_event(project, "loop_paused", reason=args.reason)
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    with project_lock(project):
        loop = load_json(project / "state" / "loop.json")
        if loop.get("status") not in {"paused", "stopped"}:
            raise ValueError("只有 paused/stopped 状态可以恢复")
        loop.update({"status": "ready", "last_stop_reason": None})
        save_loop(project, loop)
        append_event(project, "loop_resumed", note=args.note)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="领域 Skill 工程的有界批处理 Loop")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="初始化 Loop 并接管已有进行中批次")
    init.add_argument("--project", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--batch-size", type=int, default=5)
    init.add_argument("--max-retries", type=int, default=2)
    init.add_argument("--max-batches", type=int, default=100)
    init.add_argument("--gates", default="sample,80,100")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)
    for name, function, help_text in (
        ("status", cmd_status, "查看持久化状态与覆盖率"),
        ("advance", cmd_advance, "推进到下一合法动作"),
        ("release-check", cmd_release_check, "运行最终发布校验并完成 Loop"),
    ):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--project", required=True)
        child.set_defaults(func=function)
    submit = sub.add_parser("submit", help="Worker 提交当前批次并进入复核")
    submit.add_argument("--project", required=True)
    submit.add_argument("--batch-id", required=True)
    submit.add_argument("--worker", required=True)
    submit.add_argument("--note", required=True)
    submit.set_defaults(func=cmd_submit)
    review = sub.add_parser("review", help="独立 Reviewer 通过或退回批次")
    review.add_argument("--project", required=True)
    review.add_argument("--batch-id", required=True)
    review.add_argument("--result", choices=["pass", "fail"], required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True)
    review.set_defaults(func=cmd_review)
    gate = sub.add_parser("ack-gate", help="人工确认当前质量门")
    gate.add_argument("--project", required=True)
    gate.add_argument("--gate", choices=["sample", "80", "100"], required=True)
    gate.add_argument("--reviewer", required=True)
    gate.add_argument("--note", required=True)
    gate.set_defaults(func=cmd_ack_gate)
    pause = sub.add_parser("pause", help="暂停 Loop")
    pause.add_argument("--project", required=True)
    pause.add_argument("--reason", required=True)
    pause.set_defaults(func=cmd_pause)
    resume = sub.add_parser("resume", help="从 paused/stopped 恢复")
    resume.add_argument("--project", required=True)
    resume.add_argument("--note", required=True)
    resume.set_defaults(func=cmd_resume)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
