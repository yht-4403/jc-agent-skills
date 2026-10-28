# GitHub And GitLab Settings

## Shared PR/MR Requirements

Each PR/MR should state:

- Source branch and target branch.
- User-visible behavior changes.
- Validation that ran.
- Risk, rollback, data/config/deploy impact.
- Whether it includes database, auth, permission, AI cost, export, upload, or production-sensitive behavior.

Before opening or updating a PR/MR:

```bash
git fetch --all --prune
git switch <source-branch>
git rebase origin/<target-branch>
```

Push only the source branch unless the user explicitly asks for target-branch push.

## GitLab

Prefer:

- Merge method: Fast-forward merge when the team wants strict linear history.
- Squash commits: allow or encourage for noisy feature branches.
- Require pipeline success when CI exists.
- Delete source branch after merge.
- Protect `main` / `master`, and usually protect `dev` / `develop` / `test` / `staging`.
- Disable force push on protected branches.
- Require approval for production-bound branches.

If GitLab cannot fast-forward merge, the source branch has diverged from target. Rebase the source branch on the target branch.

## GitHub

Prefer one of these policies and document it:

- "Squash and merge" for small feature branches where the target branch should stay compact.
- "Rebase and merge" when each feature commit is meaningful and should be preserved linearly.
- "Create a merge commit" only for release/hotfix boundaries or when the team intentionally wants non-linear history.

Repository settings:

- Protect `main` / `master`.
- Require PR before merge.
- Require status checks when CI exists.
- Require conversation resolution when review threads matter.
- Restrict who can push to protected branches.
- Disable force pushes and deletions on protected branches.
- Enable automatic branch deletion after merge if the team wants short-lived branches cleaned up.

## Squash Policy

Squash is useful when:

- The feature branch has noisy trial commits.
- Commit messages are not review-quality.
- Reviewers want one clean target-branch unit.

Squash is not ideal when:

- The branch intentionally has multiple reviewable commits.
- Each commit is independently useful for archaeology or rollback.
- The team needs exact commit-level traceability.

## Merge Commit Policy

Avoid daily feature merge commits.

Accept merge commits for:

- `release/*` into production.
- `hotfix/*` into production.
- Production hotfix back into integration/release branches.
- Long-lived branch boundary that the team intentionally documents.
