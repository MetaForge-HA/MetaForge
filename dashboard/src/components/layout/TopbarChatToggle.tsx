import { useChatStore } from '@/store/chat-store';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Topbar button that toggles the chat sidebar open / closed.
 *
 * Uses a MessageSquare inline SVG icon. Displays a subtle active-state
 * indicator when the sidebar is open.
 */
export function TopbarChatToggle() {
  const { sidebarOpen, openSidebar, closeSidebar } = useChatStore();

  const handleClick = () => {
    if (sidebarOpen) {
      closeSidebar();
    } else {
      openSidebar();
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={sidebarOpen ? 'Close chat' : 'Open chat'}
      aria-pressed={sidebarOpen}
      className={`relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
        sidebarOpen
          ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400'
          : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100'
      }`}
    >
      {/* MessageSquare icon (Lucide-compatible inline SVG) */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>

      {/* Active dot indicator */}
      {sidebarOpen && (
        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-blue-500" />
      )}
    </button>
  );
}
