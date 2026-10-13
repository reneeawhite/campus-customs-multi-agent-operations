# Problem 8: Agent dashboard design

## The feeling

I chose the familiar front porch of a small country shop as the visual starting point: a striped awning, a hand-lettered-looking shop sign, warm paper colors, wood-and-cream details, and a little counter-side note. The attached Mom and Pop's Country Store image inspired the storefront details. A restrained red, cream, sage, and honey palette keeps the page cozy and readable while still making status and money controls easy to spot.

The page uses a small set of recurring shop details rather than turning every panel into decoration. The scalloped awning and stitched sign frame give the dashboard its local-market character; the ledger paper, dashed rules, ticket slips, approval basket, and checking jar make familiar shop work feel tangible. Small details like “Pull up a chair,” “The counter chatter,” and the dog crew roster give the team some warmth without getting in the way of the work.

## Layout

The top bar holds the shop name, the current shop date from the backend, and the checking balance. Below the storefront sign, a short greeting and three compact counts give a quick sense of the board.

The main desk has three working areas:

- The left ticket basket lists every ticket returned by the backend. Selecting a card opens it in the center. Each card shows the ticket number, kind, status, and any SKU, size, quantity, lease, or invoice references returned by the API.
- The center counter is the work area for the selected ticket. It shows the ticket details, the five agent badges, a clear button to start a review, a live activity feed, and a compact run recap.
- The right approval basket is where a human reviews payment and purchase requests. It includes the approver name, recorded vendor choices, the vendor's lead time and shipping block, and an explicit confirmation when the database does not map a vendor to a SKU. A purchase order is labeled as an unsent draft. A later PO payment is a separate approval with its own button and confirmation.

On narrower screens, the ticket basket moves above the work area and the approval panel stacks below it. The agent names and button labels stay visible at small widths.

## Dog identities and agent activity

I replaced the fruit characters with original, illustrated dog portraits built as inline SVG. Each portrait has its own silhouette, ears, coat colors, muzzle, collar, and stitched shop-badge backdrop, so the breeds stay recognizable even when the activity feed uses smaller portraits. The bulldog mascot takes inspiration from Handsome Dan while using custom artwork drawn for this dashboard.

- Boss is a confident bulldog with a deep red bandanna who leads the review and chooses the next specialist.
- Inventory is a golden retriever with a leafy green collar, a friendly shelf-finder.
- Accounting is a sharp wire-haired terrier with a blue ledger collar.
- Facilities is a steady German shepherd with a forest-green collar.
- Customer Service is a warm cocker spaniel with a berry-red collar and soft floppy ears.

Breed labels, role names, coat patterns, and collar colors make it easy to scan who is speaking. When Boss delegates a task, the called-in specialist answers with a short breed-specific bark cue: the bulldog gives a low “Rrruff!”, the retriever a lively “Arf, arf!”, the terrier a quick “Yip!”, the shepherd a firm “Woof!”, and the cocker spaniel a warm “Ruff-ruff!” Each appears in a small speech bubble on the delegated-start event, so the character detail stays separate from the actual task and report.

The dashboard polls the audit-events route while a ticket runs. Each event appears with its agent portrait, a plain-language action, its report summary, and the exact MCP tool name for lookups. The agent cards show whether someone is working, has reported back, is waiting, or needs human help, along with the latest summary and lookup where available. A working dog’s card lights up in that agent’s own color with a glowing border, a small top stripe, and a pulsing “Working now” marker; inactive agents keep the quieter paper treatment.

The bark speech bubbles can also be heard as brief, locally synthesized bark-like sounds. Filtered breath bursts and a soft falling tone replace the earlier buzzy oscillator, while pitch, resonance, and rhythm vary by breed. Audio is opt-in through the header's sound toggle, so the dashboard stays quiet until the human turns it on. The sounds remain stylized effects rather than recordings of real dogs.

A classic white dog-bone cursor uses a simple horizontal silhouette with a thin dark outline and a narrow shaft. Text-entry fields retain a standard insertion cursor.

## Ticket status and cash

Ticket status always follows the backend's ticket record. When a run finishes, the board adds a green review-complete marker and the team's run recap. A ticket is labeled resolved only when the backend reports it resolved; for example, the approved rent payment updates the linked ticket. If a review still needs a payment, purchase, or other follow-up, it remains open so the board does not mistake analysis for completed shop work.

The checking balance is visible in the header and in a dedicated checking-jar panel. Both read from the checking-balance route and refresh after approval actions. Payment buttons ask for a human confirmation before calling the backend, and the board flags a proposal that is larger than the displayed balance while still relying on the backend's live funds check. Purchase-order approval is clearly separate from payment: approving the draft does not spend cash, and a second human action is required to pay it. This makes the money movement and the human decision visible at the moment they matter.

A small “Start fresh” control restores the working database from the original after an explicit confirmation. The confirmation explains that working-copy changes and pending approvals will be reset while the append-only audit trail stays intact.

## Technical choices

The dashboard uses React, Vite, and TypeScript. It calls the existing FastAPI routes at `http://localhost:8000`, including tickets, runs, events, approvals, vendors, purchase orders, and checking balance. Vite uses port 5173. FastAPI allows both the standard local HTTP Vite origin and its HTTPS equivalent for localhost and 127.0.0.1.
