# Campus Customs Multi-Agent Operations

Campus Customs is a small-shop operations desk with a FastAPI backend, a FastMCP server for database access, a PydanticAI agent team, and a React dashboard. The agents analyze tickets and prepare recommendations or approval requests. Humans approve payments and purchase orders; customer, vendor, and landlord messages remain drafts.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer and npm
- A Portkey API key for agent runs

## Install

From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY`. The backend uses `gpt-6-luna` through Portkey for every agent. Keep `.env` private; it is excluded from Git.

Install the frontend dependencies once:

```sh
cd frontend
npm install
cd ..
```

## Database files and clean runs

- `data/campus_customs.db` is the original reset database.
- `data/campus_customs_new.db` is the working database used by MCP and FastAPI.

To restore the working copy manually, stop the backend and run this from the repository root:

```sh
cp data/campus_customs.db data/campus_customs_new.db
```

Before a full run over tickets 101, 102, and 103, reset the working database. With the backend running, use the reset route:

```sh
curl -X POST http://localhost:8000/api/reset
```

This copies the original database into the working copy through MCP and leaves the original unchanged. The dashboard's current balance and ticket statuses should be refreshed after reset.

## Start the MCP server

The MCP server uses stdio and reads and writes only `data/campus_customs_new.db`. For a standalone MCP client, run it from the repository root in a terminal with the virtual environment active:

```sh
source .venv/bin/activate
python mcp_server/server.py
```

The process waits for an MCP client over stdin/stdout; it does not open an HTTP port. The root `.mcp.json` contains a local stdio connection entry for MCP clients that support project-level configuration. The FastAPI backend also starts its own MCP stdio subprocess for requests, so a separate MCP terminal is only needed when connecting another MCP client such as Codex.

## Start the FastAPI backend

In a second terminal, from the repository root:

```sh
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. It launches the MCP server subprocess when it reads or updates shop data.

## Start the React dashboard

In a third terminal, from the repository root:

```sh
cd frontend
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). The dashboard calls the backend at `http://localhost:8000`.

## Project map

```text
hw5/
├── AI_prompts.md
├── .env.example
├── .gitignore
├── .mcp.json
├── README.md
├── requirements.txt
├── data/
├── mcp_server/
├── backend/
├── frontend/
└── output/
```

The `output/` folder contains the harness, MCP smoke evidence, ticket plans and actuals, cash reconciliation, agent audit trail, and resolved-board screenshots. See `output/harness.md` for the data tables, MCP tools, routes, agent roles, and safety rules.
