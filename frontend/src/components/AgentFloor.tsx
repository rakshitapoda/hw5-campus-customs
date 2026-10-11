import { AGENTS, type AgentState } from '../agents'
import { AgentBadge } from './AgentBadge'
import { prettyTool } from '../format'
import type { AgentName } from '../types'

interface Props {
  states: Record<AgentName, AgentState>
  live: boolean
}

const PHASE_LABEL = { idle: 'Standing by', working: 'Working', waiting: 'Waiting', done: 'Done', error: 'Error' }

export function AgentFloor({ states, live }: Props) {
  return (
    <section className="floor">
      {AGENTS.map((a) => {
        const s = states[a.name]
        const active = live && (s.phase === 'working' || s.phase === 'waiting')
        const usedTools = [...new Set(s.tools.map((t) => t.tool).filter((t) => t !== 'delegate_task'))]
        return (
          <article
            key={a.name}
            className={`station phase-${s.phase} ${s.involved ? '' : 'uninvolved'} ${active ? 'active' : ''}`}
            style={{ ['--agent' as string]: a.color, ['--agent-soft' as string]: a.soft }}
          >
            <div className="station-head">
              <AgentBadge name={a.name} size={40} pulse={active && s.phase === 'working'} />
              <div>
                <div className="station-name">{a.label}</div>
                <div className="station-role">{a.role}</div>
              </div>
              <span className={`phase-tag ${s.phase}`}>{PHASE_LABEL[s.phase]}</span>
            </div>
            <div className="bubble">
              {active && s.phase === 'working' && <span className="typing"><i /><i /><i /></span>}
              <span>{s.involved ? s.line : 'Not on this ticket'}</span>
            </div>
            {usedTools.length > 0 && (
              <div className="tool-row">
                {usedTools.map((t) => (
                  <span key={t} className="tool-chip">{prettyTool(t)}</span>
                ))}
              </div>
            )}
          </article>
        )
      })}
    </section>
  )
}
