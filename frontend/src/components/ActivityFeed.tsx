import { AGENT_BY_NAME, describeTools, outputText } from '../agents'
import { AgentBadge } from './AgentBadge'
import { fmtTime, prettyTool } from '../format'
import type { ActivityEvent } from '../types'

function describe(e: ActivityEvent): { title: string; body?: string } | null {
  const who = e.agent ? AGENT_BY_NAME[e.agent].label : 'Desk'
  switch (e.event) {
    case 'run_start':
      return { title: 'Run started', body: 'The Boss picks up the ticket.' }
    case 'run_end':
      return { title: 'Run finished' }
    case 'agent_start':
      return { title: `${who} picked up the work`, body: e.depth ? (e.details?.prompt as string | undefined)?.split('\n').slice(1).join(' ') : undefined }
    case 'model_response':
      if (!e.tools.length && !e.said) return null
      return { title: `${who}: ${describeTools(e.tools)}`, body: e.said ?? undefined }
    case 'delegation':
      return { title: `${who} → ${e.to_agent ? AGENT_BY_NAME[e.to_agent].label : '?'}`, body: e.said ?? undefined }
    case 'delegation_refused':
      return { title: `${who}: delegation refused`, body: e.said ?? undefined }
    case 'agent_end':
      return { title: `${who} reported back`, body: outputText(e.details?.output) }
    case 'agent_error':
    case 'ticket_timeout':
      return { title: `${who}: error`, body: e.said ?? undefined }
    default:
      return null
  }
}

export function ActivityFeed({ events, live }: { events: ActivityEvent[]; live: boolean }) {
  const rows = [...events].reverse().map((e, i) => ({ e, d: describe(e), i })).filter((r) => r.d)
  return (
    <section className="card feed">
      <div className="panel-head">
        <h3>Live feed</h3>
        {live ? <span className="live-tag"><span className="dot" /> Live</span> : <span className="count">{rows.length} steps</span>}
      </div>
      {rows.length === 0 && <p className="empty">No agent activity for this ticket yet. Start the agents to watch them work.</p>}
      <ol className="feed-list">
        {rows.map(({ e, d, i }) => {
          const color = e.agent ? AGENT_BY_NAME[e.agent].color : '#64748b'
          return (
            <li key={`${e.timestamp}-${i}`} style={{ ['--agent' as string]: color }} className={`feed-row ev-${e.event}`}>
              <div className="feed-icon">{e.agent ? <AgentBadge name={e.agent} size={26} /> : <span className="desk-dot" />}</div>
              <div className="feed-main">
                <div className="feed-title">
                  <span>{d!.title}</span>
                  <time>{fmtTime(e.timestamp)}</time>
                </div>
                {d!.body && <p className="feed-body">{d!.body}</p>}
                {e.tools.filter((t) => t.tool !== 'final_result' && t.tool !== 'delegate_task').length > 0 && (
                  <div className="tool-row">
                    {e.tools.filter((t) => t.tool !== 'delegate_task').map((t, j) => (
                      <span key={j} className="tool-chip" title={JSON.stringify(t.args)}>
                        {prettyTool(t.tool)}
                        {Object.keys(t.args).length > 0 && <em>({Object.values(t.args).map(String).join(', ')})</em>}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
