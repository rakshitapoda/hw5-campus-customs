import type { ActivityEvent, AgentName, AgentOutput, ToolCall } from './types'

export interface AgentMeta {
  name: AgentName
  label: string
  role: string
  color: string
  soft: string
  initials: string
}

// Each agent gets a distinct hue, icon, and monogram so it reads the same everywhere on the desk.
export const AGENTS: AgentMeta[] = [
  { name: 'boss', label: 'Boss', role: 'Routes tickets · final call', color: '#4338ca', soft: '#eef0ff', initials: 'BO' },
  { name: 'inventory', label: 'Inventory', role: 'Stock by SKU & size · vendors', color: '#0f766e', soft: '#e6f6f3', initials: 'IN' },
  { name: 'accounting', label: 'Accounting', role: 'Cash · invoices · margins', color: '#b45309', soft: '#fdf3e4', initials: 'AC' },
  { name: 'facilities', label: 'Facilities', role: 'Leases · rent', color: '#7e22ce', soft: '#f5ecfd', initials: 'FA' },
  { name: 'customer_service', label: 'Customer Service', role: 'Drafts customer messages', color: '#be185d', soft: '#fdedf4', initials: 'CS' },
]

export const AGENT_BY_NAME = Object.fromEntries(AGENTS.map((a) => [a.name, a])) as Record<AgentName, AgentMeta>

// ------------------------------------------------------- live agent state

export type AgentPhase = 'idle' | 'working' | 'waiting' | 'done' | 'error'

export interface AgentState {
  phase: AgentPhase
  line: string
  tools: ToolCall[]
  lastAt: string | null
  involved: boolean
}

export const TOOL_LABELS: Record<string, string> = {
  get_ticket: 'reading the ticket',
  get_shop_date: 'checking the shop date',
  list_open_tickets: 'scanning the queue',
  check_inventory: 'checking stock',
  check_vendor_status: 'checking vendors',
  get_lease: 'pulling the lease',
  get_invoice: 'pulling the invoice',
  get_cash_balance: 'checking cash',
  check_margin: 'running margins',
  prepare_payment: 'preparing a payment',
  prepare_purchase_order: 'preparing a purchase order',
  delegate_task: 'delegating',
}

export function describeTools(tools: ToolCall[]): string {
  const delegate = tools.find((t) => t.tool === 'delegate_task')
  if (delegate) {
    const to = AGENT_BY_NAME[delegate.args.to_agent as AgentName]?.label ?? String(delegate.args.to_agent)
    return `Handing off to ${to}`
  }
  const labels = [...new Set(tools.map((t) => TOOL_LABELS[t.tool] ?? t.tool))]
  return labels.length ? labels.join(', ').replace(/^./, (c) => c.toUpperCase()) : 'Thinking…'
}

export function outputText(output?: AgentOutput): string | undefined {
  return output?.decision ?? output?.summary
}

/** Replay a run's events (oldest first) into one state per agent. */
export function deriveAgentStates(events: ActivityEvent[]): Record<AgentName, AgentState> {
  const states = Object.fromEntries(
    AGENTS.map((a): [AgentName, AgentState] => [a.name, { phase: 'idle', line: 'Standing by', tools: [], lastAt: null, involved: false }]),
  ) as Record<AgentName, AgentState>

  for (const e of events) {
    const s = e.agent ? states[e.agent] : undefined
    if (!s) continue
    s.lastAt = e.timestamp
    s.involved = true
    switch (e.event) {
      case 'agent_start':
        s.phase = 'working'
        s.line = e.depth ? 'Picked up a task — thinking…' : 'Reading the ticket…'
        break
      case 'model_response':
        s.phase = 'working'
        s.tools.push(...e.tools)
        s.line = e.said ?? describeTools(e.tools)
        break
      case 'delegation': {
        s.phase = 'waiting'
        const to = e.to_agent ? AGENT_BY_NAME[e.to_agent].label : 'a teammate'
        s.line = `Waiting on ${to}`
        break
      }
      case 'delegation_refused':
        s.line = e.said ?? 'Delegation refused'
        break
      case 'agent_end':
        s.phase = 'done'
        s.line = outputText(e.details?.output) ?? 'Finished'
        break
      case 'agent_error':
        s.phase = 'error'
        s.line = e.said ?? 'Error'
        break
    }
  }
  return states
}
