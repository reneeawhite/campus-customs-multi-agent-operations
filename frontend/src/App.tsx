import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DogPortrait, { type DogBreed } from "./DogPortrait";
import { playDogBark } from "./barks";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type AgentRole =
  | "boss"
  | "inventory"
  | "accounting"
  | "facilities"
  | "customer_service";

type AgentMeta = {
  label: string;
  breed: DogBreed;
  breedLabel: string;
  tint: string;
  description: string;
};

const AGENTS: Record<AgentRole, AgentMeta> = {
  boss: {
    label: "Boss",
    breed: "bulldog",
    breedLabel: "Handsome Dan-inspired bulldog",
    tint: "bulldog",
    description: "Leads the counter crew",
  },
  inventory: {
    label: "Inventory",
    breed: "golden",
    breedLabel: "Golden Retriever",
    tint: "golden",
    description: "Finds the right stock",
  },
  accounting: {
    label: "Accounting",
    breed: "terrier",
    breedLabel: "Wire-haired Terrier",
    tint: "terrier",
    description: "Keeps the books",
  },
  facilities: {
    label: "Facilities",
    breed: "shepherd",
    breedLabel: "German Shepherd",
    tint: "shepherd",
    description: "Looks after the shop",
  },
  customer_service: {
    label: "Customer Service",
    breed: "cocker",
    breedLabel: "Cocker Spaniel",
    tint: "cocker",
    description: "Writes a kind reply",
  },
};

const AGENT_ORDER: AgentRole[] = [
  "boss",
  "inventory",
  "accounting",
  "facilities",
  "customer_service",
];

const DELEGATION_BARKS: Record<AgentRole, string> = {
  boss: "Rrruff!",
  inventory: "Arf, arf!",
  accounting: "Yip!",
  facilities: "Woof!",
  customer_service: "Ruff-ruff!",
};

type Ticket = {
  id: number;
  type: string;
  subject: string;
  status: string;
  is_open: boolean;
  is_resolved: boolean;
  sku?: string | null;
  size?: string | null;
  quantity?: number | null;
  lease_id?: number | null;
  invoice_id?: number | null;
};

type ApprovalRequest = {
  action_type: string;
  summary: string;
  reference_id?: number | null;
  amount?: number | null;
  reason: string;
  payment_kind?: string | null;
  sku?: string | null;
  size?: string | null;
  quantity?: number | null;
  unit_cost?: number | null;
};

type Approval = {
  approval_id: string;
  run_id: string;
  ticket_id: number;
  agent: AgentRole | string;
  request: ApprovalRequest;
  status: "pending" | "approved";
  result?: Record<string, unknown> | null;
};

type VendorCapability = {
  vendor: {
    id: number;
    name: string;
    specialty: string;
    lead_time_days: number;
  };
  open_unpaid_invoices: Array<{ id: number; amount: number; due_date: string }>;
  can_ship_new_product: boolean;
};

type PurchaseOrder = {
  id: number;
  ticket_id: number;
  sku: string;
  size: string;
  quantity: number;
  vendor_id: number;
  vendor_name: string;
  unit_cost: number;
  amount: number;
  status: string;
  approved_by: string;
  approved_at: string;
};

type AuditEvent = {
  event_id?: string;
  run_id: string;
  time: string;
  step?: number;
  event_type: string;
  agent?: AgentRole | string | null;
  parent_agent?: AgentRole | string | null;
  ticket_id?: number | null;
  details?: Record<string, any>;
};

type AgentReport = {
  summary: string;
  facts?: Array<{ statement: string; source_tools?: string[] }>;
  recommendations?: string[];
  status?: string;
};

type WorkflowResult = {
  run_id: string;
  ticket_id: number;
  status: string;
  boss_report: AgentReport;
  agent_reports: AgentReport[];
  agent_invocations: number;
  mcp_tool_calls: number;
  model_id: string;
};

type DeskRun = {
  ticketId: number;
  result: WorkflowResult;
};

type AgentSnapshot = {
  state: "waiting" | "working" | "finished" | "blocked";
  summary?: string;
  lastTool?: string;
};

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const message =
      (payload && (payload.detail || payload.message)) ||
      "The shop server returned an error (" + response.status + ").";
    throw new Error(String(message));
  }
  return payload as T;
}

function money(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function roleFor(name: unknown): AgentRole | null {
  if (typeof name !== "string") return null;
  return name in AGENTS ? (name as AgentRole) : null;
}

function agentName(role: string | null | undefined): string {
  const key = roleFor(role);
  return key ? AGENTS[key].label : "Shop team";
}

function ticketType(type: string): string {
  const labels: Record<string, string> = {
    customer_order: "Customer order",
    rent_notice: "Rent notice",
    price_override: "Discount request",
  };
  return labels[type] || type.replaceAll("_", " ");
}

function toolLabel(name: string | undefined): string {
  if (!name) return "shop records";
  const labels: Record<string, string> = {
    get_customer_order_context: "customer order records",
    get_rent_ticket_context: "lease and rent records",
    get_discount_request_context: "discount and stock records",
    list_open_tickets: "the open ticket board",
    get_inventory_for_sku: "SKU stock and prices",
    list_vendor_capabilities: "vendor and invoice records",
    assess_invoice_payment: "invoice and cash records",
    assess_lease_payment: "lease and cash records",
  };
  return labels[name] || name.replaceAll("_", " ");
}

function getEventReport(event: AuditEvent): AgentReport | null {
  const report = event.details?.report;
  return report && typeof report.summary === "string" ? (report as AgentReport) : null;
}

function eventCopy(event: AuditEvent): { title: string; detail: string; bark?: string } {
  const role = agentName(event.agent);
  const details = event.details || {};
  const tool = typeof details.tool_name === "string" ? details.tool_name : undefined;
  const report = getEventReport(event);
  switch (event.event_type) {
    case "workflow_started":
      return { title: "Boss the Bulldog opened the ticket", detail: "The team is reading the request and choosing who can help." };
    case "agent_started":
      if (event.parent_agent) {
        const roleKey = roleFor(event.agent) || "boss";
        return {
          title: role + " was called in",
          detail: "A specialist is taking on the delegated check.",
          bark: DELEGATION_BARKS[roleKey],
        };
      }
      return { title: role + " stepped up", detail: "Checking the ticket details and relevant shop records." };
    case "delegation_requested":
      return {
        title: role + " called in " + agentName(String(details.target_agent || "")),
        detail: "A specialist was asked to check one part of the ticket.",
      };
    case "delegation_returned":
      return { title: role + " got a specialist's notes", detail: String(details.summary || "The delegated review is back at the counter.") };
    case "mcp_tool_started":
      return { title: role + " opened " + toolLabel(tool), detail: "Looking up the recorded shop facts." };
    case "mcp_tool_completed":
      return { title: role + " checked " + toolLabel(tool), detail: "The result came from the shop database." };
    case "mcp_tool_failed":
      return { title: role + " could not finish a lookup", detail: "The team will flag the missing information for review." };
    case "agent_completed":
      return { title: role + " reported back", detail: report?.summary || "The review step is complete." };
    case "agent_failed":
      return { title: role + " needs a hand", detail: "This step needs human review before the shop acts." };
    case "workflow_finished":
      return { title: "Boss the Bulldog wrapped up the review", detail: "Team status: " + String(details.status || "complete").replaceAll("_", " ") + "." };
    case "human_approval_completed":
      return { title: "A human approval was recorded", detail: "The approved shop action is now reflected in the records." };
    default:
      return { title: role + " updated the desk", detail: event.event_type.replaceAll("_", " ") + "." };
  }
}

function agentSnapshots(events: AuditEvent[], running: boolean): Record<AgentRole, AgentSnapshot> {
  const snapshots = {} as Record<AgentRole, AgentSnapshot>;
  for (const role of AGENT_ORDER) {
    const mine = events.filter((event) => event.agent === role);
    let state: AgentSnapshot["state"] = "waiting";
    let summary: string | undefined;
    let lastTool: string | undefined;
    for (const event of mine) {
      if (event.event_type === "agent_started") state = "working";
      if (event.event_type === "agent_completed") {
        state = "finished";
        summary = getEventReport(event)?.summary;
      }
      if (event.event_type === "agent_failed") state = "blocked";
      if (event.event_type === "mcp_tool_started" && typeof event.details?.tool_name === "string") {
        lastTool = event.details.tool_name;
      }
    }
    if (!running && events.length === 0) state = "waiting";
    snapshots[role] = { state, summary, lastTool };
  }
  return snapshots;
}

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [shopDate, setShopDate] = useState<string | null>(null);
  const [checkingBalance, setCheckingBalance] = useState<number | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [vendors, setVendors] = useState<VendorCapability[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const [runningTicketId, setRunningTicketId] = useState<number | null>(null);
  const [lastRun, setLastRun] = useState<DeskRun | null>(null);
  const [baselineEventIds, setBaselineEventIds] = useState<string[]>([]);
  const [vendorChoices, setVendorChoices] = useState<Record<string, number>>({});
  const [vendorConfirmations, setVendorConfirmations] = useState<Record<string, boolean>>({});
  const [approverName, setApproverName] = useState("Shop manager");
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const runLock = useRef(false);
  const isMounted = useRef(true);
  const audioContext = useRef<AudioContext | null>(null);
  const eventFeedInitialized = useRef(false);
  const seenBarkEvents = useRef(new Set<string>());

  const refreshDesk = useCallback(async () => {
    const results = await Promise.allSettled([
      apiRequest<{ shop_date?: string; tickets: Ticket[] }>("/api/tickets"),
      apiRequest<{ account: { balance: number }; shop_date?: string }>("/api/cash/checking"),
      apiRequest<{ approvals: Approval[] }>("/api/approvals"),
      apiRequest<{ vendors: VendorCapability[] }>("/api/vendors"),
      apiRequest<{ purchase_orders: PurchaseOrder[] }>("/api/purchase-orders"),
    ]);
    if (!isMounted.current) return;
    const failures: string[] = [];
    const ticketsResult = results[0];
    if (ticketsResult.status === "fulfilled") {
      const ticketData = ticketsResult.value;
      setTickets(ticketData.tickets);
      setShopDate(ticketData.shop_date || null);
      setSelectedTicketId((current) => current ?? ticketData.tickets[0]?.id ?? null);
    } else failures.push("tickets: " + String(ticketsResult.reason));
    const checkingResult = results[1];
    if (checkingResult.status === "fulfilled") {
      const checkingData = checkingResult.value;
      setCheckingBalance(Number(checkingData.account.balance));
      setShopDate((current) => current || checkingData.shop_date || null);
    } else failures.push("checking: " + String(checkingResult.reason));
    if (results[2].status === "fulfilled") setApprovals(results[2].value.approvals);
    else failures.push("approvals: " + String(results[2].reason));
    if (results[3].status === "fulfilled") setVendors(results[3].value.vendors);
    else failures.push("vendors: " + String(results[3].reason));
    if (results[4].status === "fulfilled") setPurchaseOrders(results[4].value.purchase_orders);
    else failures.push("purchase orders: " + String(results[4].reason));
    setError(failures.length ? failures.join(" · ") : "");
    setLoading(false);
  }, []);

  const refreshEvents = useCallback(async () => {
    try {
      const data = await apiRequest<{ events: AuditEvent[] }>("/api/events?limit=500");
      if (isMounted.current) {
        if (!eventFeedInitialized.current) {
          data.events.forEach((event) => {
            if (event.event_id) seenBarkEvents.current.add(event.event_id);
          });
          eventFeedInitialized.current = true;
        }
        setEvents(data.events);
      }
    } catch {
      // Ticket actions remain usable if the optional activity feed is unavailable.
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    void refreshDesk();
    void refreshEvents();
    const refreshTimer = window.setInterval(() => {
      void refreshDesk();
      void refreshEvents();
    }, 15000);
    return () => {
      isMounted.current = false;
      window.clearInterval(refreshTimer);
    };
  }, [refreshDesk, refreshEvents]);

  useEffect(() => {
    if (runningTicketId === null) return;
    const timer = window.setInterval(() => void refreshEvents(), 900);
    return () => window.clearInterval(timer);
  }, [runningTicketId, refreshEvents]);

  useEffect(() => {
    for (const event of events) {
      const eventId = event.event_id;
      if (!eventId || seenBarkEvents.current.has(eventId)) continue;
      seenBarkEvents.current.add(eventId);
      if (!soundEnabled || event.event_type !== "agent_started" || !event.parent_agent) continue;
      const role = roleFor(event.agent);
      const context = audioContext.current;
      if (!role || !context || context.state === "closed") continue;
      try {
        playDogBark(context, AGENTS[role].breed);
      } catch {
        // Keep the activity board working if browser audio is unavailable.
      }
    }
  }, [events, soundEnabled]);

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedTicketId) || null,
    [tickets, selectedTicketId],
  );

  const visibleEvents = useMemo(() => {
    if (!selectedTicket) return [];
    if (lastRun?.ticketId === selectedTicket.id) {
      return events.filter((event) => event.run_id === lastRun.result.run_id);
    }
    if (runningTicketId === selectedTicket.id) {
      const baseline = new Set(baselineEventIds);
      return events.filter(
        (event) =>
          event.ticket_id === selectedTicket.id &&
          (!event.event_id || !baseline.has(event.event_id)),
      );
    }
    return events.filter((event) => event.ticket_id === selectedTicket.id).slice(-36);
  }, [events, selectedTicket, lastRun, runningTicketId, baselineEventIds]);

  const snapshots = useMemo(
    () => agentSnapshots(visibleEvents, runningTicketId === selectedTicket?.id),
    [visibleEvents, runningTicketId, selectedTicket],
  );

  const startRun = async (ticket: Ticket) => {
    if (runLock.current || !ticket.is_open) return;
    runLock.current = true;
    setSelectedTicketId(ticket.id);
    setRunningTicketId(ticket.id);
    setLastRun(null);
    setNotice("Boss the Bulldog is opening ticket " + ticket.id + " for the team.");
    setError("");
    try {
      let startingEvents: AuditEvent[] = [];
      try {
        const data = await apiRequest<{ events: AuditEvent[] }>("/api/events?limit=500");
        startingEvents = data.events;
        data.events.forEach((event) => {
          if (event.event_id) seenBarkEvents.current.add(event.event_id);
        });
        eventFeedInitialized.current = true;
        setEvents(data.events);
      } catch {
        // A missing activity feed should not keep Boss from reviewing the ticket.
      }
      setBaselineEventIds(startingEvents.map((event) => event.event_id || ""));
      const data = await apiRequest<{ workflow: WorkflowResult; pending_approvals: Approval[] }>(
        "/api/tickets/" + ticket.id + "/run",
        { method: "POST" },
      );
      setLastRun({ ticketId: ticket.id, result: data.workflow });
      setNotice("Ticket " + ticket.id + " review finished. Check the team's notes and any approval requests.");
      await Promise.all([refreshDesk(), refreshEvents()]);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "The agent run could not start.");
      setNotice("");
    } finally {
      runLock.current = false;
      setRunningTicketId(null);
      await refreshDesk();
      await refreshEvents();
    }
  };

  const approveRequest = async (approval: Approval) => {
    const id = approval.approval_id;
    if (!approverName.trim()) {
      setError("Enter the human approver's name before approving.");
      return;
    }
    const request = approval.request;
    const isPurchase = request.action_type === "purchase_order";
    const vendorId = vendorChoices[id] ?? vendors.find((item) => item.can_ship_new_product)?.vendor.id;
    if (isPurchase && !vendorId) {
      setError("There is no vendor without an open unpaid invoice available for this purchase.");
      return;
    }
    if (isPurchase && !vendorConfirmations[id]) {
      setError("Confirm the vendor choice. The shop database does not link a vendor to this SKU.");
      return;
    }
    const verb = isPurchase ? "Record this as an approved unsent purchase order?" : "Approve this payment from checking?";
    if (!window.confirm(verb + "\n\n" + request.summary + "\nAmount: " + money(request.amount))) return;
    setBusyAction(id);
    setError("");
    setNotice("");
    try {
      await apiRequest<{ approval: Approval }>(
        "/api/approvals/" + encodeURIComponent(id) + "/approve",
        {
          method: "POST",
          body: JSON.stringify({
            approved_by: approverName.trim(),
            account_name: "checking",
            vendor_id: isPurchase ? vendorId : null,
            vendor_match_confirmed: isPurchase ? true : false,
          }),
        },
      );
      setNotice(isPurchase ? "Purchase order approved as an unsent draft. No cash was spent." : "Payment approved and recorded from checking.");
      await Promise.all([refreshDesk(), refreshEvents()]);
    } catch (approvalError) {
      setError(approvalError instanceof Error ? approvalError.message : "The approval could not be recorded.");
    } finally {
      setBusyAction(null);
    }
  };

  const payPurchaseOrder = async (order: PurchaseOrder) => {
    if (!approverName.trim()) {
      setError("Enter the human approver's name before approving a payment.");
      return;
    }
    const confirmed = window.confirm(
      "Make a separate payment for purchase order " + order.id + "?\n\n" +
        order.quantity + " × " + order.sku + " / " + order.size + " from " + order.vendor_name +
        "\nAmount from checking: " + money(order.amount),
    );
    if (!confirmed) return;
    const action = "po-" + order.id;
    setBusyAction(action);
    setError("");
    try {
      await apiRequest(
        "/api/purchase-orders/" + order.id + "/pay",
        {
          method: "POST",
          body: JSON.stringify({ approved_by: approverName.trim(), account_name: "checking" }),
        },
      );
      setNotice("Purchase-order payment recorded. The checking balance has been refreshed.");
      await Promise.all([refreshDesk(), refreshEvents()]);
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "The purchase-order payment could not be recorded.");
    } finally {
      setBusyAction(null);
    }
  };

  const resetWorkingCopy = async () => {
    const confirmed = window.confirm(
      "Restore the working shop database from the original copy? This clears working-copy changes and pending approvals. The audit trail stays append-only.",
    );
    if (!confirmed) return;
    setBusyAction("reset");
    setError("");
    try {
      await apiRequest("/api/reset", { method: "POST" });
      setLastRun(null);
      setNotice("The working shop records are back at their original values. The audit trail was kept.");
      await Promise.all([refreshDesk(), refreshEvents()]);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "The working copy could not be reset.");
    } finally {
      setBusyAction(null);
    }
  };

  const toggleBarkAudio = async () => {
    if (soundEnabled) {
      setSoundEnabled(false);
      return;
    }
    try {
      if (!window.AudioContext) {
        setError("This browser does not support audio barks; the text bubbles will still appear.");
        return;
      }
      const context = audioContext.current || new window.AudioContext();
      audioContext.current = context;
      await context.resume();
      setSoundEnabled(true);
      setError("");
    } catch {
      setError("The browser could not start audio. Check its sound settings and try again.");
    }
  };

  const openCount = tickets.filter((ticket) => ticket.is_open).length;
  const resolvedCount = tickets.filter((ticket) => ticket.is_resolved).length;
  const pendingCount = approvals.filter((approval) => approval.status === "pending").length;
  const reviewedTicketIds = new Set(
    events
      .filter((event) => event.event_type === "workflow_finished" && event.ticket_id !== null && event.ticket_id !== undefined)
      .map((event) => Number(event.ticket_id)),
  );
  if (lastRun) reviewedTicketIds.add(lastRun.ticketId);
  const activeAgents = Object.values(snapshots).filter((agent) => agent.state === "working").length;

  return (
    <div className="page-wrap">
      <div className="gingham-edge" aria-hidden="true" />
      <header className="topbar">
        <div className="topbar-brand">
          <div className="tiny-emblem"><DogPortrait breed="bulldog" size={39} /></div>
          <div>
            <strong>Campus Customs</strong>
            <span>your neighborhood campus shop</span>
          </div>
        </div>
        <div className="topbar-right">
          <span className="shop-day"><span className="live-dot" /> Shop day <strong>{shopDate || "loading"}</strong></span>
          <button className={"sound-toggle" + (soundEnabled ? " sound-on" : "")} onClick={() => void toggleBarkAudio()} aria-pressed={soundEnabled} title="Turn delegated dog barks on or off">
            <span aria-hidden="true">{soundEnabled ? "♫" : "♪"}</span>{soundEnabled ? "Barks on" : "Barks off"}
          </button>
          <div className="cash-chip">
            <span className="cash-icon" aria-hidden="true">$</span>
            <span><small>Checking</small><strong>{money(checkingBalance)}</strong></span>
          </div>
          <button className="reset-button" onClick={() => void resetWorkingCopy()} disabled={busyAction === "reset"} title="Restore the working copy from the original database">
            {busyAction === "reset" ? "Resetting…" : "↺ Start fresh"}
          </button>
        </div>
      </header>

      <main className="desk-shell">
        <section className="shop-sign" aria-label="Campus Customs agent desk">
          <div className="awning" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /></div>
          <div className="sign-body">
            <div className="sign-copy">
              <p className="eyebrow">SINCE THE FIRST DAY OF CLASS</p>
              <h1>Campus <em>Customs</em></h1>
              <p className="sign-subtitle">The Corner Desk <span>·</span> orders, odds &amp; ends, all in good hands</p>
            </div>
              <div className="sign-mascot"><DogPortrait breed="bulldog" size={103} /><small>OPEN<br />FOR BUSINESS</small></div>
            <div className="sign-stitch" aria-hidden="true" />
          </div>
          <div className="sign-footer"><span>✦ A little care goes a long way ✦</span></div>
        </section>

        <section className="welcome-row">
          <div>
            <p className="eyebrow">THE MORNING BOARD</p>
            <h2>Pull up a chair.</h2>
            <p className="welcome-copy">Boss the Bulldog is keeping an eye on the counter. Pick a ticket and the right dog from the crew will pitch in.</p>
          </div>
          <div className="counter-stats" aria-label="Shop overview">
            <div className="stat-item"><strong>{tickets.length || "—"}</strong><span>tickets</span></div>
            <div className="stat-rule" />
            <div className="stat-item"><strong>{openCount}</strong><span>open</span></div>
            <div className="stat-rule" />
            <div className="stat-item"><strong>{resolvedCount}</strong><span>resolved</span></div>
          </div>
        </section>

        {error && <div className="notice notice-error" role="alert"><span>⚠</span><p>{error}</p><button onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="notice notice-success" role="status"><span>✦</span><p>{notice}</p><button onClick={() => setNotice("")} aria-label="Dismiss notice">×</button></div>}

        <div className="desk-grid">
          <aside className="ticket-column">
            <div className="section-heading">
              <div><span className="section-kicker">ON THE COUNTER</span><h2>Ticket basket</h2></div>
              <span className="count-pill">{tickets.length}</span>
            </div>
            <div className="ticket-list">
              {loading && tickets.length === 0 ? (
                <div className="empty-card"><span className="basket-emoji">🧺</span><p>Bringing the ticket basket out…</p></div>
              ) : tickets.length === 0 ? (
                <div className="empty-card"><span className="basket-emoji">🧺</span><p>No ticket details came back from the shop server.</p></div>
              ) : tickets.map((ticket) => {
                const isSelected = ticket.id === selectedTicketId;
                const hasRun = reviewedTicketIds.has(ticket.id);
                return (
                  <button
                    className={"ticket-card" + (isSelected ? " is-selected" : "") + (ticket.is_resolved ? " is-resolved" : "")}
                    key={ticket.id}
                    onClick={() => setSelectedTicketId(ticket.id)}
                    aria-pressed={isSelected}
                  >
                    <div className="ticket-card-top"><span className="ticket-number">#{ticket.id}</span><span className={"status-tag " + (ticket.is_resolved ? "status-resolved" : hasRun ? "status-reviewed" : "status-open")}>{ticket.is_resolved ? "Resolved" : hasRun ? "Reviewed" : "Open"}</span></div>
                    <strong className="ticket-subject">{ticket.subject || ticketType(ticket.type)}</strong>
                    <span className="ticket-kind">{ticketType(ticket.type)}</span>
                    {ticket.sku && <span className="ticket-extra">{ticket.quantity ? ticket.quantity + " × " : ""}{ticket.sku}{ticket.size ? " · " + ticket.size : ""}</span>}
                    {ticket.lease_id && <span className="ticket-extra">Lease #{ticket.lease_id}</span>}
                    {ticket.invoice_id && <span className="ticket-extra">Invoice #{ticket.invoice_id}</span>}
                    <span className="ticket-card-foot">{ticket.is_resolved ? "All settled" : hasRun ? "Team has left a note" : "Ready for a look"}<span aria-hidden="true">↗</span></span>
                  </button>
                );
              })}
            </div>
            <div className="little-note"><span aria-hidden="true">✎</span><p>Each ticket gets its own careful review. Specialists join only when their know-how is useful.</p></div>
          </aside>

          <section className="ticket-workspace">
            {selectedTicket ? (
              <>
                <div className="workspace-heading">
                  <div>
                    <div className="workspace-eyebrow"><span className="ticket-number">TICKET #{selectedTicket.id}</span><span className="type-badge">{ticketType(selectedTicket.type)}</span></div>
                    <h2>{selectedTicket.subject || "Shop ticket"}</h2>
                    <p className="workspace-subtitle">A good look first, then the right hands on the job.</p>
                  </div>
                  <div className="workspace-status">
                    <span className={"status-tag large " + (selectedTicket.is_resolved ? "status-resolved" : reviewedTicketIds.has(selectedTicket.id) ? "status-reviewed" : "status-open")}>
                      {selectedTicket.is_resolved ? "✓ Resolved" : reviewedTicketIds.has(selectedTicket.id) ? "✓ Review complete" : "● Open ticket"}
                    </span>
                    {lastRun?.ticketId === selectedTicket.id && <small>Team run finished · {lastRun.result.status.replaceAll("_", " ")}</small>}
                  </div>
                </div>

                <div className="ticket-detail-strip">
                  <div><span className="detail-icon">⌂</span><span><small>Shop date</small><strong>{shopDate || "From shop records"}</strong></span></div>
                  {selectedTicket.sku && <div><span className="detail-icon">▤</span><span><small>Item on ticket</small><strong>{selectedTicket.sku}{selectedTicket.size ? " · " + selectedTicket.size : ""}</strong></span></div>}
                  {selectedTicket.quantity !== null && selectedTicket.quantity !== undefined && <div><span className="detail-icon">×</span><span><small>Requested</small><strong>{selectedTicket.quantity} pieces</strong></span></div>}
                  {selectedTicket.lease_id && <div><span className="detail-icon">⌂</span><span><small>Lease reference</small><strong>#{selectedTicket.lease_id}</strong></span></div>}
                  {selectedTicket.invoice_id && <div><span className="detail-icon">▧</span><span><small>Invoice reference</small><strong>#{selectedTicket.invoice_id}</strong></span></div>}
                </div>

                <div className="team-headline">
                  <div><span className="section-kicker">THE DOG CREW AT WORK</span><h3>Who’s helping?</h3></div>
                  {runningTicketId === selectedTicket.id && <span className="working-indicator"><i /> {activeAgents ? activeAgents + " agent" + (activeAgents === 1 ? "" : "s") + " working" : "Boss is reading"}</span>}
                </div>
                <div className="agent-roster">
                  {AGENT_ORDER.map((role) => {
                    const agent = AGENTS[role];
                    const snapshot = snapshots[role];
                    const stateLabel = snapshot.state === "working" ? "Working now" : snapshot.state === "finished" ? "Reported back" : snapshot.state === "blocked" ? "Needs a hand" : runningTicketId === selectedTicket.id ? "On call" : "Ready when needed";
                    return (
                      <article className={"agent-card agent-" + agent.tint + (snapshot.state === "working" ? " agent-card-working" : "")} key={role} aria-label={agent.label + ": " + stateLabel}>
                        <div className="agent-card-top"><DogPortrait breed={agent.breed} size={54} /><span className={"agent-state state-" + snapshot.state} role="status">{stateLabel}</span></div>
                        <h4>{agent.label}</h4>
                        <p className="agent-breed">{agent.breedLabel}</p>
                        <p className="agent-specialty">{agent.description}</p>
                        {snapshot.lastTool && <p className="agent-tool">↳ {toolLabel(snapshot.lastTool)} · {snapshot.lastTool}</p>}
                        {snapshot.summary && <p className="agent-summary">{snapshot.summary}</p>}
                      </article>
                    );
                  })}
                </div>

                <div className="run-row">
                  <div className="run-explainer"><DogPortrait breed="bulldog" size={30} /><p><strong>Boss decides who to call.</strong><br />The team shares findings; nothing is sent or paid without you.</p></div>
                  <button
                    className="run-button"
                    onClick={() => void startRun(selectedTicket)}
                    disabled={!selectedTicket.is_open || runningTicketId !== null}
                  >
                    {runningTicketId === selectedTicket.id ? <><span className="button-spinner" /> Team is on it</> : selectedTicket.is_resolved ? "Ticket settled" : "Ask the team to review"}
                    {runningTicketId !== selectedTicket.id && selectedTicket.is_open && <span aria-hidden="true">→</span>}
                  </button>
                </div>

                <section className="activity-section">
                  <div className="activity-heading"><div><span className="section-kicker">THE COUNTER CHATTER</span><h3>Agent activity</h3></div><span className="activity-live"><i /> {runningTicketId === selectedTicket.id ? "Live" : "Latest notes"}</span></div>
                  {lastRun?.ticketId === selectedTicket.id && (
                    <div className="run-recap"><div className="recap-seal">✓</div><div><strong>Review finished</strong><p>{lastRun.result.agent_invocations} agent steps · {lastRun.result.mcp_tool_calls} shop lookups · {lastRun.result.model_id}</p></div></div>
                  )}
                  <div className="activity-feed" aria-live="polite" aria-relevant="additions text">
                    {visibleEvents.length === 0 ? (
                      <div className="activity-empty"><span>☕</span><p>{runningTicketId === selectedTicket.id ? "Boss is getting the ledger open…" : "The counter is quiet. Start a team review to see the notes appear here."}</p></div>
                    ) : visibleEvents.slice(-28).map((event, index) => {
                      const role = roleFor(event.agent) || "boss";
                      const copy = eventCopy(event);
                      const report = getEventReport(event);
                      return (
                        <article className={"activity-item agent-" + AGENTS[role].tint} key={event.event_id || event.run_id + "-" + event.step + "-" + index}>
                          <div className="activity-avatar"><DogPortrait breed={AGENTS[role].breed} size={34} /></div>
                          <div className="activity-content">
                            <div className="activity-item-top"><strong>{copy.title}</strong><time>{event.time ? new Date(event.time).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "just now"}</time></div>
                            <p>{copy.detail}</p>
                            {copy.bark && <div className="bark-bubble"><span aria-hidden="true">✦</span><strong>{copy.bark}</strong></div>}
                            {report?.recommendations && report.recommendations.length > 0 && <ul>{report.recommendations.slice(0, 2).map((item, i) => <li key={i}>{item}</li>)}</ul>}
                            {event.event_type === "mcp_tool_completed" && typeof event.details?.tool_name === "string" && <span className="source-chip">MCP tool · {event.details.tool_name} ({toolLabel(event.details.tool_name)})</span>}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                  {lastRun?.ticketId === selectedTicket.id && !selectedTicket.is_resolved && (
                    <p className="resolution-hint">The agent review is complete. This ticket stays open in the shop records until its required human decision or follow-up is finished.</p>
                  )}
                </section>
              </>
            ) : (
              <div className="select-ticket-empty"><span>🧺</span><h2>The basket is waiting</h2><p>Choose a ticket from the left to see its details and call in the team.</p></div>
            )}
          </section>

          <aside className="approval-column">
            <section className="approval-panel">
              <div className="section-heading approval-heading"><div><span className="section-kicker">YOUR CALL, PLEASE</span><h2>Approval basket</h2></div><span className="count-pill count-warm">{pendingCount}</span></div>
              <p className="approval-intro">The agents can prepare a request. Only a person at the counter can approve it.</p>
              <label className="approver-label" htmlFor="approver-name">Human approver</label>
              <input id="approver-name" className="approver-input" value={approverName} maxLength={120} onChange={(event) => setApproverName(event.target.value)} placeholder="Your name" />
              <div className="approval-list">
                {approvals.length === 0 ? (
                  <div className="approval-empty"><span aria-hidden="true">🧾</span><strong>Nothing waiting for a signature</strong><p>Payment and purchase requests will be set out here for your review.</p></div>
                ) : approvals.slice().reverse().map((approval) => {
                  const request = approval.request;
                  const purchase = request.action_type === "purchase_order";
                  const paymentShortfall =
                    !purchase &&
                    request.amount !== null &&
                    request.amount !== undefined &&
                    checkingBalance !== null &&
                    request.amount > checkingBalance;
                  const chosenVendor = vendorChoices[approval.approval_id] ?? vendors.find((item) => item.can_ship_new_product)?.vendor.id ?? 0;
                  const activeVendor = vendors.find((item) => item.vendor.id === chosenVendor);
                  return (
                    <article className={"approval-card " + (approval.status === "approved" ? "approval-done" : "")} key={approval.approval_id}>
                      <div className="approval-card-top"><span className="approval-type">{purchase ? "PURCHASE PLAN" : "PAYMENT REQUEST"}</span><span className={"approval-status " + (approval.status === "approved" ? "approved" : "awaiting")}>{approval.status === "approved" ? "Approved" : "Needs you"}</span></div>
                      <h3>{request.summary}</h3>
                      <p className="approval-meta">Ticket #{approval.ticket_id} · {agentName(approval.agent)}</p>
                      <div className="approval-amount"><small>{purchase ? "Proposed order total" : "Proposed payment"}</small><strong>{money(request.amount)}</strong></div>
                      <p className="approval-reason">{request.reason}</p>
                      {purchase && request.sku && <div className="approval-item-details">
                        <strong>{request.quantity || "?"} × {request.sku}{request.size ? " / " + request.size : ""}</strong>
                        {request.unit_cost !== null && request.unit_cost !== undefined && <small>{money(request.unit_cost)} each at recorded unit cost</small>}
                      </div>}
                      {paymentShortfall && <p className="funds-warning">The current checking balance is below this amount. The backend will refuse the payment unless recorded funds cover it.</p>}
                      {purchase && approval.status === "pending" && (
                        <div className="vendor-picker">
                          <label htmlFor={"vendor-" + approval.approval_id}>Choose a vendor from the records</label>
                          <select
                            id={"vendor-" + approval.approval_id}
                            value={chosenVendor || ""}
                            onChange={(event) => setVendorChoices((current) => ({ ...current, [approval.approval_id]: Number(event.target.value) }))}
                          >
                            <option value="" disabled>Select a vendor</option>
                            {vendors.map((vendor) => (
                              <option key={vendor.vendor.id} value={vendor.vendor.id} disabled={!vendor.can_ship_new_product}>
                                {vendor.vendor.name} · {vendor.can_ship_new_product ? vendor.vendor.lead_time_days + " day lead" : "blocked by unpaid invoice"}
                              </option>
                            ))}
                          </select>
                          {activeVendor && <p className={activeVendor.can_ship_new_product ? "vendor-note" : "vendor-note vendor-blocked"}>
                            {activeVendor.can_ship_new_product ? activeVendor.vendor.specialty + ". The database does not map vendors to this SKU, so review the choice." : "This vendor cannot ship while an invoice is unpaid."}
                          </p>}
                          <label className="confirm-vendor"><input type="checkbox" checked={!!vendorConfirmations[approval.approval_id]} onChange={(event) => setVendorConfirmations((current) => ({ ...current, [approval.approval_id]: event.target.checked }))} /> I confirm this vendor selection for the draft.</label>
                        </div>
                      )}
                      {approval.status === "approved" ? (
                        <div className="approval-recorded">✓ Recorded by a human. {purchase ? "The PO is unsent and cash is unchanged." : "The payment was recorded."}</div>
                      ) : (
                        <button className="approve-button" onClick={() => void approveRequest(approval)} disabled={busyAction === approval.approval_id || paymentShortfall || (purchase && (!activeVendor?.can_ship_new_product || !vendorConfirmations[approval.approval_id])) || !approverName.trim()}>
                          {busyAction === approval.approval_id ? "Recording…" : purchase ? "Approve unsent purchase" : "Approve payment"}
                          {busyAction !== approval.approval_id && <span aria-hidden="true">✓</span>}
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>

            <section className="cash-panel">
              <div className="cash-panel-heading"><span className="cash-jar" aria-hidden="true">$</span><div><span className="section-kicker">THE TILL</span><h2>Checking jar</h2></div></div>
              <div className="balance-number">{money(checkingBalance)}</div>
              <div className="balance-bottom"><span>Current recorded balance</span><button onClick={() => void refreshDesk()} title="Refresh cash and approval records">Refresh ↻</button></div>
              <p className="cash-safety"><span>✦</span> Payments are only made after your approval. The jar can’t go below zero.</p>
            </section>

            <section className="po-panel">
              <div className="section-heading po-heading"><div><span className="section-kicker">BACK ROOM BOOK</span><h2>Purchase orders</h2></div><span className="count-pill">{purchaseOrders.length}</span></div>
              {purchaseOrders.length === 0 ? <p className="po-empty">Approved orders stay here as unsent drafts until a separate payment is approved.</p> : (
                <div className="po-list">{purchaseOrders.slice().reverse().map((order) => (
                  <article className="po-card" key={order.id}>
                    <div className="po-top"><strong>PO #{order.id}</strong><span>{order.status.replaceAll("_", " ")}</span></div>
                    <p>{order.quantity} × {order.sku} / {order.size}</p>
                    <small>{order.vendor_name} · {money(order.amount)}</small>
                    {order.status === "approved_draft_unsent" && <button className="po-pay-button" onClick={() => void payPurchaseOrder(order)} disabled={busyAction === "po-" + order.id}>{busyAction === "po-" + order.id ? "Paying…" : "Approve payment · " + money(order.amount)}</button>}
                    {order.status === "paid_unsent" && <div className="po-paid">Paid from checking · still unsent</div>}
                  </article>
                ))}</div>
              )}
            </section>
          </aside>
        </div>

        <section className="dog-legend" aria-label="Agent roles">
              <div className="legend-title"><span>THE LITTLE CREW</span><strong>Good neighbors, good notes.</strong></div>
          {AGENT_ORDER.map((role) => <div className={"legend-agent agent-" + AGENTS[role].tint} key={role}><DogPortrait breed={AGENTS[role].breed} size={35} /><strong>{AGENTS[role].label}</strong></div>)}
        </section>

        <footer className="page-footer"><span>Campus Customs · The Corner Desk</span><span>Thoughtful work, one ticket at a time <b>♥</b></span></footer>
      </main>
    </div>
  );
}

export default App;
