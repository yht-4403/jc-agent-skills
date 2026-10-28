# Project Adapter

Use this reference when applying the generic workflow to a specific repository or when creating a reusable project Git guide.

## Local Rule Discovery

Before Git operations, search for local rules in this order:

1. User's direct instruction in the current conversation.
2. Nearest `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, or equivalent agent file.
3. `CONTRIBUTING.md`, README, `docs/`, `harness/`, `.github/`, `.gitlab/`, and project scripts.
4. Existing branch and commit history.
5. This skill's generic defaults.

When rules conflict, use the more local and more explicit rule.

## Questions To Resolve Per Project

Identify:

- Default integration branch: `dev`, `develop`, `test`, or another branch.
- Production branch: `main` or `master`.
- Feature branch naming pattern.
- Whether AI branches should use `codex/` or the team's normal feature pattern.
- PR/MR target branch.
- Whether target branches require fast-forward, squash, or rebase merge.
- Whether pushing is allowed by agents or requires user confirmation.
- Required checks before commit and before PR/MR.
- Release and hotfix branch policy.
- Sensitive files that must never be committed.

## Minimal AGENTS.md Git Section

Add or adapt a section like this in project-local docs:

```markdown
## Git Workflow

- Run `git status -sb` before changing branches, committing, rebasing, merging, or pushing.
- Protect user changes. Do not run destructive cleanup commands without explicit permission.
- Start ordinary work from latest `<integration-branch>`.
- Use `<branch-pattern>` for task branches.
- PR/MR target branch is `<integration-branch>`.
- Do not directly push `<production-branch>` or `<integration-branch>`.
- Commit message format: `type(scope): 中文一句话概括`.
- Rebase private feature branches onto the target branch before PR/MR.
- Keep daily history linear; reserve merge commits for release/hotfix boundaries.
- Push only when the user explicitly asks.
- Run `<checks>` before final handoff.
```

## cv-project Adapter

For `/Users/cv-project` and its subprojects:

- Read `/Users/cv-project/AGENTS.md`.
- Read `/Users/cv-project/harness/索引.md`.
- For Git, branch, commit, rebase, push, PR/MR, conflict, or squash work, use `$team-git-workflow`.
- Run `git status -sb` before modification or Git operation.
- Default task target is `dev`.
- Collaborator PR/MR target is `dev`.
- Do not push `dev`, `main`, or `master` unless the project owner explicitly asks for that exact action.
- Do not push at all unless the user explicitly asks.
- Do not use `git add .` by default; stage only task-related files.
- Commit messages are Chinese and should include 2-4 body bullets for non-trivial work.
- AI may merge into `dev`, create/update `release/*`, merge release/hotfix to production, or delete remote branches only when explicitly authorized.
- Final response must state which checks ran and which did not run.

## Forward Porting This Skill To A New Project

For a new repository, create or update the local agent/contribution doc instead of changing the generic skill:

1. Define branch roles and target branches.
2. Define branch naming.
3. Define commit language and format.
4. Define PR/MR body and required checks.
5. Define push and force-push permissions.
6. Define release/hotfix flow.
7. Reference this skill as the generic fallback.

This keeps the skill portable and lets each repository own its stricter local policy.
