import { useEffect, useRef, useState, useCallback } from 'react';
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
// Helpers
// ---------------------------------------------------------------------------

/** Build a human-readable breadcrumb line from the thread scope. */
function buildBreadcrumb(thread: ChatThread): string {
  const { kind, entityId, label } = thread.scope;
  const display = label ?? entityId;

  switch (kind) {
    case 'session':
      return `Session: ${display}`;
    case 'digital-twin-node':
      return `Node: ${display}`;
    case 'approval':
      return `Approval: ${display}`;
    case 'bom-entry':
      return `Component: ${display}`;
    case 'project':
      return `Project: ${display}`;
    default:
      return display;
  }
}

/** Return a friendly empty-state prompt tailored to the thread's scope. */
function emptyStatePrompt(thread: ChatThread): string {
  switch (thread.scope.kind) {
    case 'session':
      return 'Ask the agent about this session…';
    case 'digital-twin-node':
      return 'Ask about this component…';
    case 'approval':
      return 'Ask about this design change…';
    case 'bom-entry':
      return 'Ask about this part…';
    default:
      return 'Start a conversation…';
  }
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
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  /** Returns true when the scroll container is within 100px of the bottom. */
  const isNearBottom = useCallback((): boolean => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }, []);

  const scrollToBottom = useCallback((smooth: boolean) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
  }, []);

  // Auto-scroll to bottom when new messages arrive, but only if already near bottom.
  // If the user has scrolled up, show the scroll-to-bottom button instead.
  useEffect(() => {
    if (isNearBottom()) {
      scrollToBottom(false);
      setShowScrollBtn(false);
    } else {
      setShowScrollBtn(true);
    }
    // scrollToBottom and isNearBottom are stable callbacks; messages.length / isTyping are the real triggers
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, isTyping]);

  const handleScroll = useCallback(() => {
    setShowScrollBtn(!isNearBottom());
  }, [isNearBottom]);

  return (
    <div className="relative flex h-full flex-col">
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

      {/* ---- Context breadcrumb ---- */}
      <div className="shrink-0 border-b border-zinc-200 px-4 py-1.5 text-xs text-zinc-400 dark:border-zinc-700">
        {buildBreadcrumb(thread)}
      </div>

      {/* ---- Message list ---- */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={`flex-1 overflow-y-auto ${compact ? 'py-2' : 'py-3'}`}
      >
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center px-6">
            <p className="text-center text-sm text-zinc-400 dark:text-zinc-500">
              {emptyStatePrompt(thread)}
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

      {/* ---- Scroll-to-bottom button ---- */}
      {showScrollBtn && (
        <button
          type="button"
          aria-label="Scroll to bottom"
          onClick={() => {
            scrollToBottom(true);
            setShowScrollBtn(false);
          }}
          className="absolute bottom-20 right-4 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-zinc-700 text-white shadow-md transition-opacity hover:bg-zinc-600 dark:bg-zinc-600 dark:hover:bg-zinc-500"
        >
          {/* ChevronDown inline SVG */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      )}

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
