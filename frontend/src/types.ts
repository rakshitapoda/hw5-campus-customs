// Shapes returned by the FastAPI backend (backend/main.py, backend/models.py).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type RecommendedStatus = 'awaiting_approval' | 'blocked' | 'resolved' | 'needs_human'

export interface PaymentRequest {
  kind: 'invoice' | 'rent'
  ref_id: number
  payee: string
  amount: number
  account: string
  status: string
  reason: string
}

export interface PurchaseOrderRequest {
  vendor_id: number
  vendor_name: string
  sku: string
  size: string
  qty: number
  total_cost: number
  lead_days: number
  expected_arrival: string | null
  status: string
  reason: string
}

export interface MessageDraft {
  to: string
  subject: string
  body: string
}

export interface TicketResolution {
  ticket_id: number
  ticket_type: string
  assigned_agents: AgentName[]
  decision: string
  recommended_status: RecommendedStatus
  payment_requests: PaymentRequest[]
  purchase_orders: PurchaseOrderRequest[]
  message_drafts: MessageDraft[]
  open_issues: string[]
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: 'open' | 'resolved'
  notes: string | null
  created_at: string
  running_run_id: string | null
  agent_result: (TicketResolution & { run_id: string; finished_at: string }) | null
  approvals: Record<'pending' | 'blocked' | 'refused' | 'approved', number>
  decisions: HumanDecision[]
}

export interface HumanDecision {
  decided_by: string
  decision: string
  decided_at: string
}

export interface RunStatus {
  run_id: string
  ticket_id: number
  status: 'running' | 'completed' | 'failed'
  started_at: string
  finished_at: string | null
  error: string | null
  resolution: TicketResolution | null
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
}

export interface AgentOutput {
  agent?: AgentName
  summary?: string
  decision?: string
  recommended_status?: RecommendedStatus
  facts?: string[]
  open_issues?: string[]
}

export interface ActivityEvent {
  timestamp: string
  event: string
  run_id: string | null
  ticket_id: number | null
  agent: AgentName | null
  depth: number | null
  said: string | null
  tools: ToolCall[]
  to_agent: AgentName | null
  details: { output?: AgentOutput; prompt?: string; [key: string]: unknown } | null
}

export interface Approval {
  id: string
  item_type: 'payment' | 'purchase_order'
  ticket_id: number | null
  run_id: string
  prepared_by: AgentName | null
  status: 'pending' | 'blocked' | 'refused' | 'approved'
  proposal: Record<string, any>
  created_at: string
  approved_by: string | null
  approved_at: string | null
  execution: Record<string, any> | null
}

export interface Cash {
  name: string
  balance: number
  date: string
}
