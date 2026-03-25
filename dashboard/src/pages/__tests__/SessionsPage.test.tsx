import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/test-utils';

vi.mock('../../hooks/use-sessions', () => ({
  useSessions: vi.fn(),
}));

import { SessionsPage } from '../SessionsPage';
import { useSessions } from '../../hooks/use-sessions';

const mockUseSessions = vi.mocked(useSessions);

const COMPLETED_SESSION = {
  id: 's1',
  agentCode: 'MECH',
  taskType: 'validate_stress',
  status: 'completed' as const,
  startedAt: new Date(Date.now() - 10000).toISOString(),
  completedAt: new Date().toISOString(),
  events: [],
};

describe('SessionsPage', () => {
  it('shows loading state', () => {
    mockUseSessions.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    mockUseSessions.mockReturnValue({ data: [], isLoading: false, isError: false, refetch: vi.fn() } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByText('No agent sessions yet')).toBeInTheDocument();
  });

  it('renders session list', () => {
    mockUseSessions.mockReturnValue({
      data: [COMPLETED_SESSION],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByText('validate stress')).toBeInTheDocument();
    expect(screen.getByText('MECH')).toBeInTheDocument();
  });

  it('shows status icon for completed session', () => {
    mockUseSessions.mockReturnValue({
      data: [COMPLETED_SESSION],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    // CheckCircle renders with aria-label="Completed"
    expect(screen.getByLabelText('Completed')).toBeInTheDocument();
  });

  it('shows status icon for failed session', () => {
    mockUseSessions.mockReturnValue({
      data: [{ ...COMPLETED_SESSION, status: 'failed' as const }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByLabelText('Failed')).toBeInTheDocument();
  });

  it('shows status icon for running session', () => {
    mockUseSessions.mockReturnValue({
      data: [{ ...COMPLETED_SESSION, status: 'running' as const, completedAt: undefined }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByLabelText('Running')).toBeInTheDocument();
  });

  it('shows domain badge for known agent code', () => {
    mockUseSessions.mockReturnValue({
      data: [COMPLETED_SESSION],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByText('Mechanical')).toBeInTheDocument();
  });

  it('shows elapsed duration on each row', () => {
    mockUseSessions.mockReturnValue({
      data: [COMPLETED_SESSION],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    // Duration badge should be present (non-empty)
    const durationEl = screen.getByTestId('session-duration');
    expect(durationEl.textContent).not.toBe('');
  });
});
