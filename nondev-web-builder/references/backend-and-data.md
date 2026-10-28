# Backend and data

Add server complexity only when required by product behavior or secret handling.

## Boundaries

Organize backend code by business domain. A domain may contain its route/controller, input and output schemas, service behavior, persistence adapter, and tests. Put only cross-domain infrastructure in `core`, `platform`, or another explicitly named shared area.

For a small Python API:

```text
backend/app/
├── domains/
│   └── core_workflow/
│       ├── router.py
│       ├── schemas.py
│       ├── service.py
│       └── tests/
└── core/
    ├── config.py
    └── errors.py
```

Do not make a global `services/`, `models/`, and `routers/` layout the default when business ownership would be lost.

## API contract

Before implementing a new frontend/backend boundary, define:

- request fields and validation;
- success response;
- failure codes and user-safe messages;
- authentication and ownership checks;
- compatibility expectations;
- one automated or manual verification path.

Use a consistent failure shape such as:

```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "文件不能超过 10MB",
    "requestId": "req_123"
  }
}
```

Never return stack traces or provider secrets to the browser.

## Data and uploads

- Validate input on the server even when the frontend already validates it.
- Check file type, size, ownership, storage location, and failure cleanup for uploads.
- Do not store user data in logs.
- Make destructive operations explicit and recoverable when practical.
- For schema changes, use the project's migration system. Do not rely on an untracked one-off database command.
- Add authentication only when identity is required; add authorization checks wherever a user reads or changes owned data.

## Errors and logs

- Tell users what they can do next.
- Keep internal error code, request ID, and minimal diagnostic context in server logs.
- Never log complete tokens, cookies, passwords, API keys, uploaded documents, or private response bodies.
- For background work, record start, completion, failure reason, and a traceable job ID.
