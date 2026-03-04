import { type ChatMessage, type ChatGraphRef } from '@/types/chat';
import { formatRelativeTime } from '@/utils/format-time';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChatMessageBubbleProps {
  message: ChatMessage;
  /** Called when the user clicks a Digital Twin graph reference badge. */
  onGraphRefClick?: (nodeType: string, nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Simple markdown rendering
// ---------------------------------------------------------------------------

/**
 * Minimal markdown-to-JSX renderer.
 *
 * Handles the subset of markdown that appears in chat messages:
 * - **bold**
 * - *italic* / _italic_
 * - `inline code`
 * - Fenced code blocks (``` ... ```)
 *
 * This intentionally avoids a full markdown library to keep the bundle small.
 */
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let codeBlockLines: string[] | null = null;
  let codeKey = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!;

    // Fenced code block toggle
    if (line.startsWith('```')) {
      if (codeBlockLines !== null) {
        // Closing fence
        nodes.push(
          <pre
            key={`code-${codeKey++}`}
            className="my-1 overflow-x-auto rounded bg-zinc-800 px-3 py-2 text-xs text-zinc-100"
          >
            <code>{codeBlockLines.join('\n')}</code>
          </pre>,
        );
        codeBlockLines = null;
      } else {
        // Opening fence
        codeBlockLines = [];
      }
      continue;
    }

    if (codeBlockLines !== null) {
      codeBlockLines.push(line);
      continue;
    }

    // Inline formatting
    nodes.push(
      <span key={`line-${i}`}>
        {i > 0 && <br />}
        {renderInlineMarkdown(line)}
      </span>,
    );
  }

  // Unclosed code block — render whatever was collected
  if (codeBlockLines !== null && codeBlockLines.length > 0) {
    nodes.push(
      <pre
        key={`code-${codeKey}`}
        className="my-1 overflow-x-auto rounded bg-zinc-800 px-3 py-2 text-xs text-zinc-100"
      >
        <code>{codeBlockLines.join('\n')}</code>
      </pre>,
    );
  }

  return nodes;
}

/**
 * Replace inline markdown tokens with styled spans.
 *
 * Handles: **bold**, *italic*, _italic_, `code`
 */
function renderInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Regex handles: **bold**, *italic*, _italic_, `code`
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|_(.+?)_|`(.+?)`)/g;
  let lastIndex = 0;
  let key = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      // **bold**
      parts.push(<strong key={key++}>{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      // *italic*
      parts.push(<em key={key++}>{match[3]}</em>);
    } else if (match[4] !== undefined) {
      // _italic_
      parts.push(<em key={key++}>{match[4]}</em>);
    } else if (match[5] !== undefined) {
      // `code`
      parts.push(
        <code
          key={key++}
          className="rounded bg-zinc-200 px-1 py-0.5 text-xs dark:bg-zinc-700"
        >
          {match[5]}
        </code>,
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Trailing text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Circular avatar showing a user initial or agent code. */
function ActorAvatar({
  label,
  variant,
}: {
  label: string;
  variant: 'user' | 'agent';
}) {
  const bg =
    variant === 'user'
      ? 'bg-blue-600 text-white'
      : 'bg-emerald-600 text-white';

  return (
    <span
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${bg}`}
    >
      {label}
    </span>
  );
}

/** Clickable badge for a Digital Twin graph reference. */
function GraphRefBadge({
  graphRef,
  onClick,
}: {
  graphRef: ChatGraphRef;
  onClick?: (nodeType: string, nodeId: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick?.(graphRef.nodeType, graphRef.nodeId)}
      className="mt-1 inline-flex items-center gap-1 rounded-full border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 16 16"
        fill="currentColor"
        className="h-3 w-3"
      >
        <path d="M8 1a2.5 2.5 0 0 0-1 4.8V7H5a2 2 0 0 0-2 2v.7A2.5 2.5 0 1 0 5 12.3V9h6v3.3a2.5 2.5 0 1 0 2-2.6V9a2 2 0 0 0-2-2H9V5.8A2.5 2.5 0 0 0 8 1Z" />
      </svg>
      <span>{graphRef.label}</span>
      <span className="text-blue-400">({graphRef.nodeType})</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * Chat message bubble with layout that varies by actor kind.
 *
 * - **user**: right-aligned, primary background, user initial avatar
 * - **agent**: left-aligned, muted background, agent code badge
 * - **system**: center-aligned, muted/50 background, italic text
 */
export function ChatMessageBubble({
  message,
  onGraphRefClick,
}: ChatMessageBubbleProps) {
  const { actor, content, createdAt, graphRef, status } = message;

  // --- System messages ---
  if (actor.kind === 'system') {
    return (
      <div className="flex justify-center px-4 py-1">
        <div className="max-w-md rounded-lg bg-zinc-100/50 px-4 py-2 text-center text-sm italic text-zinc-500 dark:bg-zinc-800/50 dark:text-zinc-400">
          {renderMarkdown(content)}
          <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
            {formatRelativeTime(createdAt)}
          </div>
        </div>
      </div>
    );
  }

  const isUser = actor.kind === 'user';

  // Derive avatar label: first initial for users, agent code for agents
  const avatarLabel = isUser
    ? actor.displayName.charAt(0).toUpperCase()
    : actor.agentCode ?? actor.displayName.slice(0, 2).toUpperCase();

  return (
    <div
      className={`flex gap-2 px-4 py-1.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <ActorAvatar
        label={avatarLabel}
        variant={isUser ? 'user' : 'agent'}
      />

      {/* Bubble */}
      <div
        className={`flex max-w-[75%] flex-col ${isUser ? 'items-end' : 'items-start'}`}
      >
        {/* Sender name */}
        <span className="mb-0.5 text-xs font-medium text-zinc-500 dark:text-zinc-400">
          {actor.displayName}
        </span>

        <div
          className={`rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
            isUser
              ? 'rounded-br-md bg-blue-600 text-white'
              : 'rounded-bl-md bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
          }`}
        >
          {renderMarkdown(content)}

          {/* Graph reference badge */}
          {graphRef && (
            <div className={`mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
              <GraphRefBadge
                graphRef={graphRef}
                onClick={onGraphRefClick}
              />
            </div>
          )}
        </div>

        {/* Footer: timestamp + status */}
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500">
          <span>{formatRelativeTime(createdAt)}</span>
          {status === 'sending' && <span>Sending...</span>}
          {status === 'error' && (
            <span className="text-red-500">Failed to send</span>
          )}
        </div>
      </div>
    </div>
  );
}
