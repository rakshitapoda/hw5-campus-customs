import { AGENTS, AGENT_BY_NAME } from '../agents'
import { AgentBadge } from './AgentBadge'
import { prettyTool } from '../format'
import type { ActivityEvent, AgentName, AgentOutput } from '../types'

interface Summary {
  tools: Map<string, number>
  delegatedTo: AgentName[]
  output?: AgentOutput
}

function summarize(events: ActivityEvent[]): Map<AgentName, Summary> {
  const out = new Map<AgentName, Summary>()
  for (const e of events) {
    if (!e.agent) continue
    const s: Summary = out.get(e.agent) ?? { tools: new Map<string, number>(), delegatedTo: [] }
    out.set(e.agent, s)
    if (e.event === 'model_response') {
      for (const t of e.tools) {
        if (t.tool === 'final_result' || t.tool === 'delegate_task') continue
        s.tools.set(t.tool, (s.tools.get(t.tool) ?? 0) + 1)
      }
    }
    if (e.event === 'delegation' && e.to_agent && !s.delegatedTo.includes(e.to_agent)) s.delegatedTo.push(e.to_agent)
    if (e.event === 'agent_end') s.output = e.details?.output
  }
  return out
}

export function AgentSummaries({ events }: { events: ActivityEvent[] }) {
  const summaries = summarize(events)
  const involved = AGENTS.filter((a) => summaries.has(a.name))
  return (
    <section className="card summaries">
      <div className="panel-head">
        <h3>What each agent did</h3>
        <span className="count">{involved.length} of 5 agents</span>
      </div>
      {involved.length === 0 && <p className="empty">Summaries appear here once the agents have worked this ticket.</p>}
      <div className="summary-list">
        {involved.map((a) => {
          const s = summaries.get(a.name)!
          const text = s.output?.decision ?? s.output?.summary
          return (
            <article key={a.name} className="summary" style={{ ['--agent' as string]: a.color, ['--agent-soft' as string]: a.soft }}>
              <div className="summary-head">
                <AgentBadge name={a.name} size={28} />
                <strong>{a.label}</strong>
                {s.delegatedTo.length > 0 && (
                  <span className="handoffs">
                    → {s.delegatedTo.map((d) => AGENT_BY_NAME[d].label).join(', ')}
                  </span>
                )}
              </div>
              <p>{text ?? 'Still working…'}</p>
              {s.tools.size > 0 && (
                <div className="tool-row">
                  {[...s.tools].map(([t, n]) => (
                    <span key={t} className="tool-chip">{prettyTool(t)}{n > 1 ? ` ×${n}` : ''}</span>
                  ))}
                </div>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
