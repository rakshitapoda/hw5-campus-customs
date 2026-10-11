import type { Ticket } from './types'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
export const fmtMoney = (n: number) => money.format(n)

export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

export const TYPE_LABELS: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

export type DeskStatus = 'not_started' | 'running' | 'awaiting_approval' | 'blocked' | 'needs_human' | 'resolved'

export const STATUS_LABELS: Record<DeskStatus, string> = {
  not_started: 'Not started',
  running: 'Agents working',
  awaiting_approval: 'Needs your approval',
  blocked: 'Blocked',
  needs_human: 'Needs a decision',
  resolved: 'Resolved',
}

export function deskStatus(t: Ticket): DeskStatus {
  if (t.status === 'resolved') return 'resolved'
  if (t.running_run_id) return 'running'
  const rec = t.agent_result?.recommended_status
  // Once every approvable item is signed off, a ticket still waiting on a blocked item reads as blocked.
  if (rec === 'awaiting_approval' && t.approvals.pending === 0 && t.approvals.blocked > 0) return 'blocked'
  return rec ?? 'not_started'
}

export const prettyTool = (tool: string) => tool.replace(/_/g, ' ')
