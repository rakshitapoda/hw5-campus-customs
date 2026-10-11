import { AgentChip } from './AgentBadge'
import { STATUS_LABELS, TYPE_LABELS, deskStatus } from '../format'
import type { Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export function TicketQueue({ tickets, selectedId, onSelect }: Props) {
  const open = tickets.filter((t) => t.status !== 'resolved').length
  return (
    <aside className="queue">
      <div className="panel-head">
        <h2>Ticket queue</h2>
        <span className="count">{open} open · {tickets.length - open} resolved</span>
      </div>
      <div className="stubs">
        {tickets.map((t) => {
          const status = deskStatus(t)
          return (
            <button
              key={t.id}
              className={`stub status-${status} ${t.id === selectedId ? 'selected' : ''}`}
              onClick={() => onSelect(t.id)}
            >
              <div className="stub-top">
                <span className="stub-id">#{t.id}</span>
                <span className="stub-type">{TYPE_LABELS[t.type] ?? t.type}</span>
              </div>
              <div className="stub-subject">{t.subject}</div>
              <div className="stub-requester">{t.requester}</div>
              {t.sku && (
                <div className="stub-line">
                  {t.qty} × {t.sku} · size {t.size}
                </div>
              )}
              {t.lease_id && <div className="stub-line">Lease #{t.lease_id}</div>}
              <div className="stub-foot">
                {status === 'resolved' ? (
                  <span className="stamp">Resolved</span>
                ) : (
                  <span className={`status-chip ${status}`}>
                    {status === 'running' && <span className="spinner" />}
                    {STATUS_LABELS[status]}
                  </span>
                )}
                {t.approvals.pending > 0 && <span className="approve-dot">{t.approvals.pending} to sign</span>}
              </div>
              {t.agent_result && status !== 'running' && (
                <div className="stub-agents">
                  {t.agent_result.assigned_agents.filter((a) => a !== 'boss').map((a) => (
                    <AgentChip key={a} name={a} />
                  ))}
                </div>
              )}
            </button>
          )
        })}
      </div>
    </aside>
  )
}
