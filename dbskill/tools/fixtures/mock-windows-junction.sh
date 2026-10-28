#!/usr/bin/env bash
set -euo pipefail

action=""
path=""
target=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Action) action="$2"; shift 2 ;;
    -Path) path="$2"; shift 2 ;;
    -Target) target="$2"; shift 2 ;;
    *) shift ;;
  esac
done

marker_name=".dbs-test-junction-target"

entry_identity() {
  local entry="$1"
  local parent

  parent="$(cd "$(dirname "$entry")" && pwd -P)"
  printf '%s/%s\n' "$parent" "$(basename "$entry")"
}

case "$action" in
  create)
    [[ -n "$path" && -n "$target" && ! -e "$path" ]]
    mkdir "$path"
    printf '%s\n' "$target" > "$path/$marker_name"
    ;;
  target)
    [[ -f "$path/$marker_name" ]]
    sed -n '1p' "$path/$marker_name"
    ;;
  remove)
    [[ -f "$path/$marker_name" ]]
    rm "$path/$marker_name"
    rmdir "$path"
    ;;
  test)
    [[ -f "$path/$marker_name" ]]
    ;;
  list)
    [[ -d "$path" ]] || exit 0
    while IFS= read -r marker; do
      (cd "$(dirname "$marker")" && pwd -P)
    done < <(find "$path" -mindepth 2 -maxdepth 2 -name "$marker_name" -type f | sort)
    ;;
  same)
    [[ "$(entry_identity "$path")" == "$(entry_identity "$target")" ]]
    ;;
  under)
    child="$(entry_identity "$path")"
    root="$(entry_identity "$target")"
    [[ "$child" == "$root" || "$child" == "$root"/* ]]
    ;;
  *) exit 2 ;;
esac
