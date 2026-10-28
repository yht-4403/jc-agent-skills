# Completion and handoff

Verification is part of implementation, not a separate workflow the user must invoke.

## Minimum checks

Select checks from the actual project rather than inventing command names:

- dependency installation succeeds;
- type checking succeeds when configured;
- linting succeeds when configured;
- relevant tests succeed;
- production build succeeds;
- the affected page opens;
- the primary user flow works;
- loading, empty, invalid-input, and failure behavior works where relevant;
- browser console and network panel show no unexplained failures;
- narrow and wide layouts remain usable;
- changes stay within the task contract;
- no secret or private user data appears in tracked files or output.

Do not fix unrelated pre-existing failures silently. Identify them and distinguish them from regressions caused by the task.

## Plain-language completion report

Use this order:

1. What now works.
2. How the user starts it.
3. A short manual verification path.
4. Automated checks run and results.
5. Checks not run and why.
6. Remaining risk or human decision.
7. Required `.env.local` variable names that are still empty, never values.

## Safe handoff

Before preparing a repository or archive, exclude:

- `.env.local` and every environment-specific secret file;
- `node_modules/`;
- build caches and generated output such as `.next/`, `dist/`, and coverage artifacts;
- local logs, uploaded private files, and temporary databases unless explicitly required.

Include:

- source code;
- lockfile;
- `.env.example`;
- root `README.md` with start instructions;
- root `AGENTS.md`;
- relevant product and decision documents.

Do not delete the user's local `.env.local` during handoff preparation. Exclude it from the delivered copy.
