import { useState } from 'react'
import { STATUS_LABELS, TYPE_LABELS, deskStatus, fmtMoney } from '../format'
import type { Approval, Ticket } from '../types'

interface Props {
  ticket: Ticket
  otherRunning: boolean
  starting: boolean
  onRun: () => void
}

export function TicketHeader({ ticket, otherRunning, starting, onRun }: Props) {
  const status = deskStatus(ticket)
  const running = status === 'running'
  const resolved = status === 'resolved'
  const label = resolved ? 'Resolved' : running || starting ? 'Agents working…' : ticket.agent_result ? 'Run agents again' : 'Start agent team'
  return (
    <section className={`card ticket-header status-${status}`}>
      <div className="th-main">
        <div className="th-kicker">
          <span>#{ticket.id}</span> · <span>{TYPE_LABELS[ticket.type] ?? ticket.type}</span> · <span>{ticket.requester}</span>
        </div>
        <h1>{ticket.subject}</h1>
        {ticket.notes && <p className="th-notes">“{ticket.notes}”</p>}
        <div className="th-facts">
          {ticket.sku && <span>{ticket.qty} × <code>{ticket.sku}</code> size {ticket.size}</span>}
          {ticket.invoice_id && <span>Invoice #{ticket.invoice_id}</span>}
          {ticket.lease_id && <span>Lease #{ticket.lease_id}</span>}
        </div>
      </div>
      <div className="th-side">
        <span className={`status-chip big ${status}`}>
          {running && <span className="spinner" />}
          {STATUS_LABELS[status]}
        </span>
        <button className="btn primary" onClick={onRun} disabled={resolved || running || starting || otherRunning}>
          {(running || starting) && <span className="spinner light" />}
          {label}
        </button>
        {otherRunning && !running && <span className="hint">Another ticket is running — one run at a time.</span>}
      </div>
    </section>
  )
}

export function Decision({ ticket, approvals }: { ticket: Ticket; approvals: Approval[] }) {
  const r = ticket.agent_result
  if (!r) return null
  const status = deskStatus(ticket)
  const signed = approvals.filter((a) => a.ticket_id === ticket.id && a.status === 'approved')
  return (
    <section className={`card decision status-${status}`}>
      <div className="panel-head">
        <h3>Boss's decision</h3>
        <span className={`status-chip ${status}`}>{STATUS_LABELS[status]}</span>
      </div>
      {status === 'resolved' && (
        <p className="resolved-note">
          <span className="check">✓</span>
          Resolved
          {signed.length > 0 &&
            ` · ${signed.map((a) => `${fmtMoney(Number(a.execution?.amount ?? 0))} approved by ${a.approved_by}`).join(', ')}`}
        </p>
      )}
      {status === 'resolved' && <div className="decision-label">Agents' decision at the end of the run</div>}
      <p className="decision-text">{r.decision}</p>
      {r.open_issues.length > 0 && (
        <ul className="issues">
          {r.open_issues.map((i, n) => <li key={n}>{i}</li>)}
        </ul>
      )}
      {r.message_drafts.length > 0 && (
        <div className="drafts">
          <h4>Drafted messages <span className="not-sent">Draft · not sent</span></h4>
          {r.message_drafts.map((m, n) => (
            <article key={n} className="draft">
              <div className="draft-head"><span>To: <strong>{m.to}</strong></span><span>{m.subject}</span></div>
              <pre>{m.body}</pre>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

interface DecisionProps {
  ticket: Ticket
  approverName: string
  onDecide: (text: string) => Promise<void>
}

/** Lets a person answer a judgment call the agents flagged; the next run carries it out. */
export function HumanDecisionBox({ ticket, approverName, onDecide }: DecisionProps) {
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const status = deskStatus(ticket)
  if (status !== 'needs_human' && ticket.decisions.length === 0) return null

  async function save() {
    setSaving(true)
    try {
      await onDecide(text.trim())
      setText('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="card human-decision">
      <div className="panel-head">
        <h3>Your decision</h3>
        <span className="count">passed to the agents on the next run</span>
      </div>
      {ticket.decisions.map((d, i) => (
        <div key={i} className="decision-entry">
          <span className="check">✓</span>
          <div>
            <p>{d.decision}</p>
            <span className="stuck-reason">— {d.decided_by}</span>
          </div>
        </div>
      ))}
      {status !== 'resolved' && status !== 'running' && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Grant 10% off ($52.20) on the 8 in stock; don't restock the rest."
            rows={3}
          />
          <div className="decision-actions">
            <span className="hint">{approverName.trim() ? `Signed as ${approverName}` : 'Enter your name in the sign-off tray first.'}</span>
            <button className="btn primary" onClick={save} disabled={saving || !text.trim() || !approverName.trim()}>
              Record decision
            </button>
          </div>
        </>
      )}
    </section>
  )
}
