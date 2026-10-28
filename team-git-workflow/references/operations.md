# Git Operations

## Inspect Before Acting

Run:

```bash
git status -sb
git branch -vv
git log --oneline --decorate -n 10
```

For a broader read-only diagnostic:

```bash
~/.cc-switch/skills/team-git-workflow/scripts/git_workflow_check.sh .
```

For target-branch readiness:

```bash
TARGET_BRANCH=origin/dev ~/.cc-switch/skills/team-git-workflow/scripts/git_workflow_check.sh .
```

## Start Feature Work

Generic flow:

```bash
git fetch --all --prune
git switch <target-branch>   # ordinary work uses dev/test/etc., not main/master
git pull --ff-only
git switch -c feat/<domain>-<summary>
```

AI-assisted branch when the project has no stronger naming rule:

```bash
git switch -c codex/<domain>-<summary>
```

For `/Users/cv-project`, default to the branch naming and `dev` target described in the harness unless the user says otherwise.

## Base Branch Guard

Before merging a feature branch into `dev`, `test`, or another integration target, verify the feature branch was based on that target rather than `main`/`master`:

```bash
git log --oneline <target-branch>..<feature-branch>
git merge-base --is-ancestor <target-branch> <feature-branch>
```

The range should contain only commits for the current task. If it contains production-branch merge commits such as `Merge branch 'test' into 'master'`, `main`/`master`-only commits, or unrelated work, do not merge it. Rebuild a clean branch from the intended target:

```bash
git switch <target-branch>
git pull --ff-only
git switch -c <clean-feature-branch>
git cherry-pick <task-commit>
```

Use `main`/`master` as a base only for release, hotfix, or production-stabilization work.

## Prepare A Commit

```bash
git status -sb
git diff --stat
git diff
git add <task-files>
git diff --cached --stat
git diff --cached
git commit
```

Do not default to `git add .`. If staging many files, first list them and make sure every file belongs to the task.

Validate a message draft:

```bash
python3 ~/.cc-switch/skills/team-git-workflow/scripts/commit_msg_lint.py /path/to/message.txt
```

## Squash Local Commits

Squash only private task commits that no one else depends on.

If not pushed:

```bash
git status -sb
git reset --soft HEAD~<n>
git commit
```

For deleting, reordering, or splitting commits:

```bash
git rebase -i HEAD~<n>
```

If already pushed, do not force push unless the user explicitly approves and the branch is private or clearly owned.

## Rebase Feature Branch

```bash
git fetch --all --prune
git switch <feature-branch>
git rebase origin/<target-branch>
```

Conflict handling:

```bash
git status
# edit conflict files
git add <resolved-files>
git rebase --continue
```

Use `git rebase --abort` only when the rebase direction or premise was wrong. Do not resolve conflicts by deleting unrelated code.

After rebase, run the relevant project checks before asking for merge or push.

## Fast-Forward Merge

```bash
git switch <target-branch>
git pull --ff-only
git log --oneline <target-branch>..<feature-branch>
git merge --ff-only <feature-branch>
```

If `merge --ff-only` fails, stop and update the feature branch by rebasing it onto the latest target branch. Do not switch to a normal merge unless this is an intentional release/hotfix boundary.

## Push

Push only when the user requested it.

New feature branch:

```bash
git push -u origin <feature-branch>
```

Private branch after rebase, only with approval:

```bash
git push --force-with-lease
```

Never force push protected or shared branches.

## Cleanup Feature Branch

Only delete a branch when the target branch contains the feature branch tip.

Check containment:

```bash
git fetch origin --prune
git branch --contains <feature-branch>
git branch -r --contains <feature-branch>
```

Safe local delete:

```bash
git branch -d <feature-branch>
```

Remote delete only after confirming the remote target branch contains the tip:

```bash
git push origin --delete <feature-branch>
```

## Hotfix

Generic production hotfix:

```bash
git fetch --all --prune
git switch main
git pull --ff-only
git switch -c hotfix/v<version>

# fix, test, commit

git switch main
git merge --no-ff hotfix/v<version>
```

Then sync the hotfix back into active integration branches:

- Cherry-pick a single clear fix.
- Merge the hotfix branch when preserving release context matters.
- Rebase active feature branches after the fix reaches their target branch.

## Release

When a stabilization branch is needed:

```bash
git switch <source-branch>
git pull --ff-only
git switch -c release/v<version>

# release-only fixes, config, version bump, validation

git switch main
git merge --no-ff release/v<version>
```

If the release branch has no extra release commits and production is simply catching up to a tested branch, prefer fast-forward:

```bash
git switch main
git pull --ff-only
git merge --ff-only <tested-branch>
```

## Recommended Local Config

Use repository-level config when you work across teams with different conventions:

```bash
git config pull.rebase true
git config pull.ff only
git config rebase.autoStash true
git config fetch.prune true
```

`pull.ff only` prevents accidental pull-created merge commits. `fetch.prune true` removes stale remote-tracking branches.
