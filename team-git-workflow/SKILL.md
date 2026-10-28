---
name: team-git-workflow
description: 通用团队级 Git 协作规范，覆盖仓库本地规则识别、保护用户改动、安全分支创建、worktree 同级目录创建、中文 Conventional Commits、功能分支 rebase、线性历史、PR/MR、GitHub/GitLab 合并策略、release/hotfix 流程和混乱历史诊断。用于创建或检查分支、创建 git worktree、准备 commit、编写 commit message、rebase 功能分支、合并到 dev/main/master、推送前检查、创建 PR/MR、配置仓库协作策略，或把通用 Git 规范适配到当前项目。适用于 /Users/cv-project 时必须先遵守项目 AGENTS.md 和 harness 协作规范。
disable-model-invocation: true
---

# Team Git Workflow

Use this skill to keep a repository's Git history readable, reviewable, and recoverable while obeying the current project's local rules.

## Hard Rules

- Read the repository's nearest `AGENTS.md`, `CLAUDE.md`, README, contribution guide, or Git workflow document before changing branches, committing, rebasing, merging, or pushing.
- For `/Users/cv-project` or its subprojects, read `/Users/cv-project/AGENTS.md` and `/Users/cv-project/harness/索引.md` for project context. Git operations follow this skill unless the current user explicitly gives a stronger instruction.
- Treat project-local rules as stronger than this skill. Use this skill only to fill gaps when local docs are silent.
- Start every Git task with `git status -sb`. Use `git branch -vv`, `git diff --stat`, or the diagnostic script when deciding what is safe.
- Protect user work. Do not run `git reset --hard`, `git checkout -- .`, `git clean -fd`, or broad file rewrites unless the user explicitly asks for that destructive action.
- Do not push unless the user explicitly requests push. Never force push protected branches.
- Rebase only private or clearly owned feature branches. Do not rebase shared target branches such as `main`, `master`, `dev`, `develop`, `test`, `staging`, or `release/*`.
- Create ordinary feature/fix branches from the intended integration target branch, such as `dev`, `develop`, `test`, or the project-defined development branch. Do not create a normal feature branch from `main`/`master` and then merge it back into `dev`/`test`.
- When creating a Git worktree, create the worktree directory next to the current project's root directory. Resolve the project root with `git rev-parse --show-toplevel`, then use a sibling path under `dirname "$PROJECT_ROOT"` such as `../<project-name>-<short-branch-suffix>`. Do not create project worktrees under `.git/`, `.codex/worktrees/`, `/tmp`, the home directory, or an unrelated parent unless the user explicitly asks for that exact location.
- For nested repositories, "next to the project root" means next to that nested repository, not next to the outer handbook/workspace. Example: from `/Users/always-away/rocket/rocketai-crm-frontend`, create `/Users/always-away/rocket/rocketai-crm-frontend-<suffix>`, not `/Users/always-away/rocket-crm-frontend-<suffix>`.
- Treat `main`/`master` as production-stable release branches unless project docs say otherwise. Use them as a base only for release, hotfix, or production-stabilization work.
- Prefer daily linear history: feature branch rebased on target branch, then target branch fast-forwarded or PR/MR merged with a fast-forward/squash policy.
- Before merging, inspect `git log --oneline <target>..<feature>`. If it contains production-branch merge commits, `main`/`master`-only commits, or unrelated work, stop and rebuild the feature branch from the intended target by cherry-pick/rebase.
- Use explicit merge commits only for intentional release, hotfix, or long-lived branch boundary records.

## Decision Guide

1. Inspect readiness or history shape with `scripts/git_workflow_check.sh <repo>`.
2. For branch models, protected branches, and release/hotfix policy, read `references/branching.md`.
3. For commit message format or commit hygiene, read `references/commit-message.md`; validate drafts with `scripts/commit_msg_lint.py`.
4. For concrete local commands, conflict handling, squash, rebase, merge, push, and cleanup steps, read `references/operations.md`.
5. For GitHub/GitLab PR/MR settings, read `references/hosting-platforms.md`.
6. To adapt this workflow into a new project or to apply it to cv-project, read `references/project-adapter.md`.

## Default Flow

For ordinary feature or fix work:

```bash
git status -sb
git fetch --all --prune

git switch <target-branch>
git pull --ff-only
git switch -c <feature-branch>

# work, test, and commit

git fetch --all --prune
git switch <feature-branch>
git rebase origin/<target-branch>

git log --oneline <target-branch>..<feature-branch>

# run project validation
```

Push is a separate step and only allowed when the user explicitly asks:

```bash
git push -u origin <feature-branch>
```

If a fast-forward merge or PR/MR cannot merge cleanly, stop and rebase the feature branch onto the latest target branch. Do not silently fall back to an ordinary merge commit.

## Commit Standard

Use one meaningful commit per reviewable unit. Default format:

```text
type(scope): 中文一句话概括

- 说明核心行为变化
- 说明关键风险处理或兼容逻辑
- 说明验证方式
```

Common types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `build`, `ci`, `style`, `revert`.

## Branch Standard

Use short, searchable branch names:

```text
feat/<domain>-<summary>
fix/<domain>-<summary>
docs/<domain>-<summary>
refactor/<domain>-<summary>
release/v<version>
hotfix/v<version>
codex/<domain>-<summary>
```

AI-created branches default to `codex/` unless the project or user specifies another pattern.

## Worktree Standard

When a task needs a separate working directory, use Git's normal worktree mechanism but put
the checkout next to the repository that is being worked on.

Resolve paths from the current repository, not from an outer workspace:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_PARENT="$(dirname "$PROJECT_ROOT")"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
WORKTREE_PATH="${PROJECT_PARENT}/${PROJECT_NAME}-${BRANCH_SUFFIX}"
```

Create the worktree at that sibling path:

```bash
git fetch origin --prune
git worktree add -b "<feature-branch>" "$WORKTREE_PATH" "origin/<target-branch>"
```

Rules:

- For `/Users/always-away/rocket/rocketai-crm-frontend`, the worktree path should be
  `/Users/always-away/rocket/rocketai-crm-frontend-<suffix>`.
- For `/Users/always-away/rocket/py-rocket-ai-crm-platform`, the worktree path should be
  `/Users/always-away/rocket/py-rocket-ai-crm-platform-<suffix>`.
- For `/Users/always-away/rocket`, the worktree path should be
  `/Users/always-away/rocket-<suffix>`.
- Do not create project worktrees under `.git/`, `.codex/worktrees/`, `/tmp`, the home
  directory, or a sibling of the wrong outer workspace unless the user explicitly asks for
  that exact location.
- Before creating, check `git worktree list`, `git branch --list <feature-branch>`, and
  whether `$WORKTREE_PATH` already exists.

## Report Back

When reporting Git work, include:

- Current branch and intended target branch.
- Whether the worktree is clean and whether unrelated changes exist.
- Whether history is linear or contains daily merge commits.
- Which commits were created, squashed, rebased, merged, or pushed.
- Which tests or checks ran, and which did not run.
- Remaining risk, especially force-push risk, unresolved conflicts, or unverified target-branch containment.
