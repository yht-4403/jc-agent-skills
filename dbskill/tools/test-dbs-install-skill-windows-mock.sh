#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT_DIR/skills/dbs-install-skill/scripts/install-skill.sh"
MOCK_POWERSHELL="$ROOT_DIR/tools/fixtures/mock-windows-junction.sh"
MOCK_CYGPATH="$ROOT_DIR/tools/fixtures/mock-cygpath.sh"
TEST_DIR="$(mktemp -d)"
REAL_INSTALL_HOME="$TEST_DIR/install-home"
TEST_INSTALL_HOME="$TEST_DIR/install-home-alias"
SOURCE_DIR="$TEST_DIR/source/windows-junction-skill"
OUTPUT="$TEST_DIR/output.txt"

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

run_installer() {
  DBS_INSTALL_PLATFORM=windows \
  DBS_INSTALL_HOME="$TEST_INSTALL_HOME" \
  DBS_INSTALL_POWERSHELL="$MOCK_POWERSHELL" \
  DBS_INSTALL_CYGPATH="$MOCK_CYGPATH" \
    "$SCRIPT" "$@"
}

assert_mock_junction() {
  local path="$1"
  local expected="$2"
  [[ -d "$path" && ! -L "$path" ]] || fail "$path 应模拟为 Windows Junction"
  [[ "$(sed -n '1p' "$path/.dbs-test-junction-target")" == "$expected" ]] || \
    fail "$path 指向错误"
}

assert_missing() {
  local path="$1"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "$path 应不存在"
}

mkdir -p \
  "$SOURCE_DIR" \
  "$REAL_INSTALL_HOME/.claude" \
  "$REAL_INSTALL_HOME/.codex/skills"
ln -s "$REAL_INSTALL_HOME" "$TEST_INSTALL_HOME"
SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd -P)"
printf '%s\n' '---' 'name: windows-junction-skill' 'description: test' '---' > "$SOURCE_DIR/SKILL.md"

run_installer link "$SOURCE_DIR" > "$OUTPUT"
assert_mock_junction "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill" "$SOURCE_DIR"
assert_mock_junction "$TEST_INSTALL_HOME/.claude/skills/windows-junction-skill" "$SOURCE_DIR"

run_installer status "$SOURCE_DIR" > "$OUTPUT"
grep -q '未发现冗余入口' "$OUTPUT" || fail "status 未识别 Windows Junction"

run_installer link "$SOURCE_DIR" > "$OUTPUT"
assert_mock_junction "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill" "$SOURCE_DIR"

"$MOCK_POWERSHELL" -Action create \
  -Path "$TEST_INSTALL_HOME/.codex/skills/windows-junction-skill" \
  -Target "$SOURCE_DIR"
run_installer link "$SOURCE_DIR" > "$OUTPUT"
assert_missing "$TEST_INSTALL_HOME/.codex/skills/windows-junction-skill"

run_installer unlink "$SOURCE_DIR" > "$OUTPUT"
assert_missing "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill"
assert_missing "$TEST_INSTALL_HOME/.claude/skills/windows-junction-skill"
[[ -f "$SOURCE_DIR/SKILL.md" ]] || fail "unlink 不应删除源 Skill"

mkdir -p "$TEST_DIR/other-source"
"$MOCK_POWERSHELL" -Action create \
  -Path "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill" \
  -Target "$TEST_DIR/other-source"
if run_installer link "$SOURCE_DIR" > "$OUTPUT" 2>&1; then
  fail "指向其他来源的 Junction 冲突时 link 应返回失败"
fi
assert_mock_junction \
  "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill" \
  "$TEST_DIR/other-source"
"$MOCK_POWERSHELL" -Action remove \
  -Path "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill"

mkdir -p "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill"
printf '%s\n' 'keep' > "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill/local.txt"
if run_installer link "$SOURCE_DIR" > "$OUTPUT" 2>&1; then
  fail "真实目录冲突时 link 应返回失败"
fi
grep -q '^keep$' "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill/local.txt" || \
  fail "真实目录没有被保留"
grep -q '旧版 MSYS 生成的实体副本' "$OUTPUT" || fail "未提示旧版 MSYS 实体副本"

echo "PASS: dbs-install-skill Windows 分支模拟测试"
