# Campus Customs Corner Desk

The React, Vite, and TypeScript dashboard for monitoring Campus Customs tickets, agent activity, human approvals, and checking cash.

## Start the dashboard

From this folder, install dependencies once and start the Vite development server:

```sh
npm install
npm run dev
```

Vite serves the desk at `http://localhost:5173`. The dashboard calls the FastAPI backend at `http://localhost:8000` by default. Set `VITE_API_BASE_URL` in a local `.env` file if the backend runs at a different address.

Delegated agents can make short, synthesized cartoon barks using the browser's Web Audio API. Audio starts muted; click **Barks off** in the header to enable it. Each breed uses its own pitch and bark rhythm.

Start the backend separately from `../backend/` with `uvicorn main:app --reload --port 8000`.
