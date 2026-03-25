import { Link } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, Circle } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { formatRelativeTime } from '../utils/format-time';
import { useSessions } from '../hooks/use-sessions';
import type { SessionStatus } from '../types/session';

// ── Status icon helpers ───────────────────────────────────────────────────────

function StatusIcon({ status }: { status: SessionStatus }) {
  switch (status) {
    case 'completed':
      return <CheckCircle size={18} className="text-green-500" aria-label="Completed" />;
    case 'failed':
      return <XCircle size={18} className="text-red-500" aria-label="Failed" />;
    case 'running':
      return <Clock size={18} className="text-yellow-500" aria-label="Running" />;
    default:
      return <Circle size={18} className="text-zinc-400" aria-label="Pending" />;
  }
}

// ── Domain tag helpers ────────────────────────────────────────────────────────

const AGENT_DOMAIN: Record<string, { label: string; variant: 'info' | 'success' | 'warning' | 'error' | 'default' }> = {
  MECH: { label: 'Mechanical', variant: 'info' },
  ELEC: { label: 'Electronics', variant: 'success' },
  FW:   { label: 'Firmware',    variant: 'warning' },
  SIM:  { label: 'Simulation',  variant: 'default' },
};

function DomainBadge({ agentCode }: { agentCode: string }) {
  const config = AGENT_DOMAIN[agentCode] ?? { label: agentCode, variant: 'default' as const };
  return (
    <Badge variant={config.variant} className="shrink-0">
      {config.label}
    </Badge>
  );
}

// ── Duration helper ───────────────────────────────────────────────────────────

function formatDuration(startedAt: string, completedAt?: string): string {
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const ms = end - start;
  if (Number.isNaN(ms) || ms < 0) return '';
  if (ms < 1000) return `${ms}ms`;
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function SessionsPage() {
  const { data: sessions, isLoading, isError, refetch } = useSessions();

  if (isLoading) {
    return (
      <div data-testid="loading-skeleton">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Agent Sessions
          </h2>
        </div>
        <SkeletonList rows={5} />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Agent Sessions
          </h2>
        </div>
        <Card className="flex flex-col items-center py-12 text-center">
          <p className="text-base font-medium text-red-600 dark:text-red-400">
            Failed to load sessions
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            There was a problem fetching agent sessions.
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  const items = sessions ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Agent Sessions
        </h2>
        <span className="text-sm text-zinc-500">{items.length} sessions</span>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No agent sessions yet"
          description="Agent sessions will appear here when workflows run."
        />
      ) : (
        <div className="space-y-3">
          {items.map((session) => (
            <Link key={session.id} to={`/sessions/${session.id}`}>
              <Card className="flex items-center justify-between transition-shadow hover:shadow-md">
                <div className="flex items-center gap-3">
                  {/* Status icon */}
                  <StatusIcon status={session.status} />

                  {/* Agent code avatar */}
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300">
                    {session.agentCode}
                  </div>

                  <div>
                    <div className="font-medium text-zinc-900 dark:text-zinc-100">
                      {session.taskType.replace(/_/g, ' ')}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-zinc-400">
                      <span>Started {formatRelativeTime(session.startedAt)}</span>
                      <span className="text-zinc-300 dark:text-zinc-600">&middot;</span>
                      <span data-testid="session-duration">
                        {formatDuration(session.startedAt, session.completedAt)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <DomainBadge agentCode={session.agentCode} />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
