#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/skills/dbs-install-skill/scripts/install-skill.sh"
TEST_DIR="$(mktemp -d)"
TEST_HOME="$TEST_DIR/home"
SOURCE_DIR="$TEST_DIR/source"
GATED_ROOT="$TEST_DIR/gated-project"
THIRD_PARTY_ROOT="$TEST_DIR/third-party"
LINKED_SOURCE="$TEST_DIR/linked-source"
OUTPUT="$TEST_DIR/output.txt"

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_link() {
  local link="$1"
  local expected="$2"
  [[ -L "$link" ]] || fail "$link 应为软链"
  [[ "$(readlink "$link")" == "$expected" ]] || fail "$link 指向错误"
}

assert_missing() {
  local path="$1"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "$path 应不存在"
}

mkdir -p \
  "$TEST_HOME/.agents" \
  "$TEST_HOME/.claude/skills" \
  "$TEST_HOME/.codex/skills" \
  "$TEST_HOME/.cursor/skills" \
  "$TEST_HOME/.kilocode/skills" \
  "$TEST_HOME/.grok" \
  "$SOURCE_DIR/category-prefixed" \
  "$SOURCE_DIR/fallback-name" \
  "$GATED_ROOT/skills/gated-skill" \
  "$THIRD_PARTY_ROOT/skills/third-party-skill" \
  "$LINKED_SOURCE"

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd -P)"
GATED_ROOT="$(cd "$GATED_ROOT" && pwd -P)"
THIRD_PARTY_ROOT="$(cd "$THIRD_PARTY_ROOT" && pwd -P)"
LINKED_SOURCE="$(cd "$LINKED_SOURCE" && pwd -P)"

printf '%s\n' '---' 'name: stable-skill-name' 'description: test' '---' > "$SOURCE_DIR/category-prefixed/SKILL.md"
printf '%s\n' '---' 'description: test' '---' > "$SOURCE_DIR/fallback-name/SKILL.md"
printf '%s\n' '---' 'name: linked-source-skill' 'description: test' '---' > "$LINKED_SOURCE/SKILL.md"
ln -s "$LINKED_SOURCE" "$SOURCE_DIR/symlinked-source"
printf '%s\n' '<!-- skill-interface-gate: required -->' > "$GATED_ROOT/AGENTS.md"
printf '%s\n' '---' 'name: gated-skill' 'description: 用于测试元数据闸门能否阻止缺少界面定义的 Skill 被安装' '---' > "$GATED_ROOT/skills/gated-skill/SKILL.md"
printf '%s\n' '---' 'name: third-party-skill' 'description: test' '---' > "$THIRD_PARTY_ROOT/skills/third-party-skill/SKILL.md"

if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$GATED_ROOT/skills/gated-skill" > "$OUTPUT" 2>&1; then
  fail "启用闸门后，缺少 agents/openai.yaml 的 Skill 应安装失败"
fi
grep -q 'Skill 界面元数据校验失败' "$OUTPUT" || fail "闸门失败时未输出明确原因"

mkdir -p "$GATED_ROOT/skills/gated-skill/agents"
printf '%s\n' \
  'interface:' \
  '  display_name: "gated-skill"' \
  '  short_description: "验证安装器会在链接前检查标准名称、简短说明和默认提示词"' \
  '  default_prompt: "使用 $gated-skill，验证安装前元数据闸门。"' \
  > "$GATED_ROOT/skills/gated-skill/agents/openai.yaml"
DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$GATED_ROOT/skills/gated-skill" > "$OUTPUT"
assert_link "$TEST_HOME/.agents/skills/gated-skill" "$GATED_ROOT/skills/gated-skill"

DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$THIRD_PARTY_ROOT/skills/third-party-skill" > "$OUTPUT"
assert_link "$TEST_HOME/.agents/skills/third-party-skill" "$THIRD_PARTY_ROOT/skills/third-party-skill"

ln -s "$SOURCE_DIR/category-prefixed" "$TEST_HOME/.codex/skills/stable-skill-name"
ln -s "$SOURCE_DIR/category-prefixed" "$TEST_HOME/.cursor/skills/stable-skill-name"
ln -s "$SOURCE_DIR/fallback-name" "$TEST_HOME/.kilocode/skills/fallback-name"
ln -s "$SOURCE_DIR/removed-skill" "$TEST_HOME/.claude/skills/removed-skill"
mkdir -p "$TEST_HOME/.grok/skills/removed-skill"
printf '%s\n' \
  '---' \
  'name: removed-skill' \
  'user_invocable: true' \
  '---' \
  '# removed-skill' \
  '## Grok Bridge' \
  "- Source of truth: $SOURCE_DIR/removed-skill/SKILL.md" \
  > "$TEST_HOME/.grok/skills/removed-skill/SKILL.md"

DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR" > "$OUTPUT"

assert_link "$TEST_HOME/.agents/skills/stable-skill-name" "$SOURCE_DIR/category-prefixed"
assert_link "$TEST_HOME/.agents/skills/fallback-name" "$SOURCE_DIR/fallback-name"
assert_link "$TEST_HOME/.agents/skills/linked-source-skill" "$LINKED_SOURCE"
assert_link "$TEST_HOME/.claude/skills/stable-skill-name" "$SOURCE_DIR/category-prefixed"
assert_link "$TEST_HOME/.claude/skills/fallback-name" "$SOURCE_DIR/fallback-name"
assert_missing "$TEST_HOME/.agents/skills/category-prefixed"
assert_missing "$TEST_HOME/.codex/skills/stable-skill-name"
assert_missing "$TEST_HOME/.cursor/skills/stable-skill-name"
assert_missing "$TEST_HOME/.kilocode/skills/fallback-name"
assert_missing "$TEST_HOME/.claude/skills/removed-skill"
assert_missing "$TEST_HOME/.grok/skills/removed-skill"
assert_missing "$TEST_HOME/.qwen"
[[ -f "$TEST_HOME/.grok/skills/stable-skill-name/SKILL.md" ]] || fail "Grok 适配层未生成"
grep -q '^user_invocable: true$' "$TEST_HOME/.grok/skills/stable-skill-name/SKILL.md" || fail "Grok 适配层缺少 user_invocable"

ln -s "$SOURCE_DIR/category-prefixed" "$TEST_HOME/.codex/skills/stable-skill-name"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" status "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "status 应识别冗余入口"
fi
grep -q '发现冗余入口' "$OUTPUT" || fail "status 未报告冗余入口"

DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR/category-prefixed" > "$OUTPUT"
assert_missing "$TEST_HOME/.codex/skills/stable-skill-name"

ln -s "$SOURCE_DIR/category-prefixed" "$TEST_HOME/.agents/skills/old-stable-name"
DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR" > "$OUTPUT"
assert_missing "$TEST_HOME/.agents/skills/old-stable-name"

mkdir -p "$TEST_HOME/.cursor/skills/stable-skill-name"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "真实目录冲突时 link 应返回失败"
fi
[[ -d "$TEST_HOME/.cursor/skills/stable-skill-name" ]] || fail "真实目录不应被删除"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" status "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "status 应识别公共兼容客户端的真实目录冲突"
fi
grep -q '同名真实目录或文件' "$OUTPUT" || fail "status 未报告真实目录冲突"

rmdir "$TEST_HOME/.cursor/skills/stable-skill-name"
DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" unlink "$SOURCE_DIR" > "$OUTPUT"
assert_missing "$TEST_HOME/.agents/skills/stable-skill-name"
assert_missing "$TEST_HOME/.claude/skills/stable-skill-name"
assert_missing "$TEST_HOME/.grok/skills/stable-skill-name"

mkdir -p "$TEST_DIR/other-source"
ln -s "$TEST_DIR/other-source" "$TEST_HOME/.agents/skills/stable-skill-name"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "指向其他来源的链接冲突时 link 应返回失败"
fi
assert_link "$TEST_HOME/.agents/skills/stable-skill-name" "$TEST_DIR/other-source"

rm "$TEST_HOME/.agents/skills/stable-skill-name"

OTHER_GROK_SOURCE="$TEST_DIR/other-grok-source"
mkdir -p "$OTHER_GROK_SOURCE" "$TEST_HOME/.grok/skills/stable-skill-name"
printf '%s\n' '---' 'name: stable-skill-name' 'description: other' '---' > "$OTHER_GROK_SOURCE/SKILL.md"
printf '%s\n' \
  '---' \
  'name: stable-skill-name' \
  'user_invocable: true' \
  '---' \
  '## Grok Bridge' \
  "- Source of truth: $OTHER_GROK_SOURCE/SKILL.md" \
  > "$TEST_HOME/.grok/skills/stable-skill-name/SKILL.md"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "Grok 适配层指向其他现存真源时 link 应返回失败"
fi
grep -q "$OTHER_GROK_SOURCE/SKILL.md" "$TEST_HOME/.grok/skills/stable-skill-name/SKILL.md" || fail "指向其他真源的 Grok 适配层不应被覆盖"
if DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" unlink "$SOURCE_DIR/category-prefixed" > "$OUTPUT" 2>&1; then
  fail "Grok 适配层指向其他真源时 unlink 应返回失败"
fi
[[ -f "$TEST_HOME/.grok/skills/stable-skill-name/SKILL.md" ]] || fail "指向其他真源的 Grok 适配层不应被删除"
rm -rf "$TEST_HOME/.grok/skills/stable-skill-name"

PRIVATE_COLLECTION="$TEST_DIR/private-collection"
mkdir -p "$PRIVATE_COLLECTION/public-skill" "$PRIVATE_COLLECTION/private"
printf '%s\n' '---' 'name: public-skill' 'description: test' '---' > "$PRIVATE_COLLECTION/public-skill/SKILL.md"
printf '%s\n' '---' 'name: private-only' 'description: test' '---' > "$PRIVATE_COLLECTION/private/SKILL.md"
DBS_INSTALL_HOME="$TEST_HOME" "$SCRIPT" link "$PRIVATE_COLLECTION" > "$OUTPUT"
[[ -L "$TEST_HOME/.agents/skills/public-skill" ]] || fail "集合中的普通 Skill 应被安装"
assert_missing "$TEST_HOME/.agents/skills/private-only"

echo "PASS: dbs-install-skill frontmatter 命名、自动路由、去重、Grok 真源保护与 private 排除"
