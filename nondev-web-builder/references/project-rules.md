# Project rules and documentation

Keep the root `AGENTS.md` short. It is the AI's execution contract, not a handbook.

## Required rule categories

Create or preserve rules for:

- product purpose and primary user flow;
- detected stack and package manager;
- allowed source directories and business-feature boundaries;
- commands for development, linting, tests, type checking, and build;
- `.env.local` as the only local secret file;
- prohibition on secrets in browser code, logs, docs, and responses;
- scope control and preservation of existing user changes;
- verification and plain-language handoff expectations.

Use a clearly marked managed section when editing an existing file:

```markdown
<!-- BEGIN: nondev-web-builder -->
...
<!-- END: nondev-web-builder -->
```

Do not overwrite unrelated project rules.

## Small-project documentation

Use only the directories the project needs:

```text
docs/
├── README.md                    # links to current documents
├── product/
│   ├── brief.md                # stable product purpose and users
│   └── current-task.md         # current scope and acceptance criteria
├── decisions/                  # important decisions with lasting impact
└── guides/                     # setup, deployment, or operator instructions
```

Rules:

- Keep current truth, not raw chat transcripts.
- Prefer stable names for living documents.
- Name lasting decisions `YYYY-MM-DD-topic.md` and record context, decision, reason, and consequence.
- Update `docs/README.md` when an important document is added.
- Do not create a document merely to narrate a small code edit.

## Task contract

Before substantial work, record:

```markdown
## Goal

## Acceptance criteria

## Out of scope

## Assumptions and risks
```

Acceptance criteria must describe observable user outcomes, not internal file changes.
