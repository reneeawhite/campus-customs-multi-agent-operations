"""MCP data tools and human-approved database actions for Campus Customs."""

from contextlib import contextmanager
import calendar
from datetime import date
import math
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Literal

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Campus Customs")
DATABASE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
)
ORIGINAL_DATABASE_PATH = DATABASE_PATH.with_name("campus_customs.db")


@contextmanager
def _open_database() -> Iterator[sqlite3.Connection]:
    """Open only the working copy, in SQLite read-only mode."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Campus Customs working database not found: {DATABASE_PATH}")

    connection = sqlite3.connect(f"{DATABASE_PATH.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _open_database_for_write() -> Iterator[sqlite3.Connection]:
    """Open the working copy for a short, transaction-safe human action."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Campus Customs working database not found: {DATABASE_PATH}")

    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _one(
    connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...] = ()
) -> dict[str, Any] | None:
    row = connection.execute(query, parameters).fetchone()
    return dict(row) if row is not None else None


def _many(
    connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def _ticket(
    connection: sqlite3.Connection, ticket_id: int, expected_type: str
) -> dict[str, Any]:
    ticket = _one(connection, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} was not found in the database.")
    if ticket["type"] != expected_type:
        raise ValueError(
            f"Ticket {ticket_id} has type {ticket['type']!r}; "
            f"expected {expected_type!r}."
        )
    return ticket


def _shop_date(connection: sqlite3.Connection) -> str | None:
    row = _one(connection, "SELECT date_today FROM desk LIMIT 1")
    return row["date_today"] if row is not None else None


def _following_month(iso_date: str) -> str:
    try:
        current = date.fromisoformat(iso_date)
    except ValueError as exc:
        raise ValueError("The lease next_due date is not a valid ISO date.") from exc
    month_index = current.year * 12 + current.month
    year, month_zero_based = divmod(month_index, 12)
    month = month_zero_based + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def _ensure_purchase_orders_table(connection: sqlite3.Connection) -> None:
    """Create the working-copy-only table for human-approved, unsent PO drafts."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS purchase_orders (
               id INTEGER PRIMARY KEY,
               ticket_id INTEGER NOT NULL REFERENCES tickets(id),
               sku TEXT NOT NULL,
               size TEXT NOT NULL,
               quantity INTEGER NOT NULL CHECK (quantity > 0),
               vendor_id INTEGER NOT NULL REFERENCES vendors(id),
               unit_cost REAL NOT NULL CHECK (unit_cost > 0),
               amount REAL NOT NULL CHECK (amount > 0),
               status TEXT NOT NULL CHECK (status IN ('approved_draft_unsent', 'paid_unsent')),
               approved_by TEXT NOT NULL,
               approved_at TEXT NOT NULL
           )"""
    )


@mcp.tool()
def get_customer_order_context(ticket_id: int = 101) -> dict[str, Any]:
    """Read the customer order, exact SKU/size stock and price, and its linked invoice/vendor."""
    with _open_database() as connection:
        ticket = _ticket(connection, ticket_id, "customer_order")
        inventory = _one(
            connection,
            "SELECT * FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        )
        pricing = _one(
            connection,
            "SELECT * FROM pricing WHERE sku = ?",
            (ticket["sku"],),
        )
        invoice = (
            _one(
                connection,
                "SELECT * FROM invoices WHERE id = ?",
                (ticket["invoice_id"],),
            )
            if ticket["invoice_id"] is not None
            else None
        )
        vendor = (
            _one(
                connection,
                "SELECT * FROM vendors WHERE id = ?",
                (invoice["vendor_id"],),
            )
            if invoice is not None
            else None
        )
        return {
            "ticket": ticket,
            "shop_date": _shop_date(connection),
            "inventory": inventory,
            "pricing": pricing,
            "invoice": invoice,
            "vendor": vendor,
        }


@mcp.tool()
def get_rent_ticket_context(ticket_id: int = 102) -> dict[str, Any]:
    """Read a rent ticket, its linked lease, shop date, and cash-account balances."""
    with _open_database() as connection:
        ticket = _ticket(connection, ticket_id, "rent_notice")
        lease = (
            _one(
                connection,
                "SELECT * FROM leases WHERE id = ?",
                (ticket["lease_id"],),
            )
            if ticket["lease_id"] is not None
            else None
        )
        accounts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM cash_accounts ORDER BY name"
            ).fetchall()
        ]
        return {
            "ticket": ticket,
            "shop_date": _shop_date(connection),
            "lease": lease,
            "cash_accounts": accounts,
        }


@mcp.tool()
def get_discount_request_context(ticket_id: int = 103) -> dict[str, Any]:
    """Read a discount ticket with stock for its exact SKU/size and the SKU's stored prices."""
    with _open_database() as connection:
        ticket = _ticket(connection, ticket_id, "price_override")
        inventory = _one(
            connection,
            "SELECT * FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        )
        pricing = _one(
            connection,
            "SELECT * FROM pricing WHERE sku = ?",
            (ticket["sku"],),
        )
        return {
            "ticket": ticket,
            "inventory": inventory,
            "pricing": pricing,
        }


@mcp.tool()
def list_open_tickets() -> dict[str, Any]:
    """List the open ticket board and the shop date from the working database."""
    with _open_database() as connection:
        tickets = _many(
            connection,
            "SELECT * FROM tickets WHERE lower(status) = 'open' ORDER BY id",
        )
        return {"shop_date": _shop_date(connection), "tickets": tickets}


@mcp.tool()
def list_tickets() -> dict[str, Any]:
    """Return all ticket IDs and their current statuses for the dashboard."""
    with _open_database() as connection:
        tickets = _many(connection, "SELECT * FROM tickets ORDER BY id")
        return {"shop_date": _shop_date(connection), "tickets": tickets}


@mcp.tool()
def get_cash_balance(account_name: str = "checking") -> dict[str, Any]:
    """Read one cash account balance from the working database."""
    with _open_database() as connection:
        account = _one(
            connection,
            "SELECT * FROM cash_accounts WHERE name = ?",
            (account_name,),
        )
        if account is None:
            raise ValueError(f"Cash account {account_name!r} was not found in the database.")
        return {"account": account, "shop_date": _shop_date(connection)}


@mcp.tool()
def list_purchase_orders() -> dict[str, Any]:
    """List approved purchase-order drafts without contacting vendors or paying them."""
    with _open_database() as connection:
        has_table = _one(
            connection,
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'purchase_orders'",
        )
        orders = (
            _many(
                connection,
                """SELECT po.*, vendors.name AS vendor_name
                   FROM purchase_orders AS po
                   JOIN vendors ON vendors.id = po.vendor_id
                   ORDER BY po.id""",
            )
            if has_table
            else []
        )
        return {"purchase_orders": orders}


@mcp.tool()
def approve_purchase_order(
    ticket_id: int,
    sku: str,
    size: str,
    quantity: int,
    vendor_id: int,
    approved_by: str,
    vendor_match_confirmed: bool,
) -> dict[str, Any]:
    """Record a human-approved unsent PO draft; this does not pay or contact a vendor."""
    approver = approved_by.strip()
    if not approver or len(approver) > 120:
        raise ValueError("approved_by must identify the human approver (1 to 120 characters).")
    if not vendor_match_confirmed:
        raise ValueError(
            "A human must confirm the vendor choice; the database does not map vendors to SKUs."
        )
    if ticket_id <= 0 or vendor_id <= 0 or quantity <= 0:
        raise ValueError("ticket_id, vendor_id, and quantity must be positive integers.")
    if not sku.strip() or not size.strip():
        raise ValueError("sku and size must be non-empty database values.")

    with _open_database_for_write() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_purchase_orders_table(connection)
        ticket = _one(connection, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        if ticket is None:
            raise ValueError(f"Ticket {ticket_id} was not found in the database.")
        if ticket["status"].casefold() != "open":
            raise ValueError("A purchase order can only be prepared for an open ticket.")
        if ticket["type"] not in {"customer_order", "price_override"}:
            raise ValueError("This ticket type does not request a stocked product.")
        if ticket["sku"] != sku or ticket["size"] != size:
            raise ValueError("The SKU and size must match the open ticket exactly.")
        if ticket["qty"] is None:
            raise ValueError("The ticket has no requested quantity.")

        stock = _one(
            connection,
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        )
        if stock is None:
            raise ValueError("No exact SKU/size inventory row exists; refusing to guess a shortfall.")
        shortage = max(0, int(ticket["qty"]) - int(stock["qty"]))
        if shortage == 0:
            raise ValueError("The recorded stock covers the ticket; no restock PO is needed.")
        if quantity != shortage:
            raise ValueError(f"Quantity must equal the database-supported shortfall of {shortage}.")

        pricing = _one(connection, "SELECT unit_cost FROM pricing WHERE sku = ?", (sku,))
        if pricing is None:
            raise ValueError("No recorded unit cost exists; refusing to invent a purchase amount.")
        unit_cost = float(pricing["unit_cost"])
        amount = unit_cost * quantity
        if not math.isfinite(unit_cost) or unit_cost <= 0 or not math.isfinite(amount):
            raise ValueError("The recorded unit cost is invalid; refusing to prepare this PO.")

        vendor = _one(connection, "SELECT * FROM vendors WHERE id = ?", (vendor_id,))
        if vendor is None:
            raise ValueError(f"Vendor {vendor_id} was not found in the database.")
        open_invoice = _one(
            connection,
            """SELECT id FROM invoices
               WHERE vendor_id = ? AND lower(status) = 'open'
               ORDER BY due_date, id LIMIT 1""",
            (vendor_id,),
        )
        if open_invoice is not None:
            raise ValueError(
                f"Vendor {vendor_id} has an open unpaid invoice and cannot ship new product."
            )
        duplicate = _one(
            connection,
            """SELECT id FROM purchase_orders
               WHERE ticket_id = ? AND sku = ? AND size = ?
                 AND status IN ('approved_draft_unsent', 'paid_unsent')
               ORDER BY id LIMIT 1""",
            (ticket_id, sku, size),
        )
        if duplicate is not None:
            raise ValueError(f"An active unsent PO already exists: {duplicate['id']}.")

        shop_date = _shop_date(connection)
        if not shop_date:
            raise ValueError("desk.date_today is missing; refusing to approve a PO.")
        cursor = connection.execute(
            """INSERT INTO purchase_orders
               (ticket_id, sku, size, quantity, vendor_id, unit_cost, amount,
                status, approved_by, approved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'approved_draft_unsent', ?, ?)""",
            (ticket_id, sku, size, quantity, vendor_id, unit_cost, amount, approver, shop_date),
        )
        return {
            "purchase_order": {
                "id": cursor.lastrowid,
                "ticket_id": ticket_id,
                "sku": sku,
                "size": size,
                "quantity": quantity,
                "vendor_id": vendor_id,
                "vendor_name": vendor["name"],
                "vendor_specialty": vendor["specialty"],
                "unit_cost": unit_cost,
                "amount": amount,
                "status": "approved_draft_unsent",
                "approved_by": approver,
                "approved_at": shop_date,
            },
            "cash_changed": False,
            "vendor_contacted": False,
            "inventory_changed": False,
            "human_confirmed_vendor_selection": True,
        }


@mcp.tool()
def get_inventory_for_sku(sku: str) -> dict[str, Any]:
    """Read every size row and stored pricing for one exact SKU."""
    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("sku must be a non-empty value from a ticket or database record.")
    with _open_database() as connection:
        return {
            "sku": sku,
            "inventory": _many(
                connection,
                "SELECT * FROM inventory WHERE sku = ? ORDER BY size",
                (sku,),
            ),
            "pricing": _one(
                connection,
                "SELECT * FROM pricing WHERE sku = ?",
                (sku,),
            ),
        }


@mcp.tool()
def list_vendor_capabilities() -> dict[str, Any]:
    """List vendor specialties, lead times, and open invoices that block new shipments."""
    with _open_database() as connection:
        vendors = _many(connection, "SELECT * FROM vendors ORDER BY id")
        result = []
        for vendor in vendors:
            open_invoices = _many(
                connection,
                """SELECT id, amount, due_date, status, description
                   FROM invoices WHERE vendor_id = ? AND lower(status) = 'open'
                   ORDER BY due_date, id""",
                (vendor["id"],),
            )
            result.append(
                {
                    "vendor": vendor,
                    "open_unpaid_invoices": open_invoices,
                    "can_ship_new_product": not open_invoices,
                }
            )
        return {"vendors": result}


@mcp.tool()
def assess_invoice_payment(
    invoice_id: int, account_name: str = "checking"
) -> dict[str, Any]:
    """Check funds for an open invoice without paying it; human approval is still required."""
    with _open_database() as connection:
        invoice = _one(connection, "SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        if invoice is None:
            raise ValueError(f"Invoice {invoice_id} was not found in the database.")
        account = _one(
            connection,
            "SELECT * FROM cash_accounts WHERE name = ?",
            (account_name,),
        )
        if account is None:
            raise ValueError(f"Cash account {account_name!r} was not found in the database.")
        amount = float(invoice["amount"])
        balance = float(account["balance"])
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"Invoice {invoice_id} has an invalid payment amount.")
        if not math.isfinite(balance) or balance < 0:
            raise ValueError(f"Cash account {account_name!r} has an invalid balance.")
        is_open = invoice["status"].casefold() == "open"
        sufficient = is_open and balance >= amount
        return {
            "invoice": invoice,
            "account": account,
            "shop_date": _shop_date(connection),
            "can_cover_amount": sufficient,
            "assessment": (
                "invoice_not_open"
                if not is_open
                else "funds_sufficient_human_approval_required"
                if sufficient
                else "insufficient_funds"
            ),
            "balance_after_if_approved": balance - amount if sufficient else None,
            "shortfall_if_open": max(0.0, amount - balance) if is_open else None,
            "human_approval_required": True,
            "payment_made": False,
        }


@mcp.tool()
def assess_lease_payment(
    lease_id: int, account_name: str = "checking"
) -> dict[str, Any]:
    """Check funds for the lease's next rent amount without paying it; human approval is required."""
    with _open_database() as connection:
        lease = _one(connection, "SELECT * FROM leases WHERE id = ?", (lease_id,))
        if lease is None:
            raise ValueError(f"Lease {lease_id} was not found in the database.")
        account = _one(
            connection,
            "SELECT * FROM cash_accounts WHERE name = ?",
            (account_name,),
        )
        if account is None:
            raise ValueError(f"Cash account {account_name!r} was not found in the database.")
        amount = float(lease["monthly_rent"])
        balance = float(account["balance"])
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"Lease {lease_id} has an invalid rent amount.")
        if not math.isfinite(balance) or balance < 0:
            raise ValueError(f"Cash account {account_name!r} has an invalid balance.")
        sufficient = balance >= amount
        return {
            "lease": lease,
            "account": account,
            "shop_date": _shop_date(connection),
            "amount_checked": amount,
            "can_cover_amount": sufficient,
            "assessment": (
                "funds_sufficient_human_approval_required"
                if sufficient
                else "insufficient_funds"
            ),
            "balance_after_if_approved": balance - amount if sufficient else None,
            "shortfall": max(0.0, amount - balance),
            "human_approval_required": True,
            "payment_made": False,
        }


@mcp.tool()
def approve_payment(
    kind: Literal["invoice", "rent", "purchase_order"],
    reference_id: int,
    approved_by: str,
    account_name: str = "checking",
) -> dict[str, Any]:
    """Execute a human-approved invoice, rent, or approved-PO payment atomically."""
    approver = approved_by.strip()
    if not approver or len(approver) > 120:
        raise ValueError("approved_by must identify the human approver (1 to 120 characters).")
    if reference_id <= 0:
        raise ValueError("reference_id must be a positive database ID.")

    with _open_database_for_write() as connection:
        connection.execute("BEGIN IMMEDIATE")
        shop_date = _shop_date(connection)
        if not shop_date:
            raise ValueError("desk.date_today is missing; refusing to make a payment.")

        if kind == "invoice":
            payable = _one(
                connection,
                "SELECT * FROM invoices WHERE id = ?",
                (reference_id,),
            )
            if payable is None:
                raise ValueError(f"Invoice {reference_id} was not found in the database.")
            if payable["status"].casefold() != "open":
                raise ValueError(f"Invoice {reference_id} is not open and cannot be paid again.")
            amount = float(payable["amount"])
            payment_kind = "invoice"
            payment_reference = reference_id
        elif kind == "rent":
            payable = _one(
                connection,
                "SELECT * FROM leases WHERE id = ?",
                (reference_id,),
            )
            if payable is None:
                raise ValueError(f"Lease {reference_id} was not found in the database.")
            rent_ticket = _one(
                connection,
                """SELECT id FROM tickets
                   WHERE lease_id = ? AND lower(type) = 'rent_notice'
                     AND lower(status) = 'open'
                   ORDER BY id LIMIT 1""",
                (reference_id,),
            )
            if rent_ticket is None:
                raise ValueError("There is no open rent ticket linked to this lease.")
            if payable["next_due"] is None:
                raise ValueError(f"Lease {reference_id} has no next_due date.")
            amount = float(payable["monthly_rent"])
            payment_kind = "rent"
            payment_reference = reference_id
        else:
            _ensure_purchase_orders_table(connection)
            payable = _one(
                connection,
                "SELECT * FROM purchase_orders WHERE id = ?",
                (reference_id,),
            )
            if payable is None:
                raise ValueError(f"Purchase order {reference_id} was not found in the database.")
            if payable["status"] != "approved_draft_unsent":
                raise ValueError(
                    f"Purchase order {reference_id} is not awaiting payment."
                )
            vendor_invoice = _one(
                connection,
                """SELECT id FROM invoices
                   WHERE vendor_id = ? AND lower(status) = 'open'
                   ORDER BY due_date, id LIMIT 1""",
                (payable["vendor_id"],),
            )
            if vendor_invoice is not None:
                raise ValueError(
                    "The vendor now has an open unpaid invoice; payment refused until reviewed."
                )
            amount = float(payable["amount"])
            payment_kind = "purchase_order"
            payment_reference = reference_id

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("The recorded payment amount is invalid; refusing to pay.")
        account = _one(
            connection,
            "SELECT * FROM cash_accounts WHERE name = ?",
            (account_name,),
        )
        if account is None:
            raise ValueError(f"Cash account {account_name!r} was not found in the database.")
        balance = float(account["balance"])
        if not math.isfinite(balance) or balance < 0 or balance < amount:
            raise ValueError("Insufficient cash; payment refused and no negative balance is allowed.")

        updated = connection.execute(
            "UPDATE cash_accounts SET balance = balance - ? WHERE name = ? AND balance >= ?",
            (amount, account_name, amount),
        )
        if updated.rowcount != 1:
            raise ValueError("Cash changed during approval; payment refused. Refresh the balance.")
        connection.execute(
            """INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (payment_kind, payment_reference, amount, account_name, shop_date, approver),
        )

        if kind == "invoice":
            changed = connection.execute(
                "UPDATE invoices SET status = 'paid' WHERE id = ? AND lower(status) = 'open'",
                (reference_id,),
            )
            if changed.rowcount != 1:
                raise ValueError("Invoice status changed during approval; payment rolled back.")
        elif kind == "rent":
            next_due = _following_month(payable["next_due"])
            connection.execute(
                "UPDATE leases SET next_due = ? WHERE id = ?",
                (next_due, reference_id),
            )
            connection.execute(
                "UPDATE tickets SET status = 'resolved' WHERE id = ? AND lower(status) = 'open'",
                (rent_ticket["id"],),
            )
        else:
            connection.execute(
                "UPDATE purchase_orders SET status = 'paid_unsent' WHERE id = ?",
                (reference_id,),
            )

        invoice_after = (
            _one(connection, "SELECT * FROM invoices WHERE id = ?", (reference_id,))
            if kind == "invoice"
            else None
        )
        lease_after = (
            _one(connection, "SELECT * FROM leases WHERE id = ?", (reference_id,))
            if kind == "rent"
            else None
        )
        purchase_order_after = (
            _one(connection, "SELECT * FROM purchase_orders WHERE id = ?", (reference_id,))
            if kind == "purchase_order"
            else None
        )
        updated_account = _one(
            connection,
            "SELECT * FROM cash_accounts WHERE name = ?",
            (account_name,),
        )
        return {
            "payment": {
                "kind": payment_kind,
                "reference_id": payment_reference,
                "amount": amount,
                "account": account_name,
                "paid_at": shop_date,
                "approved_by": approver,
            },
            "account": updated_account,
            "invoice": invoice_after,
            "lease": lease_after,
            "purchase_order": purchase_order_after,
            "resolved_ticket_id": rent_ticket["id"] if kind == "rent" else None,
            "human_approval_recorded": True,
        }


@mcp.tool()
def reset_working_database() -> dict[str, Any]:
    """Replace only the working database with the original reset copy."""
    if not ORIGINAL_DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Original reset database not found: {ORIGINAL_DATABASE_PATH}")
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Campus Customs working database not found: {DATABASE_PATH}")
    source = sqlite3.connect(f"{ORIGINAL_DATABASE_PATH.as_uri()}?mode=ro", uri=True)
    destination = sqlite3.connect(DATABASE_PATH, timeout=10)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    with _open_database_for_write() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_purchase_orders_table(connection)
    return {
        "reset": True,
        "working_database": DATABASE_PATH.name,
        "source_database_unchanged": ORIGINAL_DATABASE_PATH.name,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
