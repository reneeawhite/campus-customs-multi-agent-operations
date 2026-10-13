# Campus Customs MCP Server

This FastMCP server is the only source of Campus Customs shop facts and database actions for Codex, the FastAPI backend, and the PydanticAI team. It uses `../data/campus_customs_new.db`, the working copy; reset operations read from `../data/campus_customs.db` and never modify that original. Agents are given only read-only data wrappers. The dashboard-only approval and reset tools perform bounded writes after a human action.

## Tools

- `get_customer_order_context` — for customer order ticket 101; returns its ticket, exact SKU/size stock, pricing, linked invoice, vendor, and shop date.
- `get_rent_ticket_context` — for rent ticket 102; returns its ticket, linked lease, shop date, and cash-account balances.
- `get_discount_request_context` — for discount ticket 103; returns its ticket, exact SKU/size stock, and pricing.
- `list_open_tickets` — returns open ticket rows and `desk.date_today` for Boss triage.
- `get_inventory_for_sku` — returns all recorded sizes and pricing for one exact SKU.
- `list_vendor_capabilities` — returns each vendor's specialty and lead time plus its open unpaid invoices; the database does not map vendors to specific SKUs.
- `assess_invoice_payment` — checks an open invoice amount against a cash account and shop date; reports affordability without paying.
- `assess_lease_payment` — checks the lease rent amount against a cash account and shop date; reports affordability without paying.
- `list_tickets` — returns all ticket records and the shop date so the dashboard can show open and resolved status.
- `get_cash_balance` — returns one named cash-account row and the shop date.
- `list_purchase_orders` — returns human-approved PO drafts and their vendor names; returns an empty list before the extension table exists.
- `approve_purchase_order` — records an approved, unsent PO draft in the working copy. It checks the open ticket's exact SKU/size, shortfall, stored unit cost, vendor record, and open unpaid vendor invoices. A human must confirm the vendor choice because the database has no SKU-to-vendor relationship. This does not spend cash, change stock or ticket status, place an order, or contact a vendor.
- `approve_payment` — after the backend receives a human approval, transactionally records an invoice, rent, or previously approved PO payment in `payments`, debits the selected cash account only if funds suffice, and updates the linked invoice, lease/ticket, or PO state. It refuses duplicate/closed invoice payments and never allows a negative balance.
- `reset_working_database` — restores the working copy from the original using SQLite backup and recreates the empty PO extension table. It leaves `campus_customs.db` untouched.

The ticket-context tools accept an explicit ticket ID and have defaults for the original sample tickets. The SKU, invoice, lease, and payment-capacity tools accept database identifiers or values returned by another MCP tool. Missing linked rows are returned as `null` or an empty list; tools do not fabricate database facts. A positive payment-capacity result is not human approval and does not make a payment. The PydanticAI agents only receive read-only tools; FastAPI calls the write tools after a human approves a specific proposal.

Approved PO drafts are stored in an app-managed `purchase_orders` table added only to the working copy. PO approval is separate from payment: the PO remains unsent and cash unchanged until a later human-approved payment route. No tool sends an order or contacts a customer, vendor, or landlord.
