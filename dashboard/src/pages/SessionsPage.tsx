import { Link } from 'react-router-dom';
import { EmptyState } from '../components/ui/EmptyState';
import { formatRelativeTime } from '../utils/format-time';
import { useSessions } from '../hooks/use-sessions';
import type { AgentSession } from '../types/session';

// KC color tokens
const KC = {
  surfaceContainer: 'rgba(30,31,38,0.85)',
  surfaceHigh: '#282a30',
  surfaceBorder: 'rgba(65,72,90,0.2)',
  onSurface: '#e2e2eb',
  onSurfaceVariant: '#9a9aaa',
  running: '#e67e22',
  done: '#3dd68c',
  pending: '#9a9aaa',
  error: '#ffb4ab',
} as const;

function statusDotColor(status: AgentSession['status']): string {
  switch (status) {
    case 'running': return KC.running;
    case 'completed': return KC.done;
    case 'failed': return KC.error;
    case 'pending': return KC.pending;
    default: return KC.pending;
  }
}

function StatusDot({ status }: { status: AgentSession['status'] }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: statusDotColor(status),
        flexShrink: 0,
      }}
    />
  );
}

function SessionRow({ session }: { session: AgentSession }) {
  return (
    <Link
      to={`/sessions/${session.id}`}
      style={{ textDecoration: 'none', display: 'block' }}
    >
      <div
        className="flex items-center gap-4 px-4 transition-colors"
        style={{
          height: 40,
          borderBottom: `1px solid rgba(65,72,90,0.08)`,
          color: KC.onSurface,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.background = KC.surfaceHigh;
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.background = 'transparent';
        }}
      >
        {/* Agent code chip */}
        <span
          className="font-mono shrink-0"
          style={{
            fontSize: 10,
            background: KC.surfaceHigh,
            color: KC.onSurfaceVariant,
            padding: '2px 6px',
            borderRadius: 3,
          }}
        >
          {session.agentCode}
        </span>

        {/* Task name */}
        <span
          className="flex-1 truncate"
          style={{ fontSize: 13, color: KC.onSurface }}
        >
          {session.taskType.replace(/_/g, ' ')}
        </span>

        {/* Status dot + label */}
        <div className="flex items-center gap-1.5 shrink-0">
          <StatusDot status={session.status} />
          <span
            className="font-mono"
            style={{ fontSize: 11, color: statusDotColor(session.status) }}
          >
            {session.status}
          </span>
        </div>

        {/* Timestamp */}
        <span
          className="font-mono shrink-0"
          style={{ fontSize: 11, color: KC.onSurfaceVariant }}
        >
          {formatRelativeTime(session.startedAt)}
        </span>
      </div>
    </Link>
  );
}

export function SessionsPage() {
  const { data: sessions, isLoading } = useSessions();

  if (isLoading) {
    return <div className="text-sm" style={{ color: KC.onSurfaceVariant }}>Loading sessions...</div>;
  }

  const items = sessions ?? [];

  return (
    <div>
      {/* Page header */}
      <div className="flex items-start justify-between" style={{ marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 500, color: KC.onSurface, lineHeight: 1.2 }}>
            Sessions
          </h1>
          <span
            className="font-mono"
            style={{ fontSize: 12, color: KC.onSurfaceVariant }}
          >
            Agent sessions · {items.length} total
          </span>
        </div>
      </div>

      {/* Session list */}
      {items.length === 0 ? (
        <EmptyState
          title="No sessions"
          description="Agent sessions will appear here when workflows run."
        />
      ) : (
        <div
          className="rounded overflow-hidden"
          style={{
            background: KC.surfaceContainer,
            border: `1px solid ${KC.surfaceBorder}`,
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
          }}
        >
          {/* Panel header */}
          <div
            className="flex items-center px-4"
            style={{
              height: 36,
              borderBottom: `1px solid ${KC.surfaceBorder}`,
            }}
          >
            <span
              className="font-mono uppercase"
              style={{ fontSize: 10, letterSpacing: '0.1em', color: KC.onSurfaceVariant }}
            >
              ALL SESSIONS
            </span>
          </div>

          {/* Rows */}
          {items.map((session) => (
            <SessionRow key={session.id} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
