import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import type { ChatThread, ChatMessage } from '@/types/chat';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ApprovalChatPanelProps {
  /** The approval ID this chat is scoped to. */
  approvalId: string;
  /** Agent code that proposed the change (e.g. 'ME', 'EE'). */
  agentCode?: string;
  /** Pre-resolved thread (pass from parent or `useScopedChat`). */
  thread?: ChatThread | null;
  /** Messages for the thread. */
  messages?: ChatMessage[];
  /** Whether the agent is currently typing. */
  isTyping?: boolean;
  /** Send a user message. */
  onSendMessage?: (content: string) => void;
  /** Create a new thread for this approval. */
  onCreateThread?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Compact chat panel rendered inline below the diff viewer inside an
 * expanded approval card.
 *
 * Scope: `{ kind: 'approval', entityId: approvalId }`
 */
export function ApprovalChatPanel({
  approvalId: _approvalId,
  agentCode,
  thread,
  messages = [],
  isTyping = false,
  onSendMessage,
  onCreateThread,
}: ApprovalChatPanelProps) {
  const [draft, setDraft] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message.
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

  const agentLabel = agentCode ?? 'Agent';

  // ----- No thread yet — show CTA -----
  if (!thread) {
    return (
      <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-900">
        <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
          No discussion yet for this approval.
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
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
          {agentLabel.slice(0, 2)}
        </span>
        <h4 className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
          Discussion with {agentLabel}
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
              {agentLabel} is typing...
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
          placeholder="Ask about this change..."
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
