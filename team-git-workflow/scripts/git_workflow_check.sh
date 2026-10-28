#!/usr/bin/env bash
set -u

repo="${1:-.}"
cd "$repo" || {
  echo "[error] Cannot enter directory: $repo" >&2
  exit 1
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[error] Not a Git repository: $repo" >&2
  exit 1
fi

root="$(git rev-parse --show-toplevel)"
current_branch="$(git branch --show-current 2>/dev/null || true)"
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
default_remote_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"

echo "== Repository =="
echo "$root"
echo

echo "== Local Rule Files =="
found_rules="false"
for file in \
  "$root/AGENTS.md" \
  "$root/CLAUDE.md" \
  "$root/CONTRIBUTING.md" \
  "$root/README.md" \
  "$root/.github/pull_request_template.md" \
  "$root/.gitlab/merge_request_templates"; do
  if [ -e "$file" ]; then
    found_rules="true"
    echo "$file"
  fi
done
if [ "$found_rules" = "false" ]; then
  echo "<none detected at repository root>"
fi
if [[ "$root" == /Users/cv-project* ]] || [[ "$(pwd)" == /Users/cv-project* ]]; then
  echo "[cv-project] Also read /Users/cv-project/AGENTS.md and /Users/cv-project/harness/索引.md; use team-git-workflow for Git operations."
fi
echo

echo "== Branch =="
echo "current=${current_branch:-detached HEAD}"
echo "upstream=${upstream:-<none>}"
echo "origin_head=${default_remote_branch:-<unknown>}"
echo

echo "== Worktree Status =="
git status -sb
echo

echo "== Local Git Config =="
for key in pull.rebase pull.ff rebase.autoStash fetch.prune merge.ff; do
  value="$(git config --get "$key" 2>/dev/null || true)"
  echo "$key=${value:-<unset>}"
done
echo

if [ -n "$upstream" ]; then
  echo "== Ahead / Behind Upstream =="
  git rev-list --left-right --count "$upstream"...HEAD 2>/dev/null | awk '{print "behind="$1" ahead="$2}'
  echo
fi

echo "== Recent Commits =="
git log --oneline --decorate -n 12
echo

echo "== Recent Merge Commits =="
merge_commits="$(git log --merges --oneline -n 10 2>/dev/null || true)"
if [ -n "$merge_commits" ]; then
  echo "$merge_commits"
else
  echo "<none>"
fi
echo

target="${TARGET_BRANCH:-}"
if [ -n "$target" ]; then
  echo "== Target Branch Check =="
  if git rev-parse --verify "$target" >/dev/null 2>&1; then
    if git merge-base --is-ancestor "$target" HEAD; then
      echo "[ok] $target is an ancestor of HEAD; the target can fast-forward to this branch."
    else
      echo "[warn] $target is not an ancestor of HEAD; rebase the current branch onto $target before ff-only merge."
    fi
    if git merge-base --is-ancestor HEAD "$target"; then
      echo "[info] HEAD is already contained in $target."
    else
      echo "[info] HEAD has commits not contained in $target."
    fi
  else
    echo "[warn] Target branch not found locally: $target"
  fi
  echo
fi

echo "== Guardrail Hints =="
protected_re='^(main|master|dev|develop|test|staging)$'
if [[ "${current_branch:-}" =~ $protected_re ]] || [[ "${current_branch:-}" == release/* ]]; then
  echo "[warn] Current branch looks shared/protected. Do not develop, rebase, or force push here unless the local project explicitly allows it."
fi

if git log --merges --format=%s -n 20 | grep -E "Merge branch '.+' into '(main|master|dev|develop|test|staging)'" >/dev/null 2>&1; then
  echo "[warn] Recent history contains daily-looking merge commits. Prefer feature rebase plus ff-only/squash merge unless these are intentional releases."
else
  echo "[ok] No obvious daily merge-commit smell in the recent merge history."
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "[warn] Worktree has local changes. Do not rebase, merge, or switch branches until the changes are committed, stashed intentionally, or confirmed irrelevant."
else
  echo "[ok] Worktree is clean."
fi
