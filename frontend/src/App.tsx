import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { deriveAgentStates } from './agents'
import { fmtMoney } from './format'
import { ActivityFeed } from './components/ActivityFeed'
import { AgentFloor } from './components/AgentFloor'
import { AgentSummaries } from './components/AgentSummaries'
import { ApprovalTray } from './components/ApprovalTray'
import { CashCard } from './components/CashCard'
import { Decision, HumanDecisionBox, TicketHeader } from './components/TicketDetail'
import { TicketQueue } from './components/TicketQueue'
import { TopBar } from './components/TopBar'
import type { ActivityEvent, Approval, Cash, Ticket } from './types'

const REFRESH_MS = 5000
const LIVE_MS = 1500

interface Toast {
  id: number
  kind: 'ok' | 'err' | 'info'
  text: string
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [online, setOnline] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [feed, setFeed] = useState<{ runId: string | null; events: ActivityEvent[] }>({ runId: null, events: [] })
  const [startingId, setStartingId] = useState<number | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approverName, setApproverName] = useState(() => localStorage.getItem('cc-approver') ?? '')

  const toast = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, kind, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [t, a, c] = await Promise.all([api.tickets(), api.approvals(), api.cash()])
      setTickets(t)
      setApprovals(a)
      setCash(c)
      setOnline(true)
      setSelectedId((id) => id ?? t[0]?.id ?? null)
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, REFRESH_MS)
    return () => clearInterval(timer)
  }, [refresh])

  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const runningTicket = tickets.find((t) => t.running_run_id)
  const viewRunId = selected?.running_run_id ?? selected?.agent_result?.run_id ?? null
  const live = Boolean(selected?.running_run_id)

  // Activity for the run shown on the desk; polled quickly while agents are working.
  useEffect(() => {
    if (!viewRunId) return
    let cancelled = false
    const load = () =>
      api
        .activity({ runId: viewRunId })
        .then((e) => !cancelled && setFeed({ runId: viewRunId, events: [...e].reverse() }))
        .catch(() => {})
    load()
    if (!live) return () => { cancelled = true }
    const timer = setInterval(load, LIVE_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [viewRunId, live])

  // While a run is active, poll its status so the desk updates the moment it finishes.
  useEffect(() => {
    const runId = runningTicket?.running_run_id
    if (!runId) return
    const timer = setInterval(async () => {
      try {
        const run = await api.run(runId)
        if (run.status !== 'running') {
          clearInterval(timer)
          await refresh()
          if (run.status === 'completed') toast('ok', `Ticket #${run.ticket_id}: agents finished. ${run.resolution?.recommended_status.replace('_', ' ')}.`)
          else toast('err', `Ticket #${run.ticket_id} run failed: ${run.error}`)
        }
      } catch {
        /* backend hiccup; next tick retries */
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [runningTicket?.running_run_id, refresh, toast])

  // Only show events for the run on screen (avoids flashing the previous ticket's feed).
  const events = useMemo(() => (feed.runId === viewRunId ? feed.events : []), [feed, viewRunId])
  const agentStates = useMemo(() => deriveAgentStates(events), [events])

  async function runSelected() {
    if (!selected) return
    setStartingId(selected.id)
    try {
      await api.runTicket(selected.id)
      toast('info', `Agent team started on ticket #${selected.id}.`)
      await refresh()
    } catch (e) {
      toast('err', (e as Error).message)
    } finally {
      setStartingId(null)
    }
  }

  async function approve(a: Approval) {
    try {
      const res = await api.approve(a.id, approverName.trim())
      toast('ok', `Paid ${fmtMoney(res.execution.amount)} · checking now ${fmtMoney(res.execution.balance_after)}${res.ticket_resolved ? ` · ticket #${a.ticket_id} resolved` : ''}`)
    } catch (e) {
      toast('err', `Not approved: ${(e as Error).message}`)
    }
    await refresh()
  }

  async function decide(text: string) {
    if (!selected) return
    try {
      await api.decide(selected.id, approverName.trim(), text)
      toast('ok', `Decision recorded for ticket #${selected.id}. Run the agents again to carry it out.`)
    } catch (e) {
      toast('err', (e as Error).message)
    }
    await refresh()
  }

  async function reset() {
    if (!confirm('Reset the desk? This restores the original database (cash, invoices, leases, tickets) and clears approvals. The audit trail is kept.')) return
    try {
      await api.reset()
      setFeed({ runId: null, events: [] })
      toast('info', 'Desk reset to the original database.')
    } catch (e) {
      toast('err', (e as Error).message)
    }
    await refresh()
  }

  function setName(name: string) {
    setApproverName(name)
    localStorage.setItem('cc-approver', name)
  }

  const pendingCount = approvals.filter((a) => a.status === 'pending').length

  return (
    <div className="app">
      <TopBar cash={cash} online={online} pendingCount={pendingCount} busy={Boolean(runningTicket)} onReset={reset} />
      {!online && (
        <div className="offline-banner">
          Can't reach the backend. Start it with <code>cd backend && uvicorn main:app --reload --port 8000</code>
        </div>
      )}
      <main className="layout">
        <TicketQueue tickets={tickets} selectedId={selectedId} onSelect={setSelectedId} />

        <div className="center">
          {selected ? (
            <>
              <TicketHeader
                ticket={selected}
                otherRunning={Boolean(runningTicket && runningTicket.id !== selected.id)}
                starting={startingId === selected.id}
                onRun={runSelected}
              />
              <AgentFloor states={agentStates} live={live} />
              <Decision ticket={selected} approvals={approvals} />
              <HumanDecisionBox ticket={selected} approverName={approverName} onDecide={decide} />
              <div className="center-grid">
                <ActivityFeed events={events} live={live} />
                <AgentSummaries events={events} />
              </div>
            </>
          ) : (
            <div className="card empty big">{online ? 'Loading tickets…' : 'Waiting for the backend…'}</div>
          )}
        </div>

        <div className="rail">
          <CashCard cash={cash} approvals={approvals} />
          <ApprovalTray
            approvals={approvals}
            cash={cash}
            selectedTicketId={selectedId}
            approverName={approverName}
            onApproverName={setName}
            onApprove={approve}
          />
        </div>
      </main>

      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>
        ))}
      </div>
    </div>
  )
}
