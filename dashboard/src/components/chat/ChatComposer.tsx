import { useState, useRef, useCallback, type KeyboardEvent } from 'react';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChatComposerProps {
  /** Called when the user submits a message. */
  onSend: (content: string) => void;
  /** Placeholder text for the textarea. */
  placeholder?: string;
  /** Whether the composer is disabled (e.g., while sending). */
  disabled?: boolean;
  /** Compact mode reduces padding and font size. */
  compact?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Chat message composer with a textarea and send button.
 *
 * - `Enter` sends the message.
 * - `Shift+Enter` inserts a newline.
 * - Trims whitespace before sending; empty messages are not sent.
 */
export function ChatComposer({
  onSend,
  placeholder = 'Type a message...',
  disabled = false,
  compact = false,
}: ChatComposerProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed.length === 0 || disabled) return;
    onSend(trimmed);
    setValue('');
    // Reset textarea height after clearing
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  /** Auto-grow the textarea as the user types (up to a max). */
  const handleInput = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const maxHeight = compact ? 80 : 140;
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, [compact]);

  return (
    <div
      className={`flex items-end gap-2 border-t border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900 ${
        compact ? 'px-2 py-1.5' : 'px-3 py-2'
      }`}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          handleInput();
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={`flex-1 resize-none rounded-lg border border-zinc-200 bg-zinc-50 outline-none transition-colors placeholder:text-zinc-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:placeholder:text-zinc-500 dark:focus:border-blue-500 dark:focus:ring-blue-500 ${
          compact ? 'px-2.5 py-1.5 text-sm' : 'px-3 py-2 text-sm'
        }`}
      />

      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || value.trim().length === 0}
        aria-label="Send message"
        className={`flex shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40 ${
          compact ? 'h-8 w-8' : 'h-9 w-9'
        }`}
      >
        {/* Arrow-up / Send icon (inline SVG) */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={compact ? 'h-4 w-4' : 'h-4.5 w-4.5'}
        >
          <path d="m5 12 7-7 7 7" />
          <path d="M12 19V5" />
        </svg>
      </button>
    </div>
  );
}
