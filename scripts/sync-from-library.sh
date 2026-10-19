#!/usr/bin/env bash
# 把本地 Skill 库里的 jc-* 同步到本仓库。
#
# 作者自用脚本。仓库结构本身就是技能本体，不含运行时状态文件
# （active-skills.json / skill-channels.json 之类留在库里，不进 git）。
#
# 用法：
#   ./scripts/sync-from-library.sh          # 同步，展示变更，不提交
#   ./scripts/sync-from-library.sh --commit # 同步并提交
#
# 库路径默认 ~/.cc-switch/skills，可用 JC_SKILL_LIB 覆盖。

set -euo pipefail

LIB="${JC_SKILL_LIB:-$HOME/.cc-switch/skills}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT=0
[[ "${1:-}" == "--commit" ]] && COMMIT=1

if [[ ! -d "$LIB" ]]; then
  echo "错误：找不到 Skill 库 $LIB" >&2
  exit 1
fi

EXCLUDES=(
  --exclude='.DS_Store'
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='.env'
  --exclude='.env.*'
  # jc-skill-installer 的机器级状态：含个人技能清单与本地绝对路径，不跨机器传播
  --exclude='active-skills.json'
  --exclude='source-imports.json'
  --exclude='skill-profiles.json'
  --exclude='skill-channels.json'
  --exclude='runtime-policy.json'
)

synced=0
for src in "$LIB"/jc-*/; do
  [[ -d "$src" ]] || continue
  name="$(basename "$src")"
  # 安全护栏：目标必须落在仓库内的 jc-* 目录
  [[ "$name" == jc-* ]] || continue

  # jc-voice 的 references/ 与 evals/ 在仓库中使用脱敏示例（虚构文案锚点），
  # 本地版本含真实个人文案。只同步规则主干，不回写案例部分，避免私人文案入库。
  if [[ "$name" == "jc-voice" ]]; then
    rsync -a "${EXCLUDES[@]}" "$src/SKILL.md" "$REPO/$name/SKILL.md" 2>/dev/null || true
    echo "  jc-voice：仅同步 SKILL.md，references/ 与 evals/ 保留仓库脱敏版"
    synced=$((synced + 1))
    continue
  fi

  mkdir -p "$REPO/$name"
  rsync -a --delete "${EXCLUDES[@]}" "$src" "$REPO/$name/"
  synced=$((synced + 1))
done
echo "已同步 $synced 个技能 → $REPO"

# rsync 会把本地真实文案覆盖进仓库，这里立即清洗个人与业务信息。
# 脱敏规则放在仓库之外，避免规则本身成为公开内容。
SCRUB="$(dirname "$REPO")/jc-scrub.py"
if [[ -f "$SCRUB" ]]; then
  python3 "$SCRUB" "$REPO"
else
  echo "警告：未找到脱敏脚本 $SCRUB"
  echo "      仓库可能含未脱敏内容，提交前请人工检查，不要直接 push"
fi

# 仓库里有、库里没有的，只提示，不自动删
for dir in "$REPO"/jc-*/; do
  [[ -d "$dir" ]] || continue
  name="$(basename "$dir")"
  [[ -d "$LIB/$name" ]] || echo "提示：$name 在仓库中存在但库里已没有，确认后可手动删除"
done

cd "$REPO"
if [[ -z "$(git status --porcelain)" ]]; then
  echo "无变更。"
  exit 0
fi

echo
git status --short
echo

if [[ $COMMIT -eq 0 ]]; then
  echo "有变更未提交。确认无误后执行：./scripts/sync-from-library.sh --commit"
  exit 0
fi

git add -A
git commit -q -m "chore: 同步技能库更新"
echo "已提交。推送到远端：git push"
