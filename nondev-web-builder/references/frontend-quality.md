# Frontend quality

Treat the complete user path as the unit of change.

## Implementation checks

- Keep route files and page shells thin.
- Keep feature-specific components, state, requests, schemas, and types in the owning feature.
- Align routes, UI, request code, input/output types, and error handling together.
- Validate forms before submission and validate again on the server when one exists.
- Provide loading, empty, success, validation-error, network-error, and permission-denied states where applicable.
- Preserve user input after recoverable failures.
- Use semantic HTML, keyboard access, visible focus, meaningful labels, and sufficient contrast.
- Verify responsive behavior at narrow and wide widths.
- Avoid placeholder controls that look interactive but do nothing.
- Avoid giant components that combine data loading, business rules, complex state, and all visual markup.
- Do not introduce a new design system when the project already has a coherent one.

## Browser-visible configuration

- Treat every value available to browser JavaScript as public.
- `NEXT_PUBLIC_*` and `VITE_*` variables are public configuration, never secrets.
- Private provider calls must run in a server route or Python backend.

## Review the real interface

After visual or interaction changes:

1. Start the application using its documented command.
2. Open the affected route.
3. Exercise the primary flow and important failure states.
4. Check browser console and failed network requests.
5. Inspect mobile and desktop widths.

Screenshots alone do not prove interaction correctness.
