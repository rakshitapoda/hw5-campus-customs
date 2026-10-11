import { AGENT_BY_NAME } from '../agents'
import type { AgentName } from '../types'

const ICON_PATHS: Record<AgentName, string> = {
  boss: 'M3 18h18l-1.5-9-4.5 4-3-7-3 7-4.5-4L3 18zm0 2h18v1.5H3V20z',
  inventory: 'M12 2 3 6.5v11L12 22l9-4.5v-11L12 2zm0 2.2 6.6 3.3L12 10.8 5.4 7.5 12 4.2zM5 9.2l6 3v7.6l-6-3V9.2zm8 10.6v-7.6l6-3v7.6l-6 3z',
  accounting: 'M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm1 3v4h10V5H7zm0 7v2h2v-2H7zm4 0v2h2v-2h-2zm4 0v6h2v-6h-2zm-8 4v2h2v-2H7zm4 0v2h2v-2h-2z',
  facilities: 'M4 21V9l8-6 8 6v12h-6v-6h-4v6H4zm2-2h2v-6h8v6h2v-9l-6-4.5L6 10v9z',
  customer_service: 'M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 5v2h10V9H7zm0 4v2h7v-2H7z',
}

export function AgentIcon({ name, size = 20 }: { name: AgentName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d={ICON_PATHS[name]} fill="currentColor" />
    </svg>
  )
}

export function AgentBadge({ name, size = 36, pulse = false }: { name: AgentName; size?: number; pulse?: boolean }) {
  const a = AGENT_BY_NAME[name]
  return (
    <span
      className={`agent-badge${pulse ? ' pulse' : ''}`}
      style={{ width: size, height: size, background: a.color, ['--agent' as string]: a.color }}
      title={a.label}
    >
      <AgentIcon name={name} size={Math.round(size * 0.55)} />
    </span>
  )
}

export function AgentChip({ name }: { name: AgentName }) {
  const a = AGENT_BY_NAME[name]
  return (
    <span className="agent-chip" style={{ color: a.color, background: a.soft, borderColor: `${a.color}33` }}>
      <AgentIcon name={name} size={13} />
      {a.label}
    </span>
  )
}
