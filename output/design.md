# Operations Desk: Dashboard Design

The Campus Customs dashboard (`frontend/`, React + Vite + TypeScript) is the desk where a person watches the agent team work tickets and signs off on money. The design aims for one thing: **at a glance, you can tell what needs you, which agent is doing what, and how much cash is left.**

## Layout

Three columns, arranged to match how the work moves left to right:

| Column | Contents | Why |
|---|---|---|
| **Left: ticket queue** | The three tickets as stubs: number, type, requester, SKU/size/qty or lease, status chip, the agents who worked it, and a yellow "N to sign" badge. | The queue is the to-do list, so it stays pinned on the left like an inbox. Each card is shaped like a paper ticket stub (notch on the right edge, colored status rail on the left) so it reads as "a ticket" rather than a generic card. |
| **Center: the work** | The ticket header (subject, the requester's note, status, **Start agent team** button) → the **agent floor** (five agent stations) → the **Boss's decision** (decision, open issues, drafted messages) → the **live feed** and **What each agent did** side by side. | The center follows the order you'd read a case: what was asked, who's on it right now, what they decided, then the step-by-step trail and per-agent summary for anyone who wants detail. |
| **Right: money rail** | The **Checking** card on top and the **Sign-off tray** below it. Both stay visible while scrolling. | Money and approvals are the only things that need a human decision, so they never scroll out of view. Putting the tray right under the balance means you see the cash effect of every approval before you sign. |

The navy top bar holds the brand, the books date (`cash_accounts.date`, the shop's date rather than today's real date), a yellow "N awaiting sign-off" pill when approvals are waiting, backend connection status, and **Reset desk** (calls `POST /api/reset` after a confirm).

**Responsive:** at ≤1180px the money rail moves under the center as two side-by-side cards. At ≤820px everything stacks: the ticket stubs become a horizontally scrolling strip and the agent floor goes to two columns. Animations respect `prefers-reduced-motion`.

## How the agents look different

Every agent has a fixed **identity**: a color, an icon, and a role line. It's used identically everywhere the agent appears (agent floor, feed, summaries, ticket stubs, and the "Prepared by" chip on approvals), so after a minute you recognize agents by color without reading.

| Agent | Color | Icon | Role line |
|---|---|---|---|
| Boss | Indigo `#4338ca` | Crown | Routes tickets · final call |
| Inventory | Teal `#0f766e` | Box | Stock by SKU & size · vendors |
| Accounting | Amber `#b45309` | Calculator | Cash · invoices · margins |
| Facilities | Violet `#7e22ce` | Storefront | Leases · rent |
| Customer Service | Rose `#be185d` | Speech bubble | Drafts customer messages |

The hues are spread around the color wheel so no two agents are confused, and each is dark enough to pass contrast as text on white. Green is deliberately **not** an agent color: it's reserved for cash and "resolved", so green always means money is OK or work is done.

**Agent floor:** five stations, one per agent, each with a colored top border, the agent's badge, a phase tag, a speech bubble, and chips for the MCP tools it called.
- **Working:** the badge pulses in the agent's color, the bubble shows typing dots plus what it's doing in plain words ("Checking stock", "Preparing a payment", "Handing off to Accounting"), and the station lifts with a colored glow.
- **Waiting:** "Waiting on Facilities" while a teammate it delegated to is working.
- **Done:** the bubble shows the agent's final summary.
- **Not on this ticket:** the station is dimmed and desaturated. This makes the routing visible: on ticket 102 only Boss, Facilities, and Accounting light up.

The state comes from replaying `GET /api/activity?run_id=…` (the audit trail), which the dashboard polls every 1.5 s while a run is live.

## Ticket status and resolved tickets

Status uses one color language across stub rails, chips, the ticket header's top border, and the decision card's left border:

| Status | Color | Meaning |
|---|---|---|
| Not started | Grey | The agents haven't run yet |
| Agents working | Blue + spinner | A run is in progress |
| Needs your approval | Amber | A prepared payment/PO is waiting in the tray |
| Blocked | Red | Waiting on something no approval can fix right now (e.g. vendor blocked by an unpaid invoice) |
| Needs a decision | Violet | A human judgment call, e.g. how much bulk discount to give |
| Resolved | Green | Done |

**Resolved tickets** get three cues at once: a green status chip, a green rail on the stub, and a rubber-stamp **RESOLVED** that "thunks" onto the stub (a short scale-in animation). The decision card shows a green bar such as "Resolved · $2,400.00 approved by Rakshita Podagatlapalli", and labels the agents' text as their decision *at the end of the run*. That way an older "awaiting approval" sentence isn't mistaken for the current state. The run button changes to a disabled "Resolved", because the backend refuses to rerun resolved tickets.

## Cash

The **Checking** card shows the balance from `GET /api/cash` as the largest number on the screen, in green, with tabular numerals.

- **Delta flash:** when the balance changes after an approval, a red "−$2,400.00" pops up next to it for a few seconds, so you can see the money leave.
- **Cash bar:** one horizontal bar split into *left if all approved* (solid green), *awaiting your approval* (amber diagonal stripes, which read as "not final yet"), and *paid out* (grey).
- **Three rows** spell out the same numbers: paid out (approved), awaiting your approval, and left if all approved. If approving everything would go below $0, that row turns red and a warning explains that overdrawing payments will be refused. This matches the backend rule that cash can never go negative.
- A footnote reminds that cash only flows out and nothing moves without a person.

## Approvals (the sign-off tray)

Approvals are styled as **payment slips** on a pale amber background, matching the amber "Needs your approval" status. Each slip shows: payment or purchase order, ticket #, what it's for (e.g. "Invoice #501", "Rent · lease #1"), payee, the amount in large type, **"Checking after: $…"** (red with "will be refused" if negative), and which agent prepared it.

- Slips for the selected ticket float to the top and get an amber outline.
- **Approving as** is a name field (remembered in the browser). The Approve button stays disabled until it's filled, because the backend requires `approved_by`.
- **Approve** opens a confirm dialog with the amount, checking now → checking after, and who is signing. Only **Approve & pay** calls `POST /api/approvals/{id}/approve`. Two deliberate steps for money, never one click.
- Items the backend marks `blocked` or `refused` are listed under **"Can't be approved yet"** with the tool's reason (e.g. "Vendor has open unpaid invoice(s) [501]"), and have no button.
- Approved items move to a green **Approved** list with the approver's name and payment number.
- A toast confirms the result ("Paid $2,400.00 · checking now $1,000.00 · ticket #102 resolved"), or shows the backend's refusal message if it says no.

## Other choices

- **Light theme with a navy frame.** Long sessions of reading decisions and numbers are easier on a light surface. The Yale-navy top bar and the faint dot-grid background make it feel like a desk, not a form. It also matches `output/desk_tickets.html`.
- **Plain-language activity.** Tool names are translated into phrases on the floor ("check_inventory" → "Checking stock"). The raw tool names and arguments are kept as small monospace chips in the feed for anyone auditing.
- **Drafts look like drafts.** Customer messages sit in dashed pink boxes labelled "Draft · not sent", because agents never contact anyone (shop rule 9).
- **One run at a time.** While any ticket is running, other run buttons are disabled with a hint, mirroring the backend's single-run lock on the shared database.
- **No extra libraries.** Plain React + CSS with inline SVG icons keeps the frontend small and fast to load.
