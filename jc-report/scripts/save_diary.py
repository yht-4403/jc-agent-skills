#!/usr/bin/env python3
"""把已核对的新事实追加到日期日记；重复内容不写入。"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

DEFAULT_DIR = Path('/Users/codemao/Documents/JC知识库/日记')
STATE_DIR = Path.home() / '.local/state/jc-report'


def normalize(text):
    return re.sub(r'\s+', '', text).strip()


def write_state(path, records):
    # 内部记录保存在知识库之外；写完再替换，避免留下半份 JSON。
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump({'records': records}, output, ensure_ascii=False, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save(directory, date, items, source):
    # 锁按目标目录区分，所有 AI 工具调用本脚本时共用同一把锁。
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f'日记目录不存在：{directory}；请先确认路径，不自动另建目录')
    lock_id = hashlib.sha256(str(directory).encode()).hexdigest()
    lock_path = Path(tempfile.gettempdir()) / f'jc-report-{lock_id}.lock'
    target = directory / f'{date}.md'
    state_path = STATE_DIR / lock_id / f'{date}.json'
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.is_symlink():
            raise ValueError('日期文件为符号链接，停止写入以避免修改其他文件')
        old = target.read_text(encoding='utf-8') if target.exists() else ''
        known = normalize(old)
        additions = []
        records = json.loads(state_path.read_text(encoding='utf-8'))['records'] if state_path.exists() else []
        # 兼容旧日记中的标记，新保存的正文不再写入机器信息。
        seen_ids = set(re.findall(r'<!-- jc-report:item:([a-f0-9]{64}) -->', old))
        seen_ids.update(record['id'] for record in records)
        timestamp = dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='minutes')
        source = re.sub(r'[\r\n]+', ' ', source).strip() or '未标注工具'
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('每个 items 元素必须是对象')
            title = str(item.get('title', '')).strip()
            body = str(item.get('body', '')).strip()
            if not title or not body:
                raise ValueError('每个事项必须提供非空 title 和 body')
            # id 代表这次具体事实版本，状态变化须用新 id；不替代语义去重。
            identity = str(item.get('id') or normalize(body))
            digest = hashlib.sha256(identity.encode()).hexdigest()
            if digest in seen_ids or normalize(body) in known:
                continue
            seen_ids.add(digest)
            known += normalize(body)
            # 同日追加时不重复插入已有的日记标题。
            has_title = title in old.splitlines() or any(part.startswith(title + '\n') for part in additions)
            additions.append(body if has_title else f'{title}\n\n{body}')
            records.append({'id': digest, 'source': source, 'saved_at': timestamp})
        if not additions:
            return {'path': str(target), 'added': 0, 'status': '无新内容'}
        block = ('\n' if old else '') + '\n\n'.join(additions) + '\n'
        # 追加保留原文，独占锁覆盖读取、查重、写入和落盘。
        with target.open('a', encoding='utf-8') as output:
            if old and not old.endswith('\n'):
                output.write('\n')
            output.write(block)
            output.flush()
            os.fsync(output.fileno())
        # 日记先落盘；若内部记录写入中断，重试仍能按正文阻止完全相同的重复。
        write_state(state_path, records)
        return {'path': str(target), 'added': len(additions), 'status': '已追加' if old else '已创建'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--date', default=dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    parser.add_argument('--source', default='未标注工具')
    parser.add_argument('--input', type=Path, required=True, help='UTF-8 JSON：含 items 数组')
    args = parser.parse_args()
    date = dt.date.fromisoformat(args.date).isoformat()
    if date != args.date:
        parser.error('日期须使用 YYYY-MM-DD')
    data = json.loads(args.input.read_text(encoding='utf-8'))
    items = data.get('items')
    if not isinstance(items, list):
        parser.error('输入必须包含 items 数组')
    print(json.dumps(save(args.directory, date, items, args.source), ensure_ascii=False))


if __name__ == '__main__':
    main()
