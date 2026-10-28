#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  -awl)
    input="${2:-}"
    parent="$(dirname "$input")"
    if [[ -d "$parent" ]]; then
      input="$(cd "$parent" && pwd -P)/$(basename "$input")"
    fi
    printf '%s\n' "$input"
    ;;
  -aw|-au) printf '%s\n' "$2" ;;
  *) exit 2 ;;
esac
