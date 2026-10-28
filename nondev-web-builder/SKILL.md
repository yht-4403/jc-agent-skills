---
name: nondev-web-builder
description: Build, restructure, extend, or hand off small web projects for non-developers using plain HTML, React, Next.js, or an optional Python backend. Use when a user describes a website or web app in business language and needs Codex to choose a sensible stack, organize code by business feature, manage local secrets automatically, maintain project rules and documentation, implement the change, and verify it without asking the user to make technical decisions.
---

# Non-Developer Web Builder

Act as the project's technical owner while keeping product decisions with the user. Translate business language into a small, maintainable implementation and explain outcomes without assuming coding knowledge.

## Operating rules

- Inspect an existing project before asking questions. Preserve its working conventions unless they cause a concrete problem.
- Ask only about product decisions that materially change the result. Decide technical details yourself and briefly explain important tradeoffs.
- Prefer the smallest stack that safely satisfies the requirement. Do not add a backend, database, state library, component system, or deployment service without need.
- Organize new code around business features. Put something in a shared directory only after real cross-feature reuse exists.
- Keep route and page entry files thin. Move business behavior, data access, schemas, state, and substantial UI into the owning feature.
- Never expose credentials in browser code, logs, documentation, screenshots, or final responses.
- Do not expand the requested scope silently. State assumptions and out-of-scope items before substantial implementation.
- Do not claim completion until relevant automated checks and the real user flow have been exercised.

## Workflow

### 1. Understand the product

Establish these facts from the request and repository:

1. Who uses it and what outcome they need.
2. The shortest end-to-end user flow.
3. Whether it needs persistent data, login, file upload, third-party APIs, secrets, or an admin surface.
4. Which parts are required now and explicitly out of scope.
5. How the user will run, review, and hand off the result.

Ask one concise question at a time only when a product decision is genuinely missing. Recommend an answer with each question. Do not ask the user to choose frameworks, folders, state libraries, environment-file names, validation libraries, or test tools.

### 2. Select or confirm the stack

Read [stack-selection.md](references/stack-selection.md). For existing projects, confirm the detected stack and adapt rather than migrating by default.

### 3. Establish project rules

Read [project-rules.md](references/project-rules.md). Create or update a concise root `AGENTS.md` when the project lacks equivalent rules. Preserve unrelated existing instructions and make the managed section easy to identify.

Write a short task contract before substantial changes:

```markdown
## Goal
## Acceptance criteria
## Out of scope
## Assumptions and risks
```

Store it in the existing project documentation system. For a small new project, use `docs/product/current-task.md` and replace it when the task changes rather than accumulating conversation transcripts.

### 4. Organize by business feature

Read [business-slicing.md](references/business-slicing.md) before adding a new feature or reorganizing files. Keep framework-required route files in their conventional locations, but delegate substantial behavior to `features/<business-name>/`.

For frontend implementation, also read [frontend-quality.md](references/frontend-quality.md). For server routes, databases, uploads, authentication, or Python, also read [backend-and-data.md](references/backend-and-data.md).

### 5. Configure local secrets automatically

Whenever the project needs any credential, token, password, private URL, or provider key, read [local-secrets.md](references/local-secrets.md) and run:

```bash
python3 <this-skill-directory>/scripts/setup_local_env.py \
  --project <absolute-project-root> \
  --key REQUIRED_VARIABLE_NAME
```

Pass one `--key` for each required variable. Never ask where secrets should live. Always use the root `.env.local`; automatically maintain `.env.example` and `.gitignore`. Ask the user only to paste the actual values into `.env.local` when Codex cannot obtain them safely.

### 6. Implement in vertical slices

Build one usable path at a time: entry UI, validation, behavior, data/API integration, user-visible success and failure states, and verification. Avoid creating every layer in advance.

When compatible skills are available:

- Use `frontend-design` for substantial visual creation.
- Use `web-design-guidelines` for accessibility and interaction review.
- Use `react-best-practices` for React or Next.js performance-sensitive implementation and review.

These are optional specialists. This skill remains the workflow owner.

### 7. Verify and hand off

Read [completion-and-handoff.md](references/completion-and-handoff.md). Run the project's actual checks and open the relevant page when browser tooling is available. Fix failures caused by the work before reporting completion.

Report in plain language:

- what now works;
- how to run and verify it;
- what checks were run and their results;
- what was not checked and why;
- remaining risks or decisions;
- whether `.env.local` exists and which variable names still need values, never their values.

Do not include `.env.local` in a handoff archive or repository. Include `.env.example` and transfer any real credential separately.
