import { useCallback, useEffect } from 'react';
import { useChatStore } from '@/store/chat-store';
import { useChatThreads, useChatThread, useSendChatMessage } from '@/hooks/use-chat';
import { ChatPanel } from './ChatPanel';
import { ChatThreadList } from './ChatThreadList';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Persistent right-side chat sidebar.
 *
 * Two views:
 *   1. **Thread list** — shown when no thread is selected.
 *   2. **Thread detail** — shows a `ChatPanel` for the active thread.
 *
 * Controlled by `useChatStore` (`sidebarOpen`, `activeSidebarThreadId`).
 * Includes a backdrop overlay on smaller screens.
 */
export function ChatSidebar() {
  const {
    sidebarOpen,
    activeSidebarThreadId,
    typingThreadIds,
    openSidebar,
    closeSidebar,
  } = useChatStore();

  // ---- Data fetching ----
  const { data: threadsPage } = useChatThreads(undefined, {
    enabled: sidebarOpen,
  });
  const threads = threadsPage?.data ?? [];

  const { data: activeThread } = useChatThread(
    activeSidebarThreadId ?? undefined,
    { enabled: sidebarOpen && !!activeSidebarThreadId },
  );

  const sendMessage = useSendChatMessage();

  // ---- Handlers ----
  const handleSelectThread = useCallback(
    (threadId: string) => {
      openSidebar(threadId);
    },
    [openSidebar],
  );

  const handleBack = useCallback(() => {
    openSidebar(); // clears activeSidebarThreadId
  }, [openSidebar]);

  const handleSend = useCallback(
    (content: string) => {
      if (!activeSidebarThreadId) return;
      sendMessage.mutate({
        threadId: activeSidebarThreadId,
        payload: { content },
      });
    },
    [activeSidebarThreadId, sendMessage],
  );

  // ---- Escape key closes sidebar ----
  useEffect(() => {
    if (!sidebarOpen) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') closeSidebar();
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [sidebarOpen, closeSidebar]);

  // Determine if the agent is typing in the active thread
  const isTypingInActiveThread =
    !!activeSidebarThreadId && typingThreadIds.has(activeSidebarThreadId);

  // ---- Render ----
  return (
    <>
      {/* Backdrop (visible on small screens when sidebar is open) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-[400px] max-w-full flex-col border-l border-zinc-200 bg-white shadow-lg transition-transform duration-200 ease-in-out dark:border-zinc-700 dark:bg-zinc-900 ${
          sidebarOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        aria-label="Chat sidebar"
      >
        {/* ---- Sidebar header ---- */}
        <div className="flex shrink-0 items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-700">
          <div className="flex items-center gap-2">
            {/* Back arrow — only when viewing a thread */}
            {activeSidebarThreadId && (
              <button
                type="button"
                onClick={handleBack}
                className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
                aria-label="Back to thread list"
              >
                {/* Left arrow SVG */}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                >
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>
            )}

            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {activeSidebarThreadId ? 'Thread' : 'Conversations'}
            </h2>
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={closeSidebar}
            className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            aria-label="Close chat sidebar"
          >
            {/* X icon SVG */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        {/* ---- Content area ---- */}
        <div className="flex-1 overflow-hidden">
          {activeSidebarThreadId && activeThread ? (
            <ChatPanel
              thread={activeThread}
              messages={activeThread.messages}
              compact
              isTyping={isTypingInActiveThread}
              typingAgentName="Agent"
              onSendMessage={handleSend}
            />
          ) : (
            <div className="h-full overflow-y-auto">
              <ChatThreadList
                threads={threads}
                onSelectThread={handleSelectThread}
              />
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
