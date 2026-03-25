import { useState } from 'react';
import { useProposals, useDecideProposal } from '../hooks/use-assistant';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/shared/StatusBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { formatRelativeTime } from '../utils/format-time';
import { useScopedChat } from '../hooks/use-scoped-chat';
import { ApprovalChatPanel } from '../components/chat/integrations/ApprovalChatPanel';
import type { Proposal } from '../api/endpoints/assistant';

function ProposalCard({ proposal }: { proposal: Proposal }) {
  const decide = useDecideProposal();
  const toast = useToast();
  const [chatOpen, setChatOpen] = useState(false);
  const isPending = proposal.status === 'pending';

  const chat = useScopedChat({
    scopeKind: 'approval',
    entityId: proposal.change_id,
    defaultAgentCode: proposal.agent_code,
  });

  function handleDecision(decision: 'approve' | 'reject') {
    decide.mutate(
      {
        changeId: proposal.change_id,
        decision,
        reason: decision === 'approve' ? 'Approved via dashboard' : 'Rejected via dashboard',
        reviewer: 'dashboard-user',
      },
      {
        onSuccess: () => {
          toast.success(decision === 'approve' ? 'Proposal approved.' : 'Proposal rejected.');
        },
        onError: (err) => {
          toast.error((err as Error)?.message ?? 'Failed to process decision.');
        },
      },
    );
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-medium text-zinc-900 dark:text-zinc-100">
            {proposal.description}
          </div>
          <div className="mt-1 text-xs text-zinc-400">
            Agent: <span className="font-medium">{proposal.agent_code}</span>
            {' \u00B7 '}
            Created {formatRelativeTime(proposal.created_at)}
          </div>
        </div>
        <StatusBadge status={proposal.status} />
      </div>

      {proposal.work_products_affected.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {proposal.work_products_affected.map((work_product) => (
            <span
              key={work_product}
              className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
            >
              {work_product}
            </span>
          ))}
        </div>
      )}

      {isPending && (
        <div className="flex gap-2 pt-1">
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleDecision('approve')}
            disabled={decide.isPending}
          >
            Approve
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => handleDecision('reject')}
            disabled={decide.isPending}
          >
            Reject
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setChatOpen(!chatOpen)}
          >
            {chatOpen ? 'Hide Chat' : 'Discuss'}
          </Button>
        </div>
      )}

      {proposal.decided_at && (
        <div className="text-xs text-zinc-400">
          Decided {formatRelativeTime(proposal.decided_at)}
          {proposal.reviewer && ` by ${proposal.reviewer}`}
          {proposal.decision_reason && ` \u2014 ${proposal.decision_reason}`}
        </div>
      )}

      {chatOpen && (
        <div className="mt-2">
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
    </Card>
  );
}

export function ApprovalsPage() {
  const { data, isLoading, isError, refetch } = useProposals();

  if (isLoading) {
    return (
      <div data-testid="loading-skeleton">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Approvals
          </h2>
        </div>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Approvals
          </h2>
        </div>
        <Card className="flex flex-col items-center py-12 text-center">
          <p className="text-base font-medium text-red-600 dark:text-red-400">
            Failed to load proposals
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            There was a problem fetching pending approvals.
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  const proposals = data?.proposals ?? [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Approvals
        </h2>
        <span className="text-sm text-zinc-500">{proposals.length} proposals</span>
      </div>

      {proposals.length === 0 ? (
        <EmptyState
          title="No pending approvals"
          description="Agent proposals requiring review will appear here."
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
