import { useEffect, useRef } from 'react';
import { type ChatThread, type ChatMessage } from '@/types/chat';
import { ChatMessageBubble } from './ChatMessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { ChatComposer } from './ChatComposer';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChatPanelProps {
  /** The thread being displayed (provides scope / title metadata). */
  thread: ChatThread;
  /** Messages to render inside the panel. */
  messages: ChatMessage[];
  /** Use compact layout with reduced padding / smaller text. */
  compact?: boolean;
  /** Whether an agent is currently typing in this thread. */
  isTyping?: boolean;
  /** Name of the agent that is typing (shown in the indicator). */
  typingAgentName?: string;
  /** Called when the user submits a new message. */
  onSendMessage?: (content: string) => void;
  /** Called when the user clicks a Digital Twin graph-ref badge. */
  onGraphRefClick?: (nodeType: string, nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Primary chat UI composite.
 *
 * Combines a scrollable message list, typing indicator, and composer into
 * a single panel that can be embedded in the sidebar or on a full page.
 */
export function ChatPanel({
  thread,
  messages,
  compact = false,
  isTyping = false,
  typingAgentName = 'Agent',
  onSendMessage,
  onGraphRefClick,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever new messages arrive or typing starts
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages.length, isTyping]);

  return (
    <div className="flex h-full flex-col">
      {/* ---- Header ---- */}
      <div
        className={`shrink-0 border-b border-zinc-200 dark:border-zinc-700 ${
          compact ? 'px-3 py-2' : 'px-4 py-3'
        }`}
      >
        <h3
          className={`font-semibold text-zinc-900 dark:text-zinc-100 ${
            compact ? 'text-sm' : 'text-base'
          }`}
        >
          {thread.title}
        </h3>
        {thread.scope.label && (
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            {thread.scope.label}
          </span>
        )}
      </div>

      {/* ---- Message list ---- */}
      <div
        ref={scrollRef}
        className={`flex-1 overflow-y-auto ${compact ? 'py-2' : 'py-3'}`}
      >
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-zinc-400 dark:text-zinc-500">
              No messages yet. Start the conversation.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessageBubble
            key={msg.id}
            message={msg}
            onGraphRefClick={onGraphRefClick}
          />
        ))}

        {isTyping && (
          <div className="px-4">
            <TypingIndicator agentName={typingAgentName} />
          </div>
        )}
      </div>

      {/* ---- Composer ---- */}
      {onSendMessage && (
        <ChatComposer
          onSend={onSendMessage}
          compact={compact}
          placeholder={`Message #${thread.title}...`}
        />
      )}
    </div>
  );
}
