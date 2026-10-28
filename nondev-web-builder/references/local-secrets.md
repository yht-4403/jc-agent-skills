# Local secrets

Use one fixed plaintext file at the project root:

```text
.env.local
```

The user may paste real local credentials there. Codex owns every other storage decision.

## Mandatory setup

Run the bundled script with every required variable name:

```bash
python3 <skill-directory>/scripts/setup_local_env.py \
  --project /absolute/path/to/project \
  --key OPENAI_API_KEY \
  --key DATABASE_URL
```

The script:

- creates or extends `.env.local` without overwriting existing values;
- creates or extends `.env.example` with empty values only;
- adds a managed local-secret block to `.gitignore`;
- restricts `.env.local` permissions to the current user;
- never accepts or prints secret values.

Never create another secret file unless the existing project has a stronger managed secret system and migrating would be unsafe.

## Stack integration

### Next.js

Next.js loads root `.env.local`. Read private values only in server components, route handlers, server actions, or server-only modules:

```ts
const apiKey = process.env.OPENAI_API_KEY;
```

Do not add `NEXT_PUBLIC_` to a secret variable.

### React with Vite

Vite exposes `VITE_*` variables to browser code. They are public configuration and must not hold secrets. If the feature needs a private provider key, add a small Next.js or Python server boundary and keep the key there.

### Python

Load the same root `.env.local` from server startup using the project's configuration library. If none exists, use `python-dotenv` explicitly:

```python
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local", override=False)
```

Adjust the parent depth to the actual project root and validate required variables at startup with a user-readable message. Do not silently run with a missing key.

### Plain HTML

Plain browser code cannot protect a secret. Do not paste a token into HTML or JavaScript. If a private API is required, introduce a local server boundary and document one start command for the user.

## Handoff

- Never include `.env.local` in a repository, handoff archive, screenshot, document, prompt, or final response.
- Include `.env.example` so developers know which variable names are required.
- Transfer real credentials separately only when the user explicitly requests it.
- If the receiving developer needs local access, instruct them to copy `.env.example` to `.env.local` and fill the values.
