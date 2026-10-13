# Campus Customs Database Harness

This reference describes the starting database in `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is the reset source.

The shop date in the current data is **2026-08-31**, from `desk.date_today`.

## Tables and fields

### `cash_accounts` — 1 row

- `name` TEXT — primary key.
- `balance` REAL.
- `date` TEXT.

Agents use this table to check available cash before preparing or approving an outgoing payment.

### `desk` — 1 row

- `date_today` TEXT.
- `notes` TEXT.

Agents use the shop date and desk notes as shared operating context, especially when checking what is overdue.

### `inventory` — 10 rows

- `sku` TEXT — part of the composite primary key with `size`.
- `name` TEXT.
- `size` TEXT — part of the composite primary key with `sku`.
- `qty` INTEGER.
- `location` TEXT.

Inventory lets agents check stock and shortages for a specific SKU and size.

### `invoices` — 1 row

- `id` INTEGER — primary key.
- `vendor_id` INTEGER — foreign key to `vendors.id`.
- `amount` REAL.
- `due_date` TEXT.
- `status` TEXT.
- `description` TEXT.

Accounting uses invoices to track vendor payables and due dates; an open unpaid invoice prevents that vendor from shipping more product.

### `leases` — 1 row

- `id` INTEGER — primary key.
- `space_name` TEXT.
- `landlord` TEXT.
- `monthly_rent` REAL.
- `next_due` TEXT.
- `notes` TEXT.

Facilities uses lease terms and due dates to handle rent and other shop-space tickets.

### `payments` — 0 rows

- `id` INTEGER — primary key.
- `kind` TEXT.
- `ref_id` INTEGER.
- `amount` REAL.
- `account` TEXT.
- `paid_at` TEXT.
- `approved_by` TEXT.

Payments records outgoing cash and its human approver, giving accounting an audit trail.

### `purchase_orders` — app-managed working-copy table

This table is created in `campus_customs_new.db` on the first PO approval or database reset; it is not added to the original database.

- `id` INTEGER — primary key.
- `ticket_id` INTEGER — foreign key to `tickets.id`.
- `sku` TEXT.
- `size` TEXT.
- `quantity` INTEGER.
- `vendor_id` INTEGER — foreign key to `vendors.id`, selected and confirmed by a human.
- `unit_cost` REAL.
- `amount` REAL — recorded unit cost multiplied by approved quantity.
- `status` TEXT — `approved_draft_unsent` or `paid_unsent`.
- `approved_by` TEXT.
- `approved_at` TEXT — shop date.

It stores a human-approved, unsent purchase-order draft separately from payments; approving a PO does not debit cash, change stock, or contact the vendor.

### `pricing` — 4 rows

- `sku` TEXT — primary key.
- `unit_cost` REAL.
- `list_price` REAL.

Accounting and the boss use cost and list price to assess margins and discount requests.

### `tickets` — 3 rows

- `id` INTEGER — primary key.
- `type` TEXT.
- `requester` TEXT.
- `subject` TEXT.
- `sku` TEXT.
- `size` TEXT.
- `qty` INTEGER.
- `lease_id` INTEGER — foreign key to `leases.id`.
- `invoice_id` INTEGER — foreign key to `invoices.id`.
- `status` TEXT.
- `notes` TEXT.
- `created_at` TEXT.

Tickets are the shared work queue that the boss routes to the specialist agents.

### `vendors` — 3 rows

- `id` INTEGER — primary key.
- `name` TEXT.
- `specialty` TEXT.
- `lead_days` INTEGER.

Inventory and accounting use vendor specialties and lead times to plan restocks and understand shipping constraints.

## Relationships

SQLite declares these foreign keys:

- `invoices.vendor_id` → `vendors.id`.
- `tickets.invoice_id` → `invoices.id`.
- `tickets.lease_id` → `leases.id`.
- `purchase_orders.ticket_id` → `tickets.id`, and `purchase_orders.vendor_id` → `vendors.id` when the app-managed extension table exists.

The product links are represented by matching values rather than declared foreign keys: `tickets.(sku, size)` matches `inventory.(sku, size)`, and `sku` connects `tickets` and `inventory` to `pricing`. `payments` has no declared foreign keys; interpret `kind` and `ref_id` according to the payment workflow rather than assuming SQLite enforces a reference.

## MCP tools

The tools in `mcp_server/server.py` use the working database. Agents receive only the read-only data tools; the FastAPI backend uses the human-approval and reset tools.

### `get_customer_order_context` — ticket 101

- **Tables read:** `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `desk`.
- **Why this ticket:** Ticket 101 requests a white tee in size S, so the tool checks that exact stock row and price, then follows the ticket's invoice to its vendor and shop-date status to show why fulfillment is blocked.

### `get_rent_ticket_context` — ticket 102

- **Tables read:** `tickets`, `leases`, `desk`, `cash_accounts`.
- **Why this ticket:** Ticket 102 points to lease 1, so the tool returns its rent amount and due date alongside the shop date and cash balance needed to prepare a payment request for human approval.

### `get_discount_request_context` — ticket 103

- **Tables read:** `tickets`, `inventory`, `pricing`.
- **Why this ticket:** Ticket 103 asks for 20 navy hoodies in size M, so the tool checks that exact stock count and returns the stored cost and list price for the discount and margin review.

### `list_open_tickets`

- **Tables read:** `tickets`, `desk`.
- **Why this tool:** It gives Boss the current open queue and the shop date it must use to route and prioritize the work.

### `get_inventory_for_sku`

- **Tables read:** `inventory`, `pricing`.
- **Why this tool:** It gives Inventory every stored size and price for one exact SKU, so it can compare ticket demand with size-specific stock without assuming a substitution.

### `list_vendor_capabilities`

- **Tables read:** `vendors`, `invoices`.
- **Why this tool:** It shows each vendor's recorded specialty and lead time together with open unpaid invoices that block shipment; the schema does not map vendors to specific SKUs.

### `assess_invoice_payment`

- **Tables read:** `invoices`, `cash_accounts`, `desk`.
- **Why this tool:** It checks the exact invoice amount and current account balance against the shop date so Accounting can prepare an approval request while leaving payment to a human.

### `assess_lease_payment`

- **Tables read:** `leases`, `cash_accounts`, `desk`.
- **Why this tool:** It checks the recorded rent amount against the current balance and due-date context so Facilities and Accounting can prepare a human-reviewed rent request.

### `list_tickets`

- **Tables read:** `tickets`, `desk`.
- **Why this tool:** It gives the dashboard every ticket's current status and the shop date so it can show whether each ticket is open or resolved.

### `get_cash_balance`

- **Tables read:** `cash_accounts`, `desk`.
- **Why this tool:** It returns the current checking balance the dashboard needs to show before a human reviews an outgoing payment.

### `list_purchase_orders`

- **Tables read:** `purchase_orders`, `vendors` (plus SQLite table metadata when the extension is not yet present).
- **Why this tool:** It lets the dashboard refresh the status of approved unsent PO drafts and display their selected vendor.

### `approve_payment`

- **Tables read and written:** `invoices`, `leases`, `cash_accounts`, `payments`, `tickets`, `purchase_orders`, `vendors`, `desk` (the exact subset depends on payment kind).
- **Why this tool:** FastAPI calls it only after a human approves a specific agent proposal; it rechecks the current recorded amount and funds, writes the payment, and refuses to debit cash below zero.

### `approve_purchase_order`

- **Tables read:** `tickets`, `inventory`, `pricing`, `vendors`, `invoices`, `desk`.
- **Tables written:** `purchase_orders` in the working copy.
- **Why this tool:** After human approval, it records only the ticket's database-supported stock shortfall and unit cost as an unsent PO draft, after checking that the selected vendor has no open unpaid invoice.

### `reset_working_database`

- **Source read:** `data/campus_customs.db` (all original tables).
- **Working copy written:** `data/campus_customs_new.db`; the empty `purchase_orders` extension table is recreated.
- **Why this tool:** It restores the shop data for a fresh run while keeping the original reset database untouched.

## Problem 5 agent team

The PydanticAI agents are in `backend/agents/`; their detailed role instructions are in `backend/prompts/`, one file per role. All five agents use the same fixed model, **`gpt-6-luna` through Portkey**, configured in `backend/provider.py` from `PORTKEY_API_KEY` in the repository-root `.env`. There is no model or provider fallback.

- **Boss** (`backend/agents/boss.py`) reads and triages the board, delegates specialist work, reconciles findings, and returns the final team recommendation.
- **Inventory** (`backend/agents/inventory.py`) checks exact SKU/size stock, calculates known shortfalls, and reports vendor specialty, lead-time, and unpaid-invoice constraints.
- **Accounting** (`backend/agents/accounting.py`) reviews invoices, cash, due dates, recorded costs and prices, and prepares human approval requests.
- **Facilities** (`backend/agents/facilities.py`) handles lease, shop-space, and rent-date analysis with Accounting.
- **Customer Service** (`backend/agents/customer_service.py`) prepares factual customer-message drafts that remain unsent.

Every role receives the eight MCP-backed data tools listed above and can delegate directly to any of the other four roles through `delegate_to_agent`; Boss does not need to relay peer requests. Each delegated report returns to its direct caller. A ticket run starts at Boss for triage, and Boss alone returns the final recommendation. Ticket 102 demonstrates a direct Facilities-to-Accounting handoff. Prompts direct agents to choose a context tool by the ticket's `type`, pass its actual ID, and use general inventory/vendor/payment tools only with identifiers returned by MCP. IDs 101–103 are documented as current examples, not permanent routing rules. If a future type or required lookup is unsupported, the agent must report the missing capability instead of guessing or forcing an unrelated tool. A shared workflow budget caps each run at 12 agent invocations and a delegation depth of 3. Boss may use at most 6 model requests; each specialist may use at most 4. Every agent is limited to 6 model-directed tool calls per run (including MCP calls and delegation). Delegation cycles are rejected.

## Safety and audit guardrails

- **Grounding:** Shop facts come only through MCP. Agents use `desk.date_today`, exact SKU plus size, recorded vendor lead times, and invoice status; they report missing links or proposed prices as unknown. Vendor specialty is not proof of a SKU-specific supply relationship.
- **Money:** Cash only goes out; no revenue is assumed. Payment assessments are read-only. Agents cannot pay, alter `payments`, debit `cash_accounts`, or change invoice status. FastAPI requires a pending agent proposal and a human approver, rechecks the live amount and balance through MCP, and invokes a single SQLite transaction that refuses insufficient funds, duplicate/closed invoice payments, and negative balances. Invoice payments mark the invoice paid but do not fulfill a linked customer order; rent payments advance the lease date and resolve its linked rent ticket.
- **Orders and discounts:** A human-approved PO is stored as an `approved_draft_unsent` record in the working-copy extension table. This does not debit cash, update inventory, resolve a ticket, place an order, or contact a vendor. The selected vendor must have no open unpaid invoice, and a human explicitly confirms the vendor selection because the database has no SKU-to-vendor map. A separate payment approval is required before the PO can debit cash. Discount requests remain uncommitted: the current approval route accepts invoice/rent payments and PO drafts, but does not apply or persist a discount.
- **Contact:** No agent emails, calls, orders from, or otherwise contacts customers, vendors, or the landlord. Message drafts are labeled `draft_only` and stay on the board.
- **Privacy and credentials:** The Portkey key is read from the root `.env`; it is never written into source, tool results, prompts, or audit events. Audit records omit requester, notes, contact, and message recipient/body fields; agent reports are instructed to refer to ticket IDs instead of personal names. Audit permissions are restricted, and long text is bounded.
- **Audit trail:** `output/audit_trail.json` is append-only JSON Lines: each line is one JSON event with time, run and step IDs, role, ticket, delegation, tool arguments/results, report, and usage counters. Task text is represented by a SHA-256 fingerprint and character count. It uses append mode plus a file lock and is never cleared at run start. If audit writing fails, the workflow stops.
- **Token limits:** Use only `gpt-6-luna` through Portkey; keep Boss to at most 6 model requests, each specialist to 4, and every agent to 6 model-directed tool calls. Each workflow is limited to 12 agent invocations and 3 delegation levels; each task is capped at 2,000 characters. Prompts require concise sourced reports; model retries are limited to one.

## Problem 7 FastAPI routes

Run `uvicorn main:app --reload --port 8000` from `homework/hw5/backend/`; the server listens at `http://localhost:8000`. Shop reads and writes route through MCP. The local approval routes are for this homework setup; a real deployment would also require authenticated approver identities and request protections.

- `GET /api/tickets` — returns tickets, their current statuses, and the shop date.
- `POST /api/tickets/{ticket_id}/run` — runs Boss and the delegated agent team for that ticket and returns the reports and any pending approval proposals.
- `GET /api/events?limit=100` — returns recent audit events, including agent reports, delegation events, and MCP tool use.
- `GET /api/approvals` — returns pending and completed human approval proposals from the current backend process.
- `POST /api/approvals/{approval_id}/approve` — records an approved unsent PO draft without changing cash, or executes a separately approved invoice/rent payment.
- `GET /api/purchase-orders` — returns persisted PO drafts and payment state.
- `GET /api/vendors` — returns recorded vendors and open-invoice shipping blocks for a human vendor selection.
- `POST /api/purchase-orders/{purchase_order_id}/pay` — makes a separate human-approved PO payment after rechecking funds.
- `GET /api/cash/checking` — returns the current checking account balance.
- `POST /api/reset` — restores the working database from the untouched original and clears in-memory approval proposals; the audit trail remains append-only.

## Problem 8 React dashboard

`frontend/` contains the React, Vite, and TypeScript board. It reads and acts through the FastAPI endpoints at `http://localhost:8000`; the backend allows the Vite development origin. The board shows the three database tickets, their open/reviewed/resolved distinction, the current checking balance, approval proposals, and per-agent activity with MCP tool names. Agent portraits identify Boss (bulldog), Inventory (golden retriever), Accounting (terrier), Facilities (German shepherd), and Customer Service (cocker spaniel). Delegation events add breed-specific bark bubbles; optional generated audio stays off until enabled. The custom cursor is a white dog-bone silhouette. A ticket is marked resolved only when the backend/database says it is resolved. Payment controls submit an explicit human approval; PO approval is an unsent draft and needs a separate payment action. The user-facing layout and style choices are in `output/design.md`.

## Problem 9 agent run record

The working copy was reset from the untouched original through `POST /api/reset`. The shop date is 2026-08-31 and the starting checking balance was **$3,400.00**. The append-only audit contains the final successful runs below, plus earlier attempts that stopped at the configured usage limit; those attempts were retained rather than removed.

| Ticket | Agent-run result | Current database status after approvals | Agents and delegations | MCP tools used |
| --- | --- | --- | --- | --- |
| 101 | `waiting_for_human` at run completion | `open`; invoice approval settled the bill but did not fulfill the tee order | Boss delegated to Inventory, Accounting, and Customer Service. Customer Service prepared an unsent status draft. | `list_open_tickets`, `get_customer_order_context`, `get_inventory_for_sku`, `list_vendor_capabilities`, `assess_invoice_payment` |
| 102 | `waiting_for_human` at run completion | `resolved` after the approved rent payment | Boss delegated to Facilities and Accounting; Facilities also delegated the payment-capacity check directly to Accounting. | `list_open_tickets`, `get_rent_ticket_context`, `assess_lease_payment` |
| 103 | `needs_information` | `open`; no discount or purchase approval is recorded | Boss delegated to Inventory, Accounting, and Customer Service. Customer Service prepared an unsent update draft. | `list_open_tickets`, `get_discount_request_context`, `list_vendor_capabilities` |

Final run IDs are `5b6aed04-c87c-4e1c-be6b-dc880043085d` (101), `d30abc6d-1d10-417b-a652-b5f34f778fc9` (102), and `566c6068-7dbb-4ade-b4fd-fd8ef962035a` (103). The agent workflow statuses above describe the runs before a human acted. Afterward, Shop manager approved and paid invoice 501 for ticket 101 ($840.00) and lease 1 rent for ticket 102 ($2,400.00), both on 2026-08-31. Ticket 101 stays open because size-S stock remains 0 and no purchase order or fulfillment is recorded. Ticket 102 is resolved and lease 1 now lists 2026-10-02 as its next due date. Ticket 103 still has only 8 of 20 hoodies in stock and has no proposed discount amount or approved purchase.

The two payment records are in `payments`: invoice 501, $840.00, approved by Shop manager; and rent for lease 1, $2,400.00, approved by Shop manager. Cash changed by **−$840.00** for ticket 101, **−$2,400.00** for ticket 102, and **$0.00** for ticket 103. Reconciliation: **$3,400.00 − $840.00 − $2,400.00 − $0.00 = $160.00**, matching `cash_accounts.balance` in `campus_customs_new.db`. No purchase order or hoodie purchase is recorded, and no incoming revenue is assumed.

## Open tickets observed in the starting data

### Ticket 101 — Bulldog tee

- Customer order from Tauhid Zaman for 1 `CC-TEE-WHITE`, size S; status `open`.
- Product link: `tickets.(sku, size)` matches `inventory.(sku, size)`. That size currently has **0** in stock. `pricing.sku` gives unit cost $8 and list price $28.
- Invoice link: `tickets.invoice_id = 501` joins to invoice 501 for $840, status `open`, due 2026-08-28. It belongs to Bulldog Print Co (`vendors.id = 1`, 5-day lead time). The invoice is overdue relative to the shop date, and the unpaid-invoice rule blocks that vendor from shipping.

### Ticket 102 — Rent due

- Rent notice from Elm City Properties; status `open`.
- Lease link: `tickets.lease_id = 1` joins to the Chapel Street shop lease. Monthly rent is $2,400 and `next_due` is 2026-09-02, two days after the shop date.

### Ticket 103 — Bulk hoodie discount

- Price override request from Yale AI Club for 20 `CC-HOOD-NAVY` hoodies, size M; status `open`.
- Product link: SKU and size match the inventory row, which has **8** in stock, a shortfall of **12** if all 20 are needed. `pricing.sku` gives unit cost $22 and list price $58 for the margin review.
