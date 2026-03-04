import { type ChatThread } from '@/types/chat';
import { formatRelativeTime } from '@/utils/format-time';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChatThreadListProps {
  /** Threads to display. Should be pre-sorted (most recent first). */
  threads: ChatThread[];
  /** Called when the user clicks a thread row. */
  onSelectThread: (threadId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map scope kind to a short, human-readable badge label. */
function scopeBadgeLabel(kind: string): string {
  const map: Record<string, string> = {
    session: 'Session',
    approval: 'Approval',
    'bom-entry': 'BOM',
    'digital-twin-node': 'Twin',
    project: 'Project',
  };
  return map[kind] ?? kind;
}

/** Truncate a string to a maximum length, adding an ellipsis if needed. */
function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + '...';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders a vertical list of chat thread summaries.
 *
 * Each row shows the thread title, a preview of the last message, the
 * relative timestamp, and a scope badge. Clicking a row selects the thread.
 */
export function ChatThreadList({
  threads,
  onSelectThread,
}: ChatThreadListProps) {
  if (threads.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-4">
        <p className="text-sm text-zinc-400 dark:text-zinc-500">
          No conversations yet
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
      {threads.map((thread) => {
        const lastMessage =
          thread.messages.length > 0
            ? thread.messages[thread.messages.length - 1]
            : undefined;

        return (
          <li key={thread.id}>
            <button
              type="button"
              onClick={() => onSelectThread(thread.id)}
              className="flex w-full flex-col gap-0.5 px-4 py-3 text-left transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
            >
              {/* Top row: title + timestamp */}
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {thread.title}
                </span>
                <span className="shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
                  {formatRelativeTime(thread.lastMessageAt)}
                </span>
              </div>

              {/* Last message preview */}
              {lastMessage && (
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  <span className="font-medium">
                    {lastMessage.actor.displayName}:
                  </span>{' '}
                  {truncate(lastMessage.content, 80)}
                </span>
              )}

              {/* Scope badge */}
              <span className="mt-0.5 inline-flex self-start rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                {scopeBadgeLabel(thread.scope.kind)}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
