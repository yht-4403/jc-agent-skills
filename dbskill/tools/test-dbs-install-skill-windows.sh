#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) ;;
  *)
    echo "SKIP: Windows Junction 回归测试只在 Windows Bash／MSYS 环境运行"
    exit 0
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT_DIR/skills/dbs-install-skill/scripts/install-skill.sh"
JUNCTION_HELPER="$ROOT_DIR/skills/dbs-install-skill/scripts/windows-junction.ps1"
TEST_DIR="$(mktemp -d)"
TEST_INSTALL_HOME="$TEST_DIR/install-home"
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

find_powershell() {
  local candidate
  for candidate in pwsh.exe powershell.exe pwsh powershell; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

POWERSHELL="$(find_powershell)" || fail "找不到 PowerShell"
JUNCTION_HELPER_WINDOWS="$(cygpath -aw "$JUNCTION_HELPER")"

run_junction_helper() {
  local action="$1"
  local path="$2"
  local target="${3:-}"
  local path_windows
  local target_windows=""
  local -a arguments

  path_windows="$(cygpath -aw "$path")"
  arguments=(
    -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass
    -File "$JUNCTION_HELPER_WINDOWS" -Action "$action" -Path "$path_windows"
  )
  if [[ -n "$target" ]]; then
    target_windows="$(cygpath -aw "$target")"
    arguments+=(-Target "$target_windows")
  fi

  MSYS2_ARG_CONV_EXCL='*' "$POWERSHELL" "${arguments[@]}"
}

assert_junction() {
  local path="$1"
  local expected="$2"
  local actual_windows
  local actual

  if ! run_junction_helper test "$path"; then
    echo "--- installer output ---" >&2
    sed -n '1,240p' "$OUTPUT" >&2
    echo "--- target directory ---" >&2
    ls -la "$(dirname "$path")" >&2 || true
    fail "$path 应为 Junction"
  fi
  actual_windows="$(run_junction_helper target "$path")"
  actual_windows="${actual_windows//$'\r'/}"
  actual="$(cygpath -au "$actual_windows")"
  actual="$(cd "$actual" && pwd -P)"
  [[ "$actual" == "$expected" ]] || fail "$path 指向错误：$actual"
}

assert_missing() {
  local path="$1"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "$path 应不存在"
}

mkdir -p \
  "$SOURCE_DIR" \
  "$TEST_INSTALL_HOME/.claude" \
  "$TEST_INSTALL_HOME/.workbuddy" \
  "$TEST_INSTALL_HOME/.hermes" \
  "$TEST_INSTALL_HOME/.kiro" \
  "$TEST_INSTALL_HOME/.qwen" \
  "$TEST_INSTALL_HOME/.codex/skills"

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd -P)"
printf '%s\n' '---' 'name: windows-junction-skill' 'description: test' '---' > "$SOURCE_DIR/SKILL.md"
printf '%s\n' 'before' > "$SOURCE_DIR/value.txt"

DBS_INSTALL_HOME="$TEST_INSTALL_HOME" "$SCRIPT" link "$SOURCE_DIR" > "$OUTPUT"

TARGET_DIRS=(
  "$TEST_INSTALL_HOME/.agents/skills"
  "$TEST_INSTALL_HOME/.claude/skills"
  "$TEST_INSTALL_HOME/.workbuddy/skills"
  "$TEST_INSTALL_HOME/.hermes/skills"
  "$TEST_INSTALL_HOME/.kiro/skills"
  "$TEST_INSTALL_HOME/.qwen/skills"
)

for target_dir in "${TARGET_DIRS[@]}"; do
  assert_junction "$target_dir/windows-junction-skill" "$SOURCE_DIR"
done

printf '%s\n' 'after' > "$SOURCE_DIR/value.txt"
for target_dir in "${TARGET_DIRS[@]}"; do
  grep -q '^after$' "$target_dir/windows-junction-skill/value.txt" || \
    fail "$target_dir 没有读取到源目录更新"
done

DBS_INSTALL_HOME="$TEST_INSTALL_HOME" "$SCRIPT" status "$SOURCE_DIR" > "$OUTPUT"
grep -q '未发现冗余入口' "$OUTPUT" || fail "status 未确认 Junction 状态"

run_junction_helper create \
  "$TEST_INSTALL_HOME/.codex/skills/windows-junction-skill" \
  "$SOURCE_DIR"
DBS_INSTALL_HOME="$TEST_INSTALL_HOME" "$SCRIPT" link "$SOURCE_DIR" > "$OUTPUT"
assert_missing "$TEST_INSTALL_HOME/.codex/skills/windows-junction-skill"

DBS_INSTALL_HOME="$TEST_INSTALL_HOME" "$SCRIPT" unlink "$SOURCE_DIR" > "$OUTPUT"
for target_dir in "${TARGET_DIRS[@]}"; do
  assert_missing "$target_dir/windows-junction-skill"
done
[[ -f "$SOURCE_DIR/SKILL.md" ]] || fail "unlink 不应删除源 Skill"

mkdir -p "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill"
printf '%s\n' 'keep' > "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill/local.txt"
if DBS_INSTALL_HOME="$TEST_INSTALL_HOME" "$SCRIPT" link "$SOURCE_DIR" > "$OUTPUT" 2>&1; then
  fail "真实目录冲突时 link 应返回失败"
fi
grep -q '^keep$' "$TEST_INSTALL_HOME/.agents/skills/windows-junction-skill/local.txt" || \
  fail "真实目录没有被保留"
grep -q '旧版 MSYS 生成的实体副本' "$OUTPUT" || fail "未提示旧版 MSYS 实体副本"

echo "PASS: dbs-install-skill Windows Junction 创建、状态、去重与卸载"
