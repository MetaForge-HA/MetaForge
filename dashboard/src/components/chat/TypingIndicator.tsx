interface TypingIndicatorProps {
  agentName: string;
}

/**
 * Animated typing indicator that shows when an agent is composing a message.
 *
 * Renders three dots with staggered bounce animations alongside the agent name.
 */
export function TypingIndicator({ agentName }: TypingIndicatorProps) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-500">
      <span className="inline-flex items-center gap-0.5" aria-hidden="true">
        <span
          className="inline-block h-1.5 w-1.5 rounded-full bg-zinc-400"
          style={{
            animation: 'metaforge-typing-bounce 1.2s ease-in-out infinite',
            animationDelay: '0ms',
          }}
        />
        <span
          className="inline-block h-1.5 w-1.5 rounded-full bg-zinc-400"
          style={{
            animation: 'metaforge-typing-bounce 1.2s ease-in-out infinite',
            animationDelay: '200ms',
          }}
        />
        <span
          className="inline-block h-1.5 w-1.5 rounded-full bg-zinc-400"
          style={{
            animation: 'metaforge-typing-bounce 1.2s ease-in-out infinite',
            animationDelay: '400ms',
          }}
        />
      </span>
      <span>{agentName} is typing...</span>

      {/* Inline keyframes — scoped to this component via a unique name */}
      <style>{`
        @keyframes metaforge-typing-bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  );
}
