#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_SCRIPT="$ROOT_DIR/skills/dbs/scripts/check-update.sh"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

write_manifest() {
  local path="$1"
  local version="$2"
  local notice="$3"
  printf '{\n  "version": "%s",\n  "notice": "%s"\n}\n' "$version" "$notice" > "$path"
}

assert_contains() {
  local value="$1"
  local expected="$2"
  if [[ "$value" != *"$expected"* ]]; then
    printf '断言失败：输出中缺少 %s\n实际输出：%s\n' "$expected" "$value" >&2
    exit 1
  fi
}

MANIFEST="$TEST_DIR/UPDATE.json"
HOME_ONE="$TEST_DIR/home-one"
mkdir -p "$HOME_ONE"
write_manifest "$MANIFEST" "2.18.22" "新增版本提醒，用户可以先了解主要变化，再用一句回复完成更新。"

OUTPUT="$(HOME="$HOME_ONE" DBS_UPDATE_URL="file://$MANIFEST" bash "$CHECK_SCRIPT" "2.18.21")"
assert_contains "$OUTPUT" "dbskill v2.18.22"
assert_contains "$OUTPUT" "新增版本提醒"
assert_contains "$OUTPUT" "回复 1，我现在帮你更新"

SECOND_OUTPUT="$(HOME="$HOME_ONE" DBS_UPDATE_URL="file://$MANIFEST" bash "$CHECK_SCRIPT" "2.18.21")"
[ -z "$SECOND_OUTPUT" ] || {
  printf '缓存生效后仍然输出提醒：%s\n' "$SECOND_OUTPUT" >&2
  exit 1
}

HOME_TWO="$TEST_DIR/home-two"
mkdir -p "$HOME_TWO/.dbs"
printf '损坏的时间戳\n' > "$HOME_TWO/.dbs/update_check_at"
CORRUPT_CACHE_OUTPUT="$(HOME="$HOME_TWO" DBS_UPDATE_URL="file://$MANIFEST" bash "$CHECK_SCRIPT" "2.18.21")"
assert_contains "$CORRUPT_CACHE_OUTPUT" "dbskill v2.18.22"

HOME_THREE="$TEST_DIR/home-three"
mkdir -p "$HOME_THREE"
write_manifest "$MANIFEST" "2.18.21" "当前版本没有新增提醒，这条内容不应出现在用户回复中。"
SAME_VERSION_OUTPUT="$(HOME="$HOME_THREE" DBS_UPDATE_URL="file://$MANIFEST" bash "$CHECK_SCRIPT" "2.18.21")"
[ -z "$SAME_VERSION_OUTPUT" ] || {
  printf '相同版本错误输出提醒：%s\n' "$SAME_VERSION_OUTPUT" >&2
  exit 1
}

HOME_FOUR="$TEST_DIR/home-four"
mkdir -p "$HOME_FOUR"
printf '{invalid json\n' > "$MANIFEST"
INVALID_OUTPUT="$(HOME="$HOME_FOUR" DBS_UPDATE_URL="file://$MANIFEST" bash "$CHECK_SCRIPT" "2.18.21")"
[ -z "$INVALID_OUTPUT" ] || {
  printf '无效清单错误输出提醒：%s\n' "$INVALID_OUTPUT" >&2
  exit 1
}

printf 'dbskill 更新检查测试通过\n'
