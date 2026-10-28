# Business slicing

Organize code by the user capability it serves, then layer within that feature.

## Decision order

1. Identify the user or business flow.
2. Identify the feature that owns the behavior long term.
3. Keep its UI, state, API access, schemas, types, and tests near one another.
4. Move code to `shared/` only after at least two real features reuse the same stable concept.

## Preferred shape

```text
src/
├── app/                         # framework routes and composition
├── features/
│   ├── core-workflow/
│   │   ├── components/
│   │   ├── screens/
│   │   ├── api.ts
│   │   ├── schema.ts
│   │   ├── types.ts
│   │   └── tests/
│   └── account/
└── shared/
    ├── components/
    ├── lib/
    └── styles/
```

Framework-required files may remain outside `features/`, but keep them thin:

```tsx
// src/app/workspace/page.tsx
import { WorkspaceScreen } from "@/features/core-workflow/screens/workspace-screen";

export default function Page() {
  return <WorkspaceScreen />;
}
```

## Boundary rules

- A feature may use `shared/`; `shared/` must not import a feature.
- One feature should not reach into another feature's internal files. Expose a deliberate public module when cross-feature use is necessary.
- Do not create vague buckets such as `utils`, `helpers`, `misc`, or `common` without a specific domain meaning.
- Keep mock fixtures, debugging code, and production behavior separate.
- Split a complex screen into meaningful components, hooks, configuration, and state only when that improves ownership or comprehension; do not fragment trivial code.
- Name files after business meaning rather than visual position: prefer `item-create-form.tsx` over `left-panel.tsx`.

## Vertical implementation slice

For each feature, complete a usable path before starting another:

```text
route/page
→ user input
→ validation
→ business behavior
→ API or persistence
→ success, empty, loading, and failure states
→ verification
```
