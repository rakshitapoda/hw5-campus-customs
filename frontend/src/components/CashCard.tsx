import { useEffect, useRef, useState } from 'react'
import { fmtMoney } from '../format'
import type { Approval, Cash } from '../types'

export function CashCard({ cash, approvals }: { cash: Cash | null; approvals: Approval[] }) {
  const [delta, setDelta] = useState<number | null>(null)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    if (prev.current != null && prev.current !== cash.balance) {
      setDelta(cash.balance - prev.current)
      const t = setTimeout(() => setDelta(null), 4000)
      prev.current = cash.balance
      return () => clearTimeout(t)
    }
    prev.current = cash.balance
  }, [cash])

  const balance = cash?.balance ?? 0
  const amountOf = (a: Approval) => Number(a.proposal.amount ?? a.proposal.total_cost ?? 0)
  const pending = approvals.filter((a) => a.status === 'pending').reduce((s, a) => s + amountOf(a), 0)
  const paid = approvals.filter((a) => a.status === 'approved').reduce((s, a) => s + Number(a.execution?.amount ?? amountOf(a)), 0)
  const after = balance - pending
  const scale = Math.max(balance + paid, 1)
  const pct = (n: number) => `${Math.max(0, Math.min(100, (n / scale) * 100))}%`

  return (
    <section className="card cash">
      <div className="panel-head">
        <h3>Checking</h3>
        <span className="count">cash_accounts · {cash?.date ?? '—'}</span>
      </div>
      <div className="cash-figure">
        <span className="cash-amount">{cash ? fmtMoney(balance) : '—'}</span>
        {delta != null && <span className={`cash-delta ${delta < 0 ? 'out' : 'in'}`}>{delta < 0 ? '−' : '+'}{fmtMoney(Math.abs(delta))}</span>}
      </div>
      <div className="cash-bar" aria-hidden="true">
        <span className="seg remaining" style={{ width: pct(Math.max(after, 0)) }} />
        <span className="seg pending" style={{ width: pct(Math.min(pending, balance)) }} />
        <span className="seg paid" style={{ width: pct(paid) }} />
      </div>
      <dl className="cash-rows">
        <div><dt><i className="key paid" />Paid out (approved)</dt><dd>{fmtMoney(paid)}</dd></div>
        <div><dt><i className="key pending" />Awaiting your approval</dt><dd>{fmtMoney(pending)}</dd></div>
        <div className={after < 0 ? 'neg' : ''}><dt><i className="key remaining" />Left if all approved</dt><dd>{fmtMoney(after)}</dd></div>
      </dl>
      {after < 0 && <p className="cash-warn">Approving everything would overdraw checking. Payments that go below $0 will be refused.</p>}
      <p className="cash-note">Cash only flows out here: nothing moves until a person approves it.</p>
    </section>
  )
}
