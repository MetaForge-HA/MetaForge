import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Circle,
  ChevronDown,
  ChevronRight,
  Cpu,
  Zap,
  Code2,
  Activity,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/shared/StatusBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { formatRelativeTime } from '../utils/format-time';
import { useSession } from '../hooks/use-sessions';
import { useScopedChat } from '../hooks/use-scoped-chat';
import { SessionChatPanel } from '../components/chat/integrations/SessionChatPanel';
import type { AgentEvent } from '../types/session';

// ── Agent type icon map ───────────────────────────────────────────────────────

const AGENT_ICONS: Record<string, React.ReactNode> = {
  MECH: <Cpu size={14} />,
  ELEC: <Zap size={14} />,
  FW:   <Code2 size={14} />,
  SIM:  <Activity size={14} />,
};

function AgentIcon({ agentCode }: { agentCode: string }) {
  return (
    <span className="text-zinc-500 dark:text-zinc-400">
      {AGENT_ICONS[agentCode] ?? <Activity size={14} />}
    </span>
  );
}

// ── Stage status circle on the timeline rail ──────────────────────────────────

function StageCircle({ type }: { type: AgentEvent['type'] }) {
  switch (type) {
    case 'task_completed':
      return (
        <CheckCircle2
          size={20}
          className="text-green-500"
          aria-label="completed"
        />
      );
    case 'task_failed':
      return (
        <XCircle size={20} className="text-red-500" aria-label="failed" />
      );
    case 'task_started':
      return (
        <Clock size={20} className="text-yellow-500" aria-label="running" />
      );
    default:
      return (
        <Circle size={20} className="text-zinc-400" aria-label="pending" />
      );
  }
}

// ── Duration helpers ──────────────────────────────────────────────────────────

function formatDurationMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function sessionDuration(startedAt: string, completedAt?: string): string {
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const ms = end - start;
  if (Number.isNaN(ms) || ms < 0) return '';
  return formatDurationMs(ms);
}

function eventDuration(events: AgentEvent[], idx: number): string {
  const current = events[idx];
  const next = events[idx + 1];
  if (!current || !next) return '';
  const start = new Date(current.timestamp).getTime();
  const end = new Date(next.timestamp).getTime();
  const ms = end - start;
  if (Number.isNaN(ms) || ms <= 0) return '';
  return formatDurationMs(ms);
}

// ── Log line component ────────────────────────────────────────────────────────

function LogLine({ line }: { line: string }) {
  const lower = line.toLowerCase();
  if (lower.includes('error')) {
    return (
      <div className="border-l-2 border-red-500 pl-2 text-red-700 dark:text-red-400">
        {line}
      </div>
    );
  }
  if (lower.includes('warn')) {
    return (
      <div className="border-l-2 border-yellow-500 pl-2 text-yellow-700 dark:text-yellow-400">
        {line}
      </div>
    );
  }
  return <div className="pl-2">{line}</div>;
}

// ── Stage node ────────────────────────────────────────────────────────────────

interface StageNodeProps {
  event: AgentEvent;
  duration: string;
  isLast: boolean;
  defaultExpanded: boolean;
  globalSearch: string;
}

function StageNode({ event, duration, isLast, defaultExpanded, globalSearch }: StageNodeProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Split message into individual log lines for filtering
  const allLines = useMemo(() => event.message.split('\n').filter(Boolean), [event.message]);

  const visibleLines = useMemo(() => {
    if (!globalSearch.trim()) return allLines;
    const lower = globalSearch.toLowerCase();
    return allLines.filter((l) => l.toLowerCase().includes(lower));
  }, [allLines, globalSearch]);

  return (
    <div className="relative flex gap-4">
      {/* Timeline rail */}
      <div className="flex flex-col items-center">
        <StageCircle type={event.type} />
        {!isLast && (
          <div className="mt-1 w-0.5 flex-1 bg-zinc-200 dark:bg-zinc-700" />
        )}
      </div>

      {/* Stage content */}
      <div className="mb-6 min-w-0 flex-1 last:mb-0">
        {/* Header — clickable to expand/collapse */}
        <button
          type="button"
          className="flex w-full items-center gap-2 text-left"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          data-testid={`stage-header-${event.id}`}
        >
          {expanded ? (
            <ChevronDown size={14} className="shrink-0 text-zinc-400" />
          ) : (
            <ChevronRight size={14} className="shrink-0 text-zinc-400" />
          )}
          <AgentIcon agentCode={event.agentCode} />
          <span className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {event.message.split('\n')[0]}
          </span>
          <StatusBadge status={event.type.replace('task_', '')} className="shrink-0" />
          {duration && (
            <Badge variant="default" className="shrink-0 font-mono text-xs">
              {duration}
            </Badge>
          )}
        </button>

        {/* Expanded log area */}
        {expanded && (
          <div className="mt-2 rounded-md border border-zinc-200 bg-zinc-50 p-3 font-mono text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            {visibleLines.length === 0 ? (
              <div className="text-zinc-400">
                {globalSearch ? 'No lines match search.' : 'No log lines.'}
              </div>
            ) : (
              <div className="space-y-0.5">
                {visibleLines.map((line, i) => (
                  <LogLine key={i} line={line} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: session, isLoading, isError, refetch } = useSession(id);
  const [logSearch, setLogSearch] = useState('');

  const chat = useScopedChat({
    scopeKind: 'session',
    entityId: id ?? '',
  });

  if (isLoading) {
    return (
      <div data-testid="loading-skeleton">
        <div className="mb-6">
          <div className="mb-1 h-4 w-20 animate-pulse rounded bg-zinc-200 dark:bg-zinc-700" />
          <div className="mb-4 h-7 w-64 animate-pulse rounded bg-zinc-200 dark:bg-zinc-700" />
        </div>
        <SkeletonList rows={4} />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <div className="mb-1">
          <Link
            to="/sessions"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            &larr; Sessions
          </Link>
        </div>
        <Card className="mt-4 flex flex-col items-center py-12 text-center">
          <p className="text-base font-medium text-red-600 dark:text-red-400">
            Failed to load session
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            There was a problem fetching session details.
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  if (!session) {
    return (
      <EmptyState
        title="Session not found"
        description="The session you're looking for doesn't exist."
      />
    );
  }

  const totalDuration = sessionDuration(session.startedAt, session.completedAt);

  return (
    <div>
      <div className="mb-1">
        <Link
          to="/sessions"
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          &larr; Sessions
        </Link>
      </div>

      {/* Session header */}
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300">
          {session.agentCode}
        </div>
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            {session.taskType.replace(/_/g, ' ')}
          </h2>
          <span className="text-xs text-zinc-400">
            Started {formatRelativeTime(session.startedAt)}
          </span>
        </div>
        <StatusBadge status={session.status} />
        {totalDuration && (
          <Badge variant="default" className="font-mono text-xs" data-testid="total-duration">
            {totalDuration}
          </Badge>
        )}
      </div>

      {/* Meta cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {session.id}
          </div>
          <div className="text-xs text-zinc-500">Session ID</div>
        </Card>
        <Card>
          <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {session.runId ?? '\u2014'}
          </div>
          <div className="text-xs text-zinc-500">Run ID</div>
        </Card>
        <Card>
          <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {session.completedAt ? formatRelativeTime(session.completedAt) : '\u2014'}
          </div>
          <div className="text-xs text-zinc-500">Completed</div>
        </Card>
      </div>

      {/* Timeline section */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
          Timeline
        </h3>

        {session.events.length > 0 && (
          <input
            type="search"
            placeholder="Search logs..."
            value={logSearch}
            onChange={(e) => setLogSearch(e.target.value)}
            data-testid="log-search"
            className="w-48 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder-zinc-500"
          />
        )}
      </div>

      {session.events.length === 0 ? (
        <EmptyState title="No events" description="No events have been recorded yet." />
      ) : (
        <div className="space-y-0">
          {session.events.map((event, idx) => (
            <StageNode
              key={event.id}
              event={event}
              duration={eventDuration(session.events, idx)}
              isLast={idx === session.events.length - 1}
              defaultExpanded={idx === 0}
              globalSearch={logSearch}
            />
          ))}
        </div>
      )}

      {/* Session Chat Panel */}
      <div className="mt-6">
        <SessionChatPanel
          sessionId={session.id}
          sessionTitle={session.taskType.replace(/_/g, ' ')}
          thread={chat.thread}
          messages={chat.messages}
          isTyping={chat.isTyping}
          onSendMessage={chat.sendMessage}
          onCreateThread={chat.createThread}
        />
      </div>
    </div>
  );
}
