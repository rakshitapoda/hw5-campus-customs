import { API_URL } from '../api'
import type { Cash } from '../types'

interface Props {
  cash: Cash | null
  online: boolean
  pendingCount: number
  busy: boolean
  onReset: () => void
}

export function TopBar({ cash, online, pendingCount, busy, onReset }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">CC</div>
        <div>
          <div className="brand-name">Campus Customs</div>
          <div className="brand-sub">Operations Desk</div>
        </div>
      </div>
      <div className="topbar-meta">
        <span className="meta-pill">
          Books as of <strong>{cash?.date ?? '—'}</strong>
        </span>
        <span className={`meta-pill ${pendingCount ? 'attn' : ''}`}>
          {pendingCount ? `${pendingCount} awaiting sign-off` : 'No approvals waiting'}
        </span>
        <span className={`meta-pill conn ${online ? 'on' : 'off'}`} title={API_URL}>
          <span className="dot" /> {online ? 'Backend connected' : 'Backend offline'}
        </span>
        <button className="btn ghost light" onClick={onReset} disabled={busy || !online} title="Copy the original database back over the working copy">
          Reset desk
        </button>
      </div>
    </header>
  )
}
