import { useState } from 'react'
import { AgentChip } from './AgentBadge'
import { fmtMoney } from '../format'
import type { Approval, Cash } from '../types'

interface Props {
  approvals: Approval[]
  cash: Cash | null
  selectedTicketId: number | null
  approverName: string
  onApproverName: (name: string) => void
  onApprove: (a: Approval) => Promise<void>
}

const amountOf = (a: Approval) => Number(a.proposal.amount ?? a.proposal.total_cost ?? 0)

function title(a: Approval): string {
  const p = a.proposal
  if (a.item_type === 'payment') return p.kind === 'rent' ? `Rent · lease #${p.ref_id}` : `Invoice #${p.ref_id}`
  return `Restock ${p.qty} × ${p.sku} (${p.size})`
}

function payee(a: Approval): string {
  return a.proposal.payee ?? a.proposal.vendor_name ?? ''
}

export function ApprovalTray({ approvals, cash, selectedTicketId, approverName, onApproverName, onApprove }: Props) {
  const [confirming, setConfirming] = useState<Approval | null>(null)
  const [working, setWorking] = useState(false)

  const byTicketFirst = (list: Approval[]) =>
    [...list].sort((x, y) => Number(y.ticket_id === selectedTicketId) - Number(x.ticket_id === selectedTicketId))
  const pending = byTicketFirst(approvals.filter((a) => a.status === 'pending'))
  const stuck = byTicketFirst(approvals.filter((a) => a.status === 'blocked' || a.status === 'refused'))
  const done = approvals.filter((a) => a.status === 'approved')

  async function confirm() {
    if (!confirming) return
    setWorking(true)
    try {
      await onApprove(confirming)
      setConfirming(null)
    } finally {
      setWorking(false)
    }
  }

  const balance = cash?.balance ?? 0
  return (
    <section className="card tray">
      <div className="panel-head">
        <h3>Sign-off tray</h3>
        <span className={`count ${pending.length ? 'attn' : ''}`}>{pending.length} waiting</span>
      </div>
      <label className="approver">
        <span>Approving as</span>
        <input value={approverName} onChange={(e) => onApproverName(e.target.value)} placeholder="Your name" />
      </label>

      {pending.length === 0 && <p className="empty">Nothing needs your signature. Agents only <em>prepare</em> payments; they show up here for you to approve.</p>}

      {pending.map((a) => {
        const after = balance - amountOf(a)
        return (
          <article key={a.id} className={`slip ${a.ticket_id === selectedTicketId ? 'current' : ''}`}>
            <div className="slip-top">
              <span className="slip-kind">{a.item_type === 'payment' ? 'Payment' : 'Purchase order'}</span>
              <span className="slip-ticket">Ticket #{a.ticket_id}</span>
            </div>
            <div className="slip-title">{title(a)}</div>
            <div className="slip-payee">to {payee(a)}</div>
            <div className="slip-amount">{fmtMoney(amountOf(a))}</div>
            <div className={`slip-after ${after < 0 ? 'neg' : ''}`}>
              Checking after: <strong>{fmtMoney(after)}</strong>
              {after < 0 && ' · will be refused'}
            </div>
            <div className="slip-foot">
              {a.prepared_by && <span>Prepared by <AgentChip name={a.prepared_by} /></span>}
              <button className="btn approve" onClick={() => setConfirming(a)} disabled={!approverName.trim()}>
                Approve
              </button>
            </div>
          </article>
        )
      })}

      {stuck.length > 0 && (
        <div className="stuck">
          <h4>Can't be approved yet</h4>
          {stuck.map((a) => (
            <div key={a.id} className={`stuck-row ${a.status}`}>
              <div>
                <strong>{title(a)}</strong> · {fmtMoney(amountOf(a))} <span className="slip-ticket">#{a.ticket_id}</span>
                <div className="stuck-reason">{a.proposal.reason ?? a.status}</div>
              </div>
              <span className={`status-chip ${a.status === 'blocked' ? 'blocked' : 'needs_human'}`}>{a.status}</span>
            </div>
          ))}
        </div>
      )}

      {done.length > 0 && (
        <div className="done">
          <h4>Approved</h4>
          {done.map((a) => (
            <div key={a.id} className="done-row">
              <span className="check">✓</span>
              <div>
                <strong>{title(a)}</strong> · {fmtMoney(Number(a.execution?.amount ?? amountOf(a)))}
                <div className="stuck-reason">by {a.approved_by} · payment #{a.execution?.payment_id}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {confirming && (
        <div className="modal-backdrop" onClick={() => !working && setConfirming(null)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h3>Approve this {confirming.item_type === 'payment' ? 'payment' : 'purchase order'}?</h3>
            <p className="modal-title">{title(confirming)} → {payee(confirming)}</p>
            <div className="modal-amount">{fmtMoney(amountOf(confirming))}</div>
            <dl className="cash-rows">
              <div><dt>Checking now</dt><dd>{fmtMoney(balance)}</dd></div>
              <div className={balance - amountOf(confirming) < 0 ? 'neg' : ''}><dt>Checking after</dt><dd>{fmtMoney(balance - amountOf(confirming))}</dd></div>
            </dl>
            <p className="modal-note">
              Signed by <strong>{approverName}</strong>. This records the payment and debits cash. It can't be undone except by resetting the desk.
            </p>
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setConfirming(null)} disabled={working}>Cancel</button>
              <button className="btn approve" onClick={confirm} disabled={working}>
                {working && <span className="spinner light" />} Approve & pay
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
