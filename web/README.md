# PulseAccess web

Next.js app for the PulseAccess creator and member UI. It talks to the FastAPI
backend through a proxy: `/api/v1/*` → `BACKEND_URL` (default
`http://localhost:8000`), so the browser sees one origin and the refresh
cookie works without CORS.

## Run

```bash
# terminal 1, repo root
.venv/bin/uvicorn app.main:app --port 8000 --reload
# terminal 2, web/
npm install
npm run dev            # http://localhost:3000  (UI kit: /ui)
```

## Check

```bash
npm test               # unit + component tests (Vitest, jsdom)
npm run typecheck
npm run lint
npm run build
```

## API types

Types in `src/lib/api/schema.d.ts` are generated from the backend, so the UI
can't drift from the API. After changing backend schemas:

```bash
python -m scripts.export_openapi   # repo root → web/openapi.json
npm run gen:api                    # web/ → src/lib/api/schema.d.ts
```

## Layout

- `src/lib/api/client.ts`: fetch wrapper (envelope unwrapping, ApiError,
  in-memory tokens, creator refresh-and-retry)
- `src/lib/status.ts`: backend status values → label, tone, icon
- `src/components/ui/`: Button, TextField, StatusBadge, Alert, Spinner, icons
- `src/app/globals.css`: design tokens (light + dark)
