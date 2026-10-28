---
name: git-worktree
description: "Git worktree management skill for parallel development with Claude Code. Use when you need to: (1) Create a new worktree for parallel task development, (2) List all active worktrees, (3) Merge a worktree branch back to main using rebase + ff-only strategy, (4) Clean up completed worktrees. Maintains linear git history with rebase workflow."
disable-model-invocation: true
---

# Git Worktree - Parallel Development with Claude Code

## Overview

This skill helps you manage Git worktrees for parallel development. Each worktree is an independent working directory with its own branch, allowing multiple Claude Code sessions to work simultaneously on different tasks.

**Core principle**: rebase to align, ff-only to merge, linear history always.

## Usage

When the user invokes this skill, ask them which operation they want:

1. **create** - Create a new worktree for a task
2. **list** - Show all active worktrees and their status
3. **merge** - Merge a worktree branch back to main
4. **cleanup** - Remove a completed worktree

---

## Operation: create

Create a new worktree for parallel development.

### Steps

1. Ask the user for:
   - Task description (used to generate branch name)
   - Branch type: `feature/`, `bugfix/`, or `hotfix/`

2. Get the project root directory:
```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$PROJECT_ROOT")
```

3. Fetch latest remote:
```bash
git fetch origin
```

4. Generate branch name from task description (lowercase, hyphens, no special chars). For example, task "add interview scoring" becomes `feature/interview-scoring`.

5. Create worktree as a sibling directory:
```bash
# Pattern: ../{project-name}-{short-branch-suffix}
git worktree add "../${PROJECT_NAME}-${BRANCH_SUFFIX}" -b "${BRANCH_TYPE}/${BRANCH_NAME}" origin/main
```

6. Confirm creation and print instructions:
```
Worktree created:
  Path:   /Users/cv-project/jobprep-ai-{suffix}
  Branch: feature/xxx

To start a parallel Claude Code session:
  1. Open a new terminal
  2. cd /Users/cv-project/jobprep-ai-{suffix}
  3. Run: claude
  4. Start working on your task

Current worktree stays unaffected.
```

### Important rules for create
- Always base new worktrees on `origin/main` (latest remote main)
- Never create a worktree on a branch that already has one (check with `git worktree list`)
- Worktree directory is always a sibling of the project root, never nested inside

---

## Operation: list

Show all active worktrees with their status.

### Steps

1. Run:
```bash
git worktree list
```

2. For each worktree, show:
```bash
# For each branch in worktree list
git log --oneline -1 <branch>
git log --oneline main..<branch> | wc -l  # commits ahead
git status --short --porcelain             # uncommitted changes
```

3. Format output as a table:
```
| # | Path                            | Branch              | Commits ahead | Uncommitted |
|---|--------------------------------|---------------------|---------------|-------------|
| 1 | /Users/cv-project/jobprep-ai-main    | bugfix/production   | 23            | 4 files     |
| 2 | /Users/cv-project/jobprep-feature    | feature/interview   | 3             | clean       |
```

---

## Operation: merge

Merge a worktree branch back to main, maintaining linear history.

### Steps

1. Ask which branch to merge (show list from `git worktree list`)

2. Pre-merge checks:
```bash
# Check for uncommitted changes in that worktree
git -C <worktree-path> status --porcelain
```
If dirty, warn the user and ask whether to proceed.

3. Determine merge strategy:
```bash
# Check if main has advanced since branch was created
git fetch origin
git log --oneline origin/main..<branch> | wc -l   # branch commits
git log --oneline <branch>..origin/main | wc -l    # main commits since branch
```

4a. **If main has NO new commits** (fast-forward possible):
```bash
git checkout main
git pull origin main
git merge <branch> --ff-only
git push origin main
```

4b. **If main HAS new commits** (need rebase first):
```bash
# Rebase the branch onto latest main
git -C <worktree-path> fetch origin
git -C <worktree-path> rebase origin/main

# If conflicts, notify user and help resolve
# After rebase, force-push the branch (only if previously pushed)
git -C <worktree-path> push origin <branch> --force-with-lease

# Then ff-only merge
git checkout main
git pull origin main
git merge <branch> --ff-only
git push origin main
```

5. After successful merge, ask if user wants to cleanup the worktree.

### Important rules for merge
- ALWAYS use `--ff-only` for the final merge to main - never create merge commits
- ONLY use `--force-with-lease` (never `--force`) and only on feature branches that were rebased
- NEVER force push to main
- If rebase has conflicts, stop and help the user resolve them before continuing
- Always `git fetch origin` before any merge operation

---

## Operation: cleanup

Remove a completed worktree.

### Steps

1. Show worktree list, ask which to remove

2. Check if the branch has been merged:
```bash
git branch --merged main | grep <branch>
```

3. If NOT merged, warn the user:
```
Warning: branch <branch> has NOT been merged to main.
Removing this worktree will NOT delete the branch, but the working directory will be gone.
Continue? (y/n)
```

4. Remove:
```bash
git worktree remove <worktree-path>
# If branch was merged, also delete the branch
git branch -d <branch>
```

5. Confirm cleanup complete.

---

## Commit conventions

Commits in worktrees follow the same conventions as the main project. No special handling needed - each worktree is a normal git working directory.

```bash
# In any worktree, commits work normally:
git add .
git commit -m "feat: description"
git push origin <branch>
```

## Safety rules

1. **Never force push to main** - main is protected, always ff-only
2. **Never delete a worktree with uncommitted changes** without explicit user confirmation
3. **Never rebase main** - only rebase feature/bugfix branches
4. **Always fetch before merge** - ensure you have the latest remote state
5. **One branch per worktree** - never checkout a different branch in an existing worktree
