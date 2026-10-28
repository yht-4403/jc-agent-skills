#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-"$ROOT_DIR/dist/skills"}"
VERSION="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 command is required" >&2
  exit 1
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

INNER_DIR="$(mktemp -d)"
trap 'rm -rf "$INNER_DIR"' EXIT

# skill 名 → 分组目录
group_for() {
  case "$1" in
    dbs|dbs-update)
      echo "必装入口" ;;
    dbs-diagnosis|dbs-standard-answer|dbs-theory-grounding|dbs-deconstruct|dbs-goal|dbs-good-question|dbs-jtbd|dbs-action)
      echo "看商业问题" ;;
    dbs-content|dbs-content-value|dbs-video-navigation|dbs-content-risk-check|dbs-benchmark|dbs-title-cover-intro|dbs-ai-check|dbs-plain-writing|dbs-wechat-html|dbs-spread|dbs-resonate|dbs-script-flow|dbs-video-extract)
      echo "做内容" ;;
    dbs-content-system)
      echo "进阶-内容工程" ;;
    dbs-knowledge)
      echo "进阶-知识库" ;;
    dbs-chatroom|dbs-chatroom-austrian)
      echo "进阶-聊天室" ;;
    dbs-save|dbs-restore|dbs-report)
      echo "进阶-状态管理" ;;
    dbs-decision)
      echo "进阶-决策系统" ;;
    dbs-install-skill|dbs-skill-maker)
      echo "进阶-Agent基建" ;;
    dbs-learning)
      echo "进阶-学习" ;;
    *)
      echo "未分组" ;;
  esac
}

build_one() {
  local skill_dir="$1"
  local name
  local group
  local stage_dir
  local target_dir
  local refs

  name="$(basename "$skill_dir")"
  group="$(group_for "$name")"
  target_dir="$INNER_DIR/$group"
  mkdir -p "$target_dir"

  stage_dir="$(mktemp -d)"

  cp "$skill_dir/SKILL.md" "$stage_dir/SKILL.md"

  if [ -d "$skill_dir/templates" ]; then
    mkdir -p "$stage_dir/templates"
    cp -R "$skill_dir/templates/." "$stage_dir/templates/"
  fi

  if [ -d "$skill_dir/scaffold" ]; then
    mkdir -p "$stage_dir/scaffold"
    cp -R "$skill_dir/scaffold/." "$stage_dir/scaffold/"
  fi

  if [ -d "$skill_dir/docs" ]; then
    mkdir -p "$stage_dir/docs"
    cp -R "$skill_dir/docs/." "$stage_dir/docs/"
  fi

  if [ -d "$skill_dir/tools" ]; then
    mkdir -p "$stage_dir/tools"
    cp -R "$skill_dir/tools/." "$stage_dir/tools/"
  fi

  if [ -d "$skill_dir/scripts" ]; then
    mkdir -p "$stage_dir/scripts"
    cp -R "$skill_dir/scripts/." "$stage_dir/scripts/"
  fi

  if [ -d "$skill_dir/agents" ]; then
    mkdir -p "$stage_dir/agents"
    cp -R "$skill_dir/agents/." "$stage_dir/agents/"
  fi

  if [ -d "$skill_dir/references" ]; then
    mkdir -p "$stage_dir/references"
    cp -R "$skill_dir/references/." "$stage_dir/references/"
  fi

  if [ -d "$skill_dir/numbered-prompts" ]; then
    mkdir -p "$stage_dir/numbered-prompts"
    cp -R "$skill_dir/numbered-prompts/." "$stage_dir/numbered-prompts/"
  fi

  if [ -d "$skill_dir/assets" ]; then
    mkdir -p "$stage_dir/assets"
    cp -R "$skill_dir/assets/." "$stage_dir/assets/"
  fi

  refs="$(grep -Eo '知识库/[^`,。 、)]*\.md' "$skill_dir/SKILL.md" || true)"
  if [ -n "$refs" ]; then
    while IFS= read -r ref; do
      [ -n "$ref" ] || continue
      if [ -f "$ROOT_DIR/$ref" ]; then
        mkdir -p "$stage_dir/$(dirname "$ref")"
        cp "$ROOT_DIR/$ref" "$stage_dir/$ref"
      fi
    done <<< "$refs"
  fi

  python3 - "$stage_dir" "$target_dir/${name}.zip" <<'PY'
import os
import sys
import zipfile

source_dir, archive_path = sys.argv[1], sys.argv[2]

with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [dirname for dirname in dirs if dirname != "__pycache__"]
        for filename in files:
            if filename.endswith((".pyc", ".pyo")):
                continue
            path = os.path.join(root, filename)
            archive.write(path, os.path.relpath(path, source_dir))
PY

  rm -rf "$stage_dir"
  echo "built $group/${name}.zip"
}

while IFS= read -r skill_ref; do
  [ -n "$skill_ref" ] || continue
  build_one "$ROOT_DIR/$skill_ref"
done < <(
  python3 - "$ROOT_DIR/.claude-plugin/plugin.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as file:
    manifest = json.load(file)

for skill_ref in manifest.get("skills", []):
    print(skill_ref.removeprefix("./"))
PY
)

cat > "$INNER_DIR/README.md" <<EOF
# dbskill ${VERSION}

Trae Solo 一个 zip 装一个 skill。本压缩包按使用场景分了几个文件夹，按需把里面的 zip 逐个拖进 Trae Solo 的「上传技能」窗口即可。

## 必装入口

- **dbs** — 技能调度台，根据你的问题自动路由到合适的诊断 skill。其他 skill 都依赖它，先装这个。
- **dbs-update** — 更新 dbskill。安装后直接对 Agent 说「更新 dbskill」。

## 看商业问题

- **dbs-diagnosis** — 商业模式诊断（根据用户问题自动选择诊断流程）
- **dbs-theory-grounding** — 理论溯源与案例重释（审查命题、核实理论来源并标明适用边界）
- **dbs-standard-answer** — 理论挖掘与历史同构研究（先找相关领域、作者和理论，再提炼带条件的历史答案）
- **dbs-deconstruct** — 概念拆解（维特根斯坦 + 奥派经济学）
- **dbs-goal** — 目标清晰化（把「我想做个人 IP」这种愿望语法审计成可检查的交付物）
- **dbs-good-question** — 好问题生成器（把模糊问题改成 Agent 可推理、可验证的问题说明书）
- **dbs-jtbd** — JTBD 任务澄清（识别情境中的进展、切换力量与选择标准）
- **dbs-action** — 执行力诊断（阿德勒心理学，「知道该做但就是不做」）

## 做内容

- **dbs-content** — 内容创作诊断
- **dbs-content-risk-check** — 内容发布风险检查（区分机器审核信号与内容实质问题，给出最小修改动作）
- **dbs-benchmark** — 对标分析
- **dbs-title-cover-intro** — 先定选题，再按拍摄状态生成标题、封面文字和视频开头
- **dbs-ai-check** — AI 写作特征识别
- **dbs-plain-writing** — 平铺直叙写作（按事实顺序写产品、功能和更新说明，检查措辞歧义）
- **dbs-wechat-html** — 微信公众号 HTML 生成（15 种经典风格，支持预览和全量生成）
- **dbs-spread** — 传播心理解码
- **dbs-resonate** — 文稿共鸣诊断
- **dbs-video-extract** — 短视频信息提取（查询作品／账号数据并生成语音文字稿）

## 进阶-内容工程

- **dbs-content-system** — 内容结构化系统（把本地大量内容资产搭成可继续生长的内容工程）

## 进阶-知识库

- **dbs-knowledge** — 文件夹知识库（让 Agent 稳定查找、收录、调用和维护本地资料）

## 进阶-聊天室

- **dbs-chatroom** — 定向聊天室（推荐专家或指定人物，多角色对话）
- **dbs-chatroom-austrian** — 奥派经济聊天室（哈耶克 × 米塞斯 × Claude）

## 进阶-状态管理

诊断状态跨会话续接的三件套，攒几次诊断打包成一份报告。

- **dbs-save** — 存档当前诊断
- **dbs-restore** — 恢复上次诊断
- **dbs-report** — 多次存档合并成可交付的 markdown 报告

## 进阶-决策系统

- **dbs-decision** — 决策系统（把重大决策沉淀成 ~/.dbs/decisions/ 下的本地知识工程）

## 进阶-Agent基建

- **dbs-install-skill** — 多端 Skill 安装与同步（安装、查看或卸载本地与外部 Skill）
- **dbs-skill-maker** — Skill 制作与改进（按改动规模先给方案、真实任务对比验证与可选 GitHub 发布）

## 进阶-学习

- **dbs-learning** — 交互式学习（根据上一篇反馈生成下一篇）

---

每个 zip 解压后根级是 SKILL.md（带 YAML frontmatter，含 name + description），格式遵循 Anthropic Skills 规范。
EOF

python3 - "$INNER_DIR" "$OUT_DIR/dbskill-${VERSION}.zip" <<'PY'
import os
import sys
import zipfile

inner_dir, archive_path = sys.argv[1], sys.argv[2]

with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for root, _, files in os.walk(inner_dir):
        for filename in sorted(files):
            path = os.path.join(root, filename)
            archive.write(path, os.path.relpath(path, inner_dir))
PY

echo
echo "done: $OUT_DIR/dbskill-${VERSION}.zip"
