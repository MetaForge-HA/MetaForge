import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import type { ChatThread, ChatMessage } from '@/types/chat';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ComponentChatPanelProps {
  /** BOM component / entry ID. */
  componentId: string;
  /** Human-readable component name (shown in the header). */
  componentName: string;
  /** Agent code — defaults to "SC" (Supply Chain). */
  agentCode?: string;
  /** Pre-resolved thread. */
  thread?: ChatThread | null;
  /** Messages for the thread. */
  messages?: ChatMessage[];
  /** Whether the agent is currently typing. */
  isTyping?: boolean;
  /** Send a user message. */
  onSendMessage?: (content: string) => void;
  /** Create a new thread for this BOM entry. */
  onCreateThread?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Compact, collapsible chat panel scoped to a single BOM table row.
 *
 * Scope: `{ kind: 'bom-entry', entityId: componentId }`
 *
 * The parent is responsible for show/hide toggling (e.g. clicking a chat
 * icon in the BOM row). This component simply renders its contents and
 * stays compact so it fits in an inline or popover container.
 */
export function ComponentChatPanel({
  componentId: _componentId,
  componentName,
  agentCode = 'SC',
  thread,
  messages = [],
  isTyping = false,
  onSendMessage,
  onCreateThread,
}: ComponentChatPanelProps) {
  const [draft, setDraft] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

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
      <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-900">
        <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
          No discussion yet for <span className="font-medium">{componentName}</span>.
        </p>
        <button
          type="button"
          onClick={onCreateThread}
          className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
        >
          Start conversation
        </button>
      </div>
    );
  }

  // ----- Thread exists — render compact chat -----
  return (
    <div className="flex flex-col rounded-md border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-zinc-200 px-3 py-1.5 dark:border-zinc-700">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
          {agentCode.slice(0, 2)}
        </span>
        <h4 className="truncate text-xs font-medium text-zinc-700 dark:text-zinc-300">
          Chat about {componentName} with {agentCode}
        </h4>
      </div>

      {/* Message list */}
      <div className="max-h-48 overflow-y-auto px-3 py-2">
        {messages.length === 0 && (
          <p className="text-xs text-zinc-400">No messages yet.</p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-1.5 flex flex-col ${
              msg.actor.kind === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <span className="mb-0.5 text-[10px] text-zinc-400">
              {msg.actor.displayName}
            </span>
            <div
              className={`max-w-[85%] rounded px-2 py-1 text-xs leading-relaxed ${
                msg.actor.kind === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200'
              }`}
            >
              {msg.content}
            </div>
            {msg.status === 'sending' && (
              <span className="mt-0.5 text-[10px] text-zinc-400">Sending...</span>
            )}
            {msg.status === 'error' && (
              <span className="mt-0.5 text-[10px] text-red-500">Failed to send</span>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="mb-1.5 flex items-start">
            <span className="rounded bg-zinc-100 px-2 py-1 text-xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
              {agentCode} is typing...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-1.5 border-t border-zinc-200 px-3 py-1.5 dark:border-zinc-700"
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Ask ${agentCode} about ${componentName}...`}
          rows={1}
          className="flex-1 resize-none rounded border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-800 placeholder-zinc-400 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
        />
        <button
          type="submit"
          disabled={draft.trim().length === 0}
          className="rounded bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
