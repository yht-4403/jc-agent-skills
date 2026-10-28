# Stack selection

Choose the smallest safe default from observable product needs. Do not ask a non-developer to select the framework.

| Product need | Default | Reason |
| --- | --- | --- |
| Static landing page, event page, simple portfolio | Plain HTML, CSS, and minimal JavaScript | Few dependencies and easy handoff |
| Interactive browser-only tool without private keys or server data | React + TypeScript + Vite | Clear component model without server complexity |
| Login, database, uploads, private API keys, server rendering, or admin tools | Next.js + TypeScript | One project can safely own UI and server behavior |
| AI/data processing, long-running jobs, Python libraries, or an existing Python service | Next.js/React frontend plus a small Python API | Introduce Python only for a concrete capability |

## Defaults

- Use TypeScript for React and Next.js.
- Prefer the package manager already present. For a new JavaScript project, use the current official scaffold and its default package manager unless the environment establishes another standard.
- Use framework defaults before adding state, routing, form, styling, or data-fetching libraries.
- Keep one repository for a small full-stack project unless independent deployment or ownership requires separation.
- Do not migrate an existing working stack merely because another option is fashionable.

## Escalation rules

- A browser must not call a private third-party API with a secret. Move that call behind a Next.js server route or Python endpoint.
- Add Python only when a required library, workload, or existing system justifies it.
- Add a database only when data must survive refreshes or be shared between users/devices.
- Add authentication only when data or actions must be associated with an identity.
- If requirements are still uncertain, implement a reversible UI slice with mock data before committing to backend infrastructure.
