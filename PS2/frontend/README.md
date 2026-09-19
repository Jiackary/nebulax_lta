# Nusa Journey Companion frontend

Mobile-first React PWA for the fixed Bedok → Singapore General Hospital journey. The backend remains the authority for route planning, timings, accessibility assessment, disruptions and alternatives.

## Run locally

Start the backend from `PS2/backend` first:

```powershell
$env:PS2_USE_FIXTURES = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then run the frontend from this directory:

```powershell
npm install
npm run dev
```

Vite proxies `/api` and `/openapi.json` to the backend at port 8000. Regenerate committed API types after a backend contract change with `npm run api:generate`.

## Verification

```powershell
npm run lint
npm run typecheck
npm run test:run
npm run build
```

`npm run build` emits an installable PWA shell. It precaches application assets only; API calls stay network-only. A saved offline journey is stored explicitly in IndexedDB after the user chooses **Save written steps offline**.

## Deployment requirements

Serve the frontend and `/api` from the same HTTPS origin. Configure SPA fallback for client routes such as `/trip/:tripId`, but never rewrite `/api/*` to `index.html`. Set `Referrer-Policy: no-referrer` because a trip ID functions as a private access link.

Set `VITE_ENABLE_DEMO=true` only for an isolated demonstration environment. The demo scenario endpoint uses shared server state.

## Current limits

The app does not track location, provide turn-by-turn navigation, choose alternatives, cache base-map tiles, or provide voice output. Push reminders require HTTPS, a configured VAPID backend and a browser that supports service workers and Push API.
