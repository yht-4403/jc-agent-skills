# Branching Model

## Branch Responsibilities

Long-lived branches represent environment or release state. Short-lived branches represent task work.

| Branch | Role | Rule |
| --- | --- | --- |
| `main` / `master` | Production line | Protect it. Accept only reviewed and validated release content. Prefer fast-forward when possible. |
| `dev` / `develop` | Daily integration line | Protect or semi-protect it. Features merge here after review and validation. |
| `test` / `staging` | Test environment line | Protect or semi-protect it. Use it when a team has a separate testing environment branch. |
| `feature/*` / `feat/*` | Feature work | Short-lived. Rebase onto the target branch before merge or PR/MR. |
| `fix/*` | Ordinary bug fix | Short-lived. Rebase onto the target branch before merge or PR/MR. |
| `docs/*` | Documentation-only work | Short-lived. Keep it separate from code changes. |
| `refactor/*` | Behavior-preserving internal change | Short-lived. Keep validation explicit because review risk can be high. |
| `release/*` | Release stabilization | Short-lived. Accept only release fixes, version/config updates, and regression fixes. |
| `hotfix/*` | Production emergency fix | Branch from production, then sync the fix back into active integration/release branches. |
| `codex/*` | AI-assisted task branch | Treat as a feature branch unless local project rules say otherwise. |

## Linear History

Daily development should normally end in this shape:

```text
target:  A -> C
feature: A -> C -> B'
final:   A -> C -> B'
```

Use:

```bash
git switch <feature-branch>
git rebase <target-branch>
git switch <target-branch>
git merge --ff-only <feature-branch>
```

This avoids noisy daily merge commits and makes `git bisect`, revert, and review easier.

## Merge Commits

Use explicit merge commits only when the merge itself communicates useful history:

- `release/*` into `main` or `master`.
- `hotfix/*` into `main` or `master`.
- Production hotfix back into `dev`, `develop`, `test`, `staging`, or active `release/*`.
- Long-lived branch boundary that the team intentionally wants to preserve.

Repeated commits like `Merge branch 'dev' into 'main'` are usually process noise unless each one maps to an intentional release event.

## Branch Naming

Use lowercase English and hyphen-separated words:

```text
feat/resume-export-watermark
fix/auth-token-refresh
docs/team-git-workflow
refactor/resume-layout-engine
release/v1.8.0
hotfix/v1.8.1
codex/resume-editor-save-state
```

Keep names short but searchable. Avoid vague names, personal notes, and date-only branches.

## Protected Branches

Protect environment and release branches:

- Deny direct push to `main` / `master`.
- Prefer PR/MR for `dev`, `develop`, `test`, and `staging`.
- Require CI before merge when CI exists.
- Deny force push on all shared branches.
- Require review for production-bound changes.

## cv-project Defaults

For `/Users/cv-project`, local harness rules are authoritative:

- Work normally starts from latest `dev`.
- Collaborator PR/MR target is `dev`.
- Do not directly push `dev`, `main`, or `master`.
- Use `feature/<name>/<task>`, `fix/<name>/<task>`, `docs/<name>/<task>`, `release/<version>`, or `hotfix/<name>/<task>` when the project asks for that naming.
- AI may merge into `dev`, create/update `release/*`, or merge to `main`/`master` only when the project owner explicitly asks.
