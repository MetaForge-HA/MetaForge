import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import type { ChatThread, ChatMessage } from '@/types/chat';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface SessionChatPanelProps {
  /** Session ID this chat is scoped to. */
  sessionId: string;
  /** Human-readable session title (falls back to the session ID). */
  sessionTitle?: string;
  /** Pre-resolved thread. */
  thread?: ChatThread | null;
  /** Messages for the thread. */
  messages?: ChatMessage[];
  /** Whether the agent is currently typing. */
  isTyping?: boolean;
  /** Send a user message. */
  onSendMessage?: (content: string) => void;
  /** Create a new thread for this session. */
  onCreateThread?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Full-size chat panel rendered below the trace viewer on the session
 * detail page. Unlike the other integration panels this one is **not**
 * compact — it uses larger padding, standard font sizes, and a taller
 * composer to encourage deeper technical conversation about trace steps,
 * re-runs, and diagnostics.
 *
 * Scope: `{ kind: 'session', entityId: sessionId }`
 */
export function SessionChatPanel({
  sessionId,
  sessionTitle,
  thread,
  messages = [],
  isTyping = false,
  onSendMessage,
  onCreateThread,
}: SessionChatPanelProps) {
  const [draft, setDraft] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const title = sessionTitle ?? sessionId;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isTyping]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = draft.trim();
    if (trimmed.length === 0) return;
    onSendMessage?.(trimmed);
    setDraft('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // ----- No thread yet — show CTA -----
  if (!thread) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <h3 className="mb-1 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Session: {title}
        </h3>
        <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
          Start a conversation to ask about trace steps, request re-runs, or
          discuss diagnostics for this session.
        </p>
        <button
          type="button"
          onClick={onCreateThread}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Start conversation
        </button>
      </div>
    );
  }

  // ----- Thread exists — render full-size chat -----
  return (
    <div className="flex flex-col rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-zinc-200 px-4 py-3 dark:border-zinc-700">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-900">
          <svg
            className="h-4 w-4 text-violet-600 dark:text-violet-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Session: {title}
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Ask about trace steps, request re-runs, or discuss diagnostics
          </p>
        </div>
      </div>

      {/* Message list */}
      <div className="max-h-96 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-400">No messages yet. Say something to begin.</p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-3 flex flex-col ${
              msg.actor.kind === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <span className="mb-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">
              {msg.actor.displayName}
              {msg.actor.agentCode ? ` (${msg.actor.agentCode})` : ''}
            </span>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                msg.actor.kind === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200'
              }`}
            >
              {msg.content}
            </div>
            {msg.status === 'sending' && (
              <span className="mt-1 text-xs text-zinc-400">Sending...</span>
            )}
            {msg.status === 'error' && (
              <span className="mt-1 text-xs text-red-500">Failed to send</span>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="mb-3 flex items-start">
            <span className="rounded-lg bg-zinc-100 px-3 py-2 text-sm text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
              Agent is typing...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Composer — full size */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 border-t border-zinc-200 px-4 py-3 dark:border-zinc-700"
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about this session..."
          rows={2}
          className="flex-1 resize-none rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-800 placeholder-zinc-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
        />
        <button
          type="submit"
          disabled={draft.trim().length === 0}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
