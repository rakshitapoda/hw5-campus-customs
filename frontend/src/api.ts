import type { ActivityEvent, Approval, Cash, HumanDecision, RunStatus, Ticket } from './types'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_URL}. Is uvicorn running?`)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : res.statusText
    throw new ApiError(res.status, message)
  }
  return body as T
}

export const api = {
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTicket: (ticketId: number) => request<RunStatus>(`/api/tickets/${ticketId}/run`, { method: 'POST' }),
  run: (runId: string) => request<RunStatus>(`/api/runs/${runId}`),
  activity: (params: { runId?: string; ticketId?: number; limit?: number }) => {
    const q = new URLSearchParams({ limit: String(params.limit ?? 500) })
    if (params.runId) q.set('run_id', params.runId)
    if (params.ticketId !== undefined) q.set('ticket_id', String(params.ticketId))
    return request<ActivityEvent[]>(`/api/activity?${q}`)
  },
  approvals: () => request<Approval[]>('/api/approvals'),
  approve: (approvalId: string, approvedBy: string) =>
    request<{ approval: Approval; execution: Record<string, any>; ticket_resolved: boolean }>(
      `/api/approvals/${approvalId}/approve`,
      { method: 'POST', body: JSON.stringify({ approved_by: approvedBy }) },
    ),
  decide: (ticketId: number, decidedBy: string, decision: string) =>
    request<HumanDecision & { ticket_id: number }>(`/api/tickets/${ticketId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: decidedBy, decision }),
    }),
  cash: () => request<Cash>('/api/cash'),
  reset: () => request<{ status: string }>('/api/reset', { method: 'POST' }),
}
