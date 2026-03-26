import { useState } from 'react';
import { useProposals, useDecideProposal } from '../hooks/use-assistant';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { formatRelativeTime } from '../utils/format-time';
import { useScopedChat } from '../hooks/use-scoped-chat';
import { ApprovalChatPanel } from '../components/chat/integrations/ApprovalChatPanel';
import type { Proposal } from '../api/endpoints/assistant';

// ─── Kinetic Console design tokens ──────────────────────────────────────────
const KC = {
  surface:          '#111319',
  surfaceLow:       '#191b22',
  surfaceContainer: '#1e1f26',
  surfaceHigh:      '#282a30',
  surfaceHighest:   '#33343b',
  surfaceLowest:    '#0c0e14',
  onSurface:        '#e2e2eb',
  onSurfaceVariant: '#9a9aaa',
  primary:          '#ffb783',
  primaryContainer: '#e67e22',
  error:            '#ffb4ab',
  success:          '#3dd68c',
  border:           'rgba(65,72,90,0.2)',
  glass:            'rgba(30,31,38,0.85)',
} as const;

// ─── Status dot ─────────────────────────────────────────────────────────────
function StatusDot({ status }: { status: string }) {
  const color =
    status === 'approved' ? KC.success :
    status === 'rejected' ? KC.error :
    KC.onSurfaceVariant;

  return (
    <span
      style={{
        display: 'inline-block',
        width: 6,
        height: 6,
        borderRadius: '50%',
        backgroundColor: color,
        flexShrink: 0,
      }}
    />
  );
}

// ─── Diff panel ─────────────────────────────────────────────────────────────
function DiffPanel({ diff }: { diff: Record<string, unknown> }) {
  const entries = Object.entries(diff);
  if (entries.length === 0) return null;

  return (
    <div
      className="rounded overflow-auto"
      style={{
        backgroundColor: KC.surfaceLowest,
        border: `1px solid ${KC.border}`,
        maxHeight: 160,
      }}
    >
      <div className="font-mono text-xs p-3 space-y-0.5">
        {entries.map(([key, value]) => {
          const raw = typeof value === 'object' ? JSON.stringify(value) : String(value);
          const isAdded   = key.startsWith('+') || key === 'added';
          const isRemoved = key.startsWith('-') || key === 'removed';
          const lineColor = isAdded ? KC.success : isRemoved ? KC.error : KC.onSurfaceVariant;
          const prefix    = isAdded ? '+ ' : isRemoved ? '- ' : '  ';
          return (
            <div key={key} style={{ color: lineColor }}>
              {prefix}{key}: {raw}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── ProposalCard ────────────────────────────────────────────────────────────
function ProposalCard({ proposal }: { proposal: Proposal }) {
  const decide = useDecideProposal();
  const [chatOpen, setChatOpen] = useState(false);
  const isPending = proposal.status === 'pending';

  const chat = useScopedChat({
    scopeKind: 'approval',
    entityId: proposal.change_id,
    defaultAgentCode: proposal.agent_code,
  });

  function handleDecision(decision: 'approve' | 'reject') {
    decide.mutate({
      changeId: proposal.change_id,
      decision,
      reason: decision === 'approve' ? 'Approved via dashboard' : 'Rejected via dashboard',
      reviewer: 'dashboard-user',
    });
  }

  const hasDiff = Object.keys(proposal.diff).length > 0;

  return (
    <div
      className="rounded-lg space-y-3 p-4"
      style={{
        background: KC.glass,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: `1px solid ${KC.border}`,
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
          <StatusDot status={proposal.status} />
          <div className="min-w-0">
            <div
              className="font-medium leading-snug"
              style={{ color: KC.onSurface }}
            >
              {proposal.description}
            </div>
            <div className="mt-1 flex items-center gap-2 flex-wrap">
              <span
                className="font-mono rounded px-1.5 py-0.5"
                style={{
                  fontSize: 10,
                  backgroundColor: KC.surfaceHigh,
                  color: KC.onSurfaceVariant,
                }}
              >
                {proposal.agent_code}
              </span>
              <span
                className="font-mono"
                style={{ fontSize: 11, color: KC.onSurfaceVariant }}
              >
                {formatRelativeTime(proposal.created_at)}
              </span>
            </div>
          </div>
        </div>

        {/* Status label */}
        <span
          className="font-mono shrink-0 rounded px-1.5 py-0.5"
          style={{
            fontSize: 10,
            backgroundColor:
              proposal.status === 'approved' ? 'rgba(61,214,140,0.12)' :
              proposal.status === 'rejected' ? 'rgba(255,180,171,0.12)' :
              KC.surfaceHigh,
            color:
              proposal.status === 'approved' ? KC.success :
              proposal.status === 'rejected' ? KC.error :
              KC.onSurfaceVariant,
          }}
        >
          {proposal.status}
        </span>
      </div>

      {/* Affected work products */}
      {proposal.work_products_affected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {proposal.work_products_affected.map((wp) => (
            <span
              key={wp}
              className="rounded px-1.5 py-0.5 font-mono"
              style={{
                fontSize: 10,
                backgroundColor: KC.surfaceHigh,
                color: KC.onSurfaceVariant,
                border: `1px solid ${KC.border}`,
              }}
            >
              {wp}
            </span>
          ))}
        </div>
      )}

      {/* Diff panel */}
      {hasDiff && <DiffPanel diff={proposal.diff} />}

      {/* Action buttons — pending only */}
      {isPending && (
        <div className="flex items-center gap-2 pt-1">
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleDecision('approve')}
            disabled={decide.isPending}
            className="gap-1.5"
            style={{
              backgroundColor: KC.primaryContainer,
              color: KC.surface,
              border: 'none',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>check_circle</span>
            Approve
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDecision('reject')}
            disabled={decide.isPending}
            className="gap-1.5"
            style={{
              backgroundColor: 'rgba(255,180,171,0.10)',
              color: KC.error,
              border: `1px solid rgba(255,180,171,0.20)`,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>cancel</span>
            Reject
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setChatOpen(!chatOpen)}
            className="gap-1.5 ml-auto"
            style={{
              color: KC.onSurfaceVariant,
              border: `1px solid ${KC.border}`,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>
              {chatOpen ? 'chat_bubble' : 'chat_bubble_outline'}
            </span>
            {chatOpen ? 'Hide' : 'Discuss'}
          </Button>
        </div>
      )}

      {/* Decision metadata */}
      {proposal.decided_at && (
        <div
          className="font-mono"
          style={{ fontSize: 11, color: KC.onSurfaceVariant }}
        >
          Decided {formatRelativeTime(proposal.decided_at)}
          {proposal.reviewer && ` · ${proposal.reviewer}`}
          {proposal.decision_reason && ` — ${proposal.decision_reason}`}
        </div>
      )}

      {/* Inline chat */}
      {chatOpen && (
        <div
          className="mt-1 rounded"
          style={{
            borderTop: `1px solid ${KC.border}`,
            paddingTop: 12,
          }}
        >
          <ApprovalChatPanel
            approvalId={proposal.change_id}
            agentCode={proposal.agent_code}
            thread={chat.thread}
            messages={chat.messages}
            isTyping={chat.isTyping}
            onSendMessage={chat.sendMessage}
            onCreateThread={chat.createThread}
          />
        </div>
      )}
    </div>
  );
}

// ─── ApprovalsPage ───────────────────────────────────────────────────────────
export function ApprovalsPage() {
  const { data, isLoading } = useProposals();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-lg h-24 animate-pulse"
            style={{
              background: KC.glass,
              border: `1px solid ${KC.border}`,
            }}
          />
        ))}
      </div>
    );
  }

  const proposals = data?.proposals ?? [];

  return (
    <div>
      {/* Page header */}
      <div className="mb-5 flex items-start justify-between">
        <div>
          <h1
            className="text-lg font-medium leading-tight"
            style={{ color: KC.onSurface }}
          >
            Approvals
          </h1>
          <span
            className="font-mono"
            style={{ fontSize: 12, color: KC.onSurfaceVariant }}
          >
            Human-in-the-loop review · {proposals.length} proposal{proposals.length !== 1 ? 's' : ''}
          </span>
        </div>
        <span
          className="font-mono"
          style={{ fontSize: 11, color: KC.onSurfaceVariant, paddingTop: 3 }}
        >
          <span className="material-symbols-outlined align-middle" style={{ fontSize: 14 }}>
            how_to_reg
          </span>
        </span>
      </div>

      {/* Content */}
      {proposals.length === 0 ? (
        <EmptyState
          title="No pending proposals"
          description="Agent proposals requiring review will appear here."
          icon={
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 40, color: KC.onSurfaceVariant }}
            >
              inbox
            </span>
          }
        />
      ) : (
        <div className="space-y-3">
          {proposals.map((proposal) => (
            <ProposalCard key={proposal.change_id} proposal={proposal} />
          ))}
        </div>
      )}
    </div>
  );
}
