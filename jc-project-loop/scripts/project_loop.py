#!/usr/bin/env python3
"""JC 项目循环：仅使用本地文件的顺序任务状态机。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


配置文件名 = "项目配置.json"
任务文件名 = "任务.jsonl"
状态文件名 = "状态.json"
事件文件名 = "事件.jsonl"
进度文件名 = "进度.md"

任务状态集合 = {"待处理", "进行中", "待复核", "待返工", "已完成", "已阻塞", "已跳过"}
项目状态集合 = {"运行中", "已暂停", "已停止", "已完成"}
可领取状态 = {"待处理", "待返工"}
未完成状态 = {"待处理", "进行中", "待复核", "待返工", "已阻塞"}


class 循环错误(Exception):
    pass


def 当前时间() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def 输出(data: dict[str, Any], exit_code: int = 0) -> None:
    stream = sys.stdout if exit_code == 0 else sys.stderr
    print(json.dumps(data, ensure_ascii=False, indent=2), file=stream)
    raise SystemExit(exit_code)


def 项目路径(args: argparse.Namespace) -> Path:
    return Path(args.项目).expanduser().resolve()


def 原子写入(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def 读取_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise 循环错误(f"缺少文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise 循环错误(f"JSON 格式错误：{path}，{exc}") from exc


def 写入_json(path: Path, data: dict[str, Any]) -> None:
    原子写入(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def 读取任务(project: Path) -> list[dict[str, Any]]:
    path = project / 任务文件名
    if not path.exists():
        raise 循环错误(f"缺少文件：{path}")
    tasks: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise 循环错误(f"{任务文件名} 第 {line_number} 行格式错误：{exc}") from exc
        if not isinstance(item, dict):
            raise 循环错误(f"{任务文件名} 第 {line_number} 行必须是 JSON 对象")
        tasks.append(item)
    return tasks


def 写入任务(project: Path, tasks: list[dict[str, Any]]) -> None:
    content = "".join(json.dumps(task, ensure_ascii=False) + "\n" for task in tasks)
    原子写入(project / 任务文件名, content)


def 追加事件(project: Path, 事件: str, **details: Any) -> None:
    record = {"时间": 当前时间(), "事件": 事件, **details}
    path = project / 事件文件名
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def 加载项目(project: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    config = 读取_json(project / 配置文件名)
    state = 读取_json(project / 状态文件名)
    tasks = 读取任务(project)
    return config, state, tasks


def 查找任务(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    for task in tasks:
        if task.get("任务编号") == task_id:
            return task
    raise 循环错误(f"找不到任务：{task_id}")


def 安全文件名(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "-", value).strip("-")
    return cleaned or "任务"


def 解析质量门(values: list[str] | None) -> list[dict[str, Any]]:
    raw_values = values or ["首批样本:1"]
    gates: list[dict[str, Any]] = []
    names: set[str] = set()
    for raw in raw_values:
        if ":" not in raw:
            raise 循环错误(f"质量门格式应为“名称:完成任务数”：{raw}")
        name, threshold_text = raw.rsplit(":", 1)
        name = name.strip()
        if not name or name in names:
            raise 循环错误(f"质量门名称为空或重复：{raw}")
        try:
            threshold = int(threshold_text)
        except ValueError as exc:
            raise 循环错误(f"质量门阈值必须是整数：{raw}") from exc
        if threshold < 1:
            raise 循环错误(f"质量门阈值必须大于 0：{raw}")
        gates.append({"名称": name, "完成任务数": threshold, "已确认": False, "确认记录": None})
        names.add(name)
    return gates


def 新任务(
    task_id: str,
    title: str,
    description: str,
    criteria: list[str],
    inputs: list[str],
    outputs: list[str],
    max_attempts: int,
) -> dict[str, Any]:
    return {
        "任务编号": task_id,
        "标题": title,
        "说明": description,
        "验收标准": criteria,
        "输入文件": inputs,
        "期望产物": outputs,
        "状态": "待处理",
        "尝试次数": 0,
        "最大尝试次数": max_attempts,
        "领取时间": None,
        "提交时间": None,
        "完成时间": None,
        "产物文件": [],
        "提交说明": None,
        "复核意见": [],
        "阻塞原因": None,
        "跳过原因": None,
    }


def 下一个编号(tasks: list[dict[str, Any]]) -> str:
    used = {task.get("任务编号") for task in tasks}
    number = 1
    while f"task-{number:03d}" in used:
        number += 1
    return f"task-{number:03d}"


def 规范列表(value: Any, field: str, line_number: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise 循环错误(f"导入文件第 {line_number} 行“{field}”必须是字符串数组")
    return value


def 已完成数量(tasks: list[dict[str, Any]]) -> int:
    return sum(task.get("状态") == "已完成" for task in tasks)


def 待确认质量门(config: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    completed = 已完成数量(tasks)
    gates = sorted(config.get("质量门", []), key=lambda item: item["完成任务数"])
    for gate in gates:
        if not gate.get("已确认") and completed >= gate["完成任务数"]:
            return gate
    return None


def 计算动作(config: dict[str, Any], state: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    project_status = state.get("项目状态")
    if project_status == "已停止":
        return {"动作": "已停止", "原因": state.get("停止原因")}
    if project_status == "已暂停":
        return {"动作": "已暂停", "原因": state.get("暂停原因")}

    gate = 待确认质量门(config, tasks)
    if gate:
        return {"动作": "质量门", "质量门": gate}

    running = [task for task in tasks if task.get("状态") == "进行中"]
    if running:
        return {"动作": "执行", "任务": running[0]}

    reviewing = [task for task in tasks if task.get("状态") == "待复核"]
    if reviewing:
        return {"动作": "复核", "任务": reviewing[0]}

    retrying = [task for task in tasks if task.get("状态") == "待返工"]
    if retrying:
        return {"动作": "领取", "候选任务": retrying[0]}

    pending = [task for task in tasks if task.get("状态") == "待处理"]
    if pending:
        return {"动作": "领取", "候选任务": pending[0]}

    blocked = [task for task in tasks if task.get("状态") == "已阻塞"]
    if blocked:
        return {"动作": "阻塞", "任务": blocked}

    if tasks and all(task.get("状态") in {"已完成", "已跳过"} for task in tasks):
        return {"动作": "完成", "完成标准": config.get("完成标准")}

    if not tasks:
        return {"动作": "等待任务", "说明": "项目尚未添加任务"}

    return {"动作": "阻塞", "说明": "存在无法识别的任务状态"}


def 生成进度内容(
    config: dict[str, Any], state: dict[str, Any], tasks: list[dict[str, Any]]
) -> str:
    counts = Counter(task.get("状态", "未知") for task in tasks)
    total = len(tasks)
    completed = counts["已完成"]
    progress = f"{completed / total * 100:.1f}%" if total else "0.0%"
    action = 计算动作(config, state, tasks)
    lines = [
        f"# 项目进度：{config.get('项目名称', '未命名项目')}",
        "",
        f"- 目标：{config.get('目标', '')}",
        f"- 完成标准：{config.get('完成标准', '')}",
        f"- 项目状态：{state.get('项目状态')}",
        f"- 下一动作：{action.get('动作')}",
        f"- 完成进度：{completed}/{total}（{progress}）",
        f"- 更新时间：{当前时间()}",
        "",
        "## 状态统计",
        "",
    ]
    for status in ["待处理", "进行中", "待复核", "待返工", "已完成", "已阻塞", "已跳过"]:
        lines.append(f"- {status}：{counts[status]}")
    lines.extend(
        [
            "",
            "## 质量门",
            "",
            "| 名称 | 触发条件 | 状态 |",
            "| --- | ---: | --- |",
        ]
    )
    for gate in config.get("质量门", []):
        gate_status = "已确认" if gate.get("已确认") else "待确认"
        lines.append(f"| {gate['名称']} | 完成 {gate['完成任务数']} 项 | {gate_status} |")
    if not config.get("质量门"):
        lines.append("| 无 | - | - |")
    lines.extend(
        [
            "",
            "## 任务",
            "",
            "| 编号 | 标题 | 状态 | 尝试 | 产物数 |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for task in tasks:
        title = str(task.get("标题", "")).replace("|", "\\|")
        lines.append(
            f"| {task.get('任务编号')} | {title} | {task.get('状态')} | "
            f"{task.get('尝试次数', 0)}/{task.get('最大尝试次数', 0)} | "
            f"{len(task.get('产物文件', []))} |"
        )
    lines.append("")
    lines.append("> 本文件由脚本生成；任务事实以 `任务.jsonl` 为准。")
    lines.append("")
    return "\n".join(lines)


def 刷新进度(project: Path, config: dict[str, Any], state: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    原子写入(project / 进度文件名, 生成进度内容(config, state, tasks))


def 校验结构(project: Path) -> list[str]:
    errors: list[str] = []
    for name in [配置文件名, 任务文件名, 状态文件名, 事件文件名]:
        if not (project / name).is_file():
            errors.append(f"缺少文件：{name}")
    if errors:
        return errors
    try:
        config, state, tasks = 加载项目(project)
    except 循环错误 as exc:
        return [str(exc)]

    if state.get("项目状态") not in 项目状态集合:
        errors.append(f"非法项目状态：{state.get('项目状态')}")
    ids: list[str] = []
    for index, task in enumerate(tasks, start=1):
        task_id = task.get("任务编号")
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"第 {index} 个任务缺少任务编号")
        else:
            ids.append(task_id)
        if not task.get("标题"):
            errors.append(f"任务 {task_id or index} 缺少标题")
        if task.get("状态") not in 任务状态集合:
            errors.append(f"任务 {task_id or index} 状态非法：{task.get('状态')}")
        attempts = task.get("尝试次数")
        max_attempts = task.get("最大尝试次数")
        if not isinstance(attempts, int) or attempts < 0:
            errors.append(f"任务 {task_id or index} 尝试次数非法")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            errors.append(f"任务 {task_id or index} 最大尝试次数非法")
    if len(ids) != len(set(ids)):
        errors.append("任务编号重复")

    running = [task.get("任务编号") for task in tasks if task.get("状态") == "进行中"]
    if len(running) > 1:
        errors.append(f"同时存在多个进行中任务：{running}")
    current = state.get("当前任务")
    if running and current != running[0]:
        errors.append(f"状态.json 当前任务与任务账本不一致：{current} != {running[0]}")
    if not running and current is not None:
        errors.append(f"没有进行中任务，但状态.json 仍记录当前任务：{current}")

    gate_names: set[str] = set()
    for gate in config.get("质量门", []):
        name = gate.get("名称")
        if not name or name in gate_names:
            errors.append(f"质量门名称为空或重复：{name}")
        gate_names.add(name)
        if not isinstance(gate.get("完成任务数"), int) or gate["完成任务数"] < 1:
            errors.append(f"质量门阈值非法：{name}")
    return errors


def 保存并输出(
    project: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    tasks: list[dict[str, Any]],
    result: dict[str, Any],
) -> None:
    写入_json(project / 配置文件名, config)
    写入_json(project / 状态文件名, state)
    写入任务(project, tasks)
    刷新进度(project, config, state, tasks)
    输出(result)


def 命令_初始化(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    if (project / 配置文件名).exists():
        raise 循环错误(f"项目已经初始化：{project}")
    if args.最大尝试次数 < 1:
        raise 循环错误("最大尝试次数必须大于 0")
    project.mkdir(parents=True, exist_ok=True)
    for dirname in ["产物", "复核", "协议"]:
        (project / dirname).mkdir(exist_ok=True)
    config = {
        "格式版本": 1,
        "项目名称": args.项目名称 or project.name,
        "目标": args.目标,
        "完成标准": args.完成标准,
        "默认最大尝试次数": args.最大尝试次数,
        "质量门": 解析质量门(args.质量门),
        "创建时间": 当前时间(),
        "更新时间": 当前时间(),
    }
    state = {
        "项目状态": "运行中",
        "当前任务": None,
        "暂停原因": None,
        "停止原因": None,
        "更新时间": 当前时间(),
    }
    写入_json(project / 配置文件名, config)
    写入_json(project / 状态文件名, state)
    原子写入(project / 任务文件名, "")
    原子写入(project / 事件文件名, "")
    追加事件(project, "初始化项目", 目标=args.目标, 完成标准=args.完成标准)
    刷新进度(project, config, state, [])
    输出({"结果": "已初始化", "项目目录": str(project), "下一步": "添加任务或导入任务"})


def 命令_添加任务(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    task_id = args.任务编号 or 下一个编号(tasks)
    if any(task.get("任务编号") == task_id for task in tasks):
        raise 循环错误(f"任务编号重复：{task_id}")
    max_attempts = args.最大尝试次数 or config["默认最大尝试次数"]
    if max_attempts < 1:
        raise 循环错误("最大尝试次数必须大于 0")
    task = 新任务(
        task_id,
        args.标题,
        args.说明 or "",
        args.验收标准 or [],
        args.输入文件 or [],
        args.期望产物 or [],
        max_attempts,
    )
    tasks.append(task)
    config["更新时间"] = 当前时间()
    追加事件(project, "添加任务", 任务编号=task_id, 标题=args.标题)
    保存并输出(project, config, state, tasks, {"结果": "已添加任务", "任务": task})


def 命令_导入任务(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    source = Path(args.文件).expanduser().resolve()
    if not source.is_file():
        raise 循环错误(f"任务导入文件不存在：{source}")
    used = {task.get("任务编号") for task in tasks}
    added: list[str] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise 循环错误(f"导入文件第 {line_number} 行格式错误：{exc}") from exc
        if not isinstance(item, dict) or not item.get("标题"):
            raise 循环错误(f"导入文件第 {line_number} 行必须是对象且包含“标题”")
        task_id = item.get("任务编号") or 下一个编号(tasks)
        if not isinstance(task_id, str):
            raise 循环错误(f"导入文件第 {line_number} 行“任务编号”必须是字符串")
        if task_id in used:
            raise 循环错误(f"导入文件第 {line_number} 行任务编号重复：{task_id}")
        try:
            max_attempts = int(item.get("最大尝试次数", config["默认最大尝试次数"]))
        except (TypeError, ValueError) as exc:
            raise 循环错误(f"任务 {task_id} 最大尝试次数必须是整数") from exc
        task = 新任务(
            task_id,
            item["标题"],
            item.get("说明", ""),
            规范列表(item.get("验收标准"), "验收标准", line_number),
            规范列表(item.get("输入文件"), "输入文件", line_number),
            规范列表(item.get("期望产物"), "期望产物", line_number),
            max_attempts,
        )
        if task["最大尝试次数"] < 1:
            raise 循环错误(f"任务 {task_id} 最大尝试次数必须大于 0")
        tasks.append(task)
        used.add(task_id)
        added.append(task_id)
    config["更新时间"] = 当前时间()
    追加事件(project, "导入任务", 来源=str(source), 数量=len(added), 任务编号=added)
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": "已导入任务", "数量": len(added), "任务编号": added},
    )


def 命令_检查(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    errors = 校验结构(project)
    if errors:
        输出({"结果": "检查失败", "错误": errors}, 2)
    config, state, tasks = 加载项目(project)
    刷新进度(project, config, state, tasks)
    输出({"结果": "检查通过", "任务数": len(tasks), "下一动作": 计算动作(config, state, tasks)})


def 命令_状态(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    counts = Counter(task.get("状态") for task in tasks)
    action = 计算动作(config, state, tasks)
    if action.get("动作") == "完成" and state.get("项目状态") == "运行中":
        state["项目状态"] = "已完成"
        state["更新时间"] = 当前时间()
        写入_json(project / 状态文件名, state)
        追加事件(project, "项目满足任务完成条件", 完成标准=config.get("完成标准"))
    刷新进度(project, config, state, tasks)
    输出(
        {
            "项目": config.get("项目名称"),
            "目标": config.get("目标"),
            "完成标准": config.get("完成标准"),
            "项目状态": state.get("项目状态"),
            "当前任务": state.get("当前任务"),
            "任务总数": len(tasks),
            "状态统计": dict(counts),
            "下一动作": action,
        }
    )


def 命令_下一步(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    action = 计算动作(config, state, tasks)
    if action.get("动作") == "完成" and state.get("项目状态") == "运行中":
        state["项目状态"] = "已完成"
        state["更新时间"] = 当前时间()
        写入_json(project / 状态文件名, state)
        追加事件(project, "项目满足任务完成条件", 完成标准=config.get("完成标准"))
    刷新进度(project, config, state, tasks)
    输出(action)


def 确认可运行(config: dict[str, Any], state: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    if state.get("项目状态") != "运行中":
        raise 循环错误(f"项目当前不是运行中：{state.get('项目状态')}")
    gate = 待确认质量门(config, tasks)
    if gate:
        raise 循环错误(f"存在未确认质量门：{gate['名称']}")


def 命令_领取(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    确认可运行(config, state, tasks)
    running = [task for task in tasks if task.get("状态") == "进行中"]
    if running:
        输出({"结果": "继续当前任务", "任务": running[0]})
    reviewing = [task for task in tasks if task.get("状态") == "待复核"]
    if reviewing:
        raise 循环错误(f"必须先复核任务：{reviewing[0]['任务编号']}")
    candidates = [task for task in tasks if task.get("状态") == "待返工"]
    if not candidates:
        candidates = [task for task in tasks if task.get("状态") == "待处理"]
    if not candidates:
        raise 循环错误(f"当前没有可领取任务，下一动作：{计算动作(config, state, tasks)['动作']}")
    task = candidates[0]
    if task["尝试次数"] >= task["最大尝试次数"]:
        task["状态"] = "已阻塞"
        task["阻塞原因"] = "达到最大尝试次数"
        写入任务(project, tasks)
        刷新进度(project, config, state, tasks)
        raise 循环错误(f"任务 {task['任务编号']} 已达到最大尝试次数")
    task["状态"] = "进行中"
    task["尝试次数"] += 1
    task["领取时间"] = 当前时间()
    task["阻塞原因"] = None
    state["当前任务"] = task["任务编号"]
    state["更新时间"] = 当前时间()
    追加事件(
        project,
        "领取任务",
        任务编号=task["任务编号"],
        尝试次数=task["尝试次数"],
        最大尝试次数=task["最大尝试次数"],
    )
    保存并输出(project, config, state, tasks, {"结果": "已领取", "任务": task})


def 解析产物路径(project: Path, values: list[str]) -> list[str]:
    resolved: list[str] = []
    for value in values:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = project / path
        path = path.resolve()
        if not path.exists():
            raise 循环错误(f"产物不存在：{path}")
        try:
            relative = path.relative_to(project)
        except ValueError:
            raise 循环错误(f"产物必须位于项目目录内：{path}")
        resolved.append(str(relative))
    return resolved


def 命令_提交(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    确认可运行(config, state, tasks)
    task_id = args.任务编号 or state.get("当前任务")
    if not task_id:
        raise 循环错误("没有当前任务，请提供 --任务编号")
    task = 查找任务(tasks, task_id)
    if task.get("状态") != "进行中":
        raise 循环错误(f"任务 {task_id} 当前状态不是进行中：{task.get('状态')}")
    products = 解析产物路径(project, args.产物)
    task["状态"] = "待复核"
    task["提交时间"] = 当前时间()
    task["产物文件"] = products
    task["提交说明"] = args.说明
    state["当前任务"] = None
    state["更新时间"] = 当前时间()
    追加事件(project, "提交任务", 任务编号=task_id, 产物=products, 说明=args.说明)
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": "已提交，等待复核", "任务编号": task_id, "产物": products},
    )


def 写入复核记录(project: Path, task_id: str, record: dict[str, Any]) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    filename = f"{安全文件名(task_id)}-{timestamp}.json"
    path = project / "复核" / filename
    写入_json(path, record)
    return str(path.relative_to(project))


def 命令_复核(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    if state.get("项目状态") not in {"运行中", "已暂停"}:
        raise 循环错误(f"项目当前不可复核：{state.get('项目状态')}")
    task = 查找任务(tasks, args.任务编号)
    if task.get("状态") != "待复核":
        raise 循环错误(f"任务 {args.任务编号} 当前状态不是待复核：{task.get('状态')}")
    record = {
        "时间": 当前时间(),
        "任务编号": args.任务编号,
        "结果": args.结果,
        "复核者": args.复核者,
        "意见": args.意见,
        "产物文件": task.get("产物文件", []),
        "尝试次数": task.get("尝试次数"),
    }
    review_path = 写入复核记录(project, args.任务编号, record)
    task.setdefault("复核意见", []).append({**record, "复核记录": review_path})
    if args.结果 == "通过":
        task["状态"] = "已完成"
        task["完成时间"] = 当前时间()
        result_text = "复核通过"
    else:
        if task["尝试次数"] >= task["最大尝试次数"]:
            task["状态"] = "已阻塞"
            task["阻塞原因"] = f"复核未通过且达到最大尝试次数：{args.意见}"
            result_text = "复核未通过，已阻塞"
        else:
            task["状态"] = "待返工"
            task["阻塞原因"] = None
            result_text = "复核未通过，等待返工"
    追加事件(
        project,
        "复核任务",
        任务编号=args.任务编号,
        结果=args.结果,
        复核者=args.复核者,
        意见=args.意见,
        复核记录=review_path,
    )
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": result_text, "任务编号": args.任务编号, "复核记录": review_path},
    )


def 命令_确认质量门(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    gate = next((item for item in config.get("质量门", []) if item.get("名称") == args.名称), None)
    if gate is None:
        raise 循环错误(f"找不到质量门：{args.名称}")
    if gate.get("已确认"):
        输出({"结果": "质量门已经确认", "质量门": gate})
    if 已完成数量(tasks) < gate["完成任务数"]:
        raise 循环错误(
            f"质量门尚未触发：需要完成 {gate['完成任务数']} 项，当前完成 {已完成数量(tasks)} 项"
        )
    gate["已确认"] = True
    gate["确认记录"] = {"时间": 当前时间(), "确认者": args.确认者, "意见": args.意见}
    config["更新时间"] = 当前时间()
    追加事件(project, "确认质量门", 名称=args.名称, 确认者=args.确认者, 意见=args.意见)
    保存并输出(project, config, state, tasks, {"结果": "已确认质量门", "质量门": gate})


def 命令_暂停(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    if state.get("项目状态") != "运行中":
        raise 循环错误(f"只有运行中项目可以暂停：{state.get('项目状态')}")
    state["项目状态"] = "已暂停"
    state["暂停原因"] = args.原因
    state["更新时间"] = 当前时间()
    追加事件(project, "暂停项目", 原因=args.原因)
    保存并输出(project, config, state, tasks, {"结果": "项目已暂停", "原因": args.原因})


def 命令_恢复(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    if state.get("项目状态") != "已暂停":
        raise 循环错误(f"只有已暂停项目可以恢复：{state.get('项目状态')}")
    state["项目状态"] = "运行中"
    state["暂停原因"] = None
    state["更新时间"] = 当前时间()
    追加事件(project, "恢复项目", 说明=args.说明)
    保存并输出(project, config, state, tasks, {"结果": "项目已恢复", "说明": args.说明})


def 命令_停止(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    if state.get("项目状态") == "已停止":
        输出({"结果": "项目已经停止", "原因": state.get("停止原因")})
    state["项目状态"] = "已停止"
    state["停止原因"] = args.原因
    state["更新时间"] = 当前时间()
    追加事件(project, "停止项目", 原因=args.原因)
    保存并输出(project, config, state, tasks, {"结果": "项目已停止", "原因": args.原因})


def 命令_跳过(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    task = 查找任务(tasks, args.任务编号)
    if task.get("状态") not in {"待处理", "待返工", "已阻塞"}:
        raise 循环错误(f"任务 {args.任务编号} 当前状态不可跳过：{task.get('状态')}")
    task["状态"] = "已跳过"
    task["跳过原因"] = args.原因
    task["阻塞原因"] = None
    if state.get("当前任务") == args.任务编号:
        state["当前任务"] = None
    追加事件(project, "跳过任务", 任务编号=args.任务编号, 原因=args.原因)
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": "任务已跳过", "任务编号": args.任务编号, "原因": args.原因},
    )


def 命令_标记阻塞(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    task = 查找任务(tasks, args.任务编号)
    if task.get("状态") in {"已完成", "已跳过"}:
        raise 循环错误(f"终态任务不可标记阻塞：{task.get('状态')}")
    task["状态"] = "已阻塞"
    task["阻塞原因"] = args.原因
    if state.get("当前任务") == args.任务编号:
        state["当前任务"] = None
    追加事件(project, "标记任务阻塞", 任务编号=args.任务编号, 原因=args.原因)
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": "任务已阻塞", "任务编号": args.任务编号, "原因": args.原因},
    )


def 命令_解除阻塞(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    task = 查找任务(tasks, args.任务编号)
    if task.get("状态") != "已阻塞":
        raise 循环错误(f"任务 {args.任务编号} 当前状态不是已阻塞：{task.get('状态')}")
    if args.追加尝试次数 < 0:
        raise 循环错误("追加尝试次数不能小于 0")
    task["最大尝试次数"] += args.追加尝试次数
    if task["尝试次数"] >= task["最大尝试次数"]:
        raise 循环错误("解除后仍没有可用尝试次数，请使用 --追加尝试次数")
    task["状态"] = "待返工"
    task["阻塞原因"] = None
    追加事件(
        project,
        "解除任务阻塞",
        任务编号=args.任务编号,
        原因=args.原因,
        追加尝试次数=args.追加尝试次数,
    )
    保存并输出(
        project,
        config,
        state,
        tasks,
        {"结果": "已解除阻塞", "任务编号": args.任务编号, "下一状态": "待返工"},
    )


def 命令_生成进度(args: argparse.Namespace) -> None:
    project = 项目路径(args)
    config, state, tasks = 加载项目(project)
    刷新进度(project, config, state, tasks)
    输出({"结果": "已生成进度", "文件": str(project / 进度文件名)})


def 创建解析器() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JC 项目循环：本地文件顺序状态机")
    parser.add_argument("--项目", required=True, help="项目目录")
    subparsers = parser.add_subparsers(dest="命令", required=True)

    sub = subparsers.add_parser("初始化")
    sub.add_argument("--项目名称")
    sub.add_argument("--目标", required=True)
    sub.add_argument("--完成标准", required=True)
    sub.add_argument("--最大尝试次数", type=int, default=3)
    sub.add_argument("--质量门", action="append")
    sub.set_defaults(handler=命令_初始化)

    sub = subparsers.add_parser("添加任务")
    sub.add_argument("--任务编号")
    sub.add_argument("--标题", required=True)
    sub.add_argument("--说明")
    sub.add_argument("--验收标准", action="append")
    sub.add_argument("--输入文件", action="append")
    sub.add_argument("--期望产物", action="append")
    sub.add_argument("--最大尝试次数", type=int)
    sub.set_defaults(handler=命令_添加任务)

    sub = subparsers.add_parser("导入任务")
    sub.add_argument("--文件", required=True)
    sub.set_defaults(handler=命令_导入任务)

    for name, handler in [
        ("检查", 命令_检查),
        ("状态", 命令_状态),
        ("下一步", 命令_下一步),
        ("领取", 命令_领取),
        ("生成进度", 命令_生成进度),
    ]:
        sub = subparsers.add_parser(name)
        sub.set_defaults(handler=handler)

    sub = subparsers.add_parser("提交")
    sub.add_argument("--任务编号")
    sub.add_argument("--产物", action="append", required=True)
    sub.add_argument("--说明", required=True)
    sub.set_defaults(handler=命令_提交)

    sub = subparsers.add_parser("复核")
    sub.add_argument("--任务编号", required=True)
    sub.add_argument("--结果", choices=["通过", "返工"], required=True)
    sub.add_argument("--复核者", required=True)
    sub.add_argument("--意见", required=True)
    sub.set_defaults(handler=命令_复核)

    sub = subparsers.add_parser("确认质量门")
    sub.add_argument("--名称", required=True)
    sub.add_argument("--确认者", required=True)
    sub.add_argument("--意见", required=True)
    sub.set_defaults(handler=命令_确认质量门)

    sub = subparsers.add_parser("暂停")
    sub.add_argument("--原因", required=True)
    sub.set_defaults(handler=命令_暂停)

    sub = subparsers.add_parser("恢复")
    sub.add_argument("--说明", required=True)
    sub.set_defaults(handler=命令_恢复)

    sub = subparsers.add_parser("停止")
    sub.add_argument("--原因", required=True)
    sub.set_defaults(handler=命令_停止)

    sub = subparsers.add_parser("跳过")
    sub.add_argument("--任务编号", required=True)
    sub.add_argument("--原因", required=True)
    sub.set_defaults(handler=命令_跳过)

    sub = subparsers.add_parser("标记阻塞")
    sub.add_argument("--任务编号", required=True)
    sub.add_argument("--原因", required=True)
    sub.set_defaults(handler=命令_标记阻塞)

    sub = subparsers.add_parser("解除阻塞")
    sub.add_argument("--任务编号", required=True)
    sub.add_argument("--原因", required=True)
    sub.add_argument("--追加尝试次数", type=int, default=0)
    sub.set_defaults(handler=命令_解除阻塞)

    return parser


def main() -> None:
    parser = 创建解析器()
    args = parser.parse_args()
    try:
        args.handler(args)
    except 循环错误 as exc:
        输出({"结果": "失败", "错误": str(exc)}, 2)


if __name__ == "__main__":
    main()
