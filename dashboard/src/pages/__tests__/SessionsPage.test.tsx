import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/test-utils';

vi.mock('../../hooks/use-sessions', () => ({
  useSessions: vi.fn(),
}));

import { SessionsPage } from '../SessionsPage';
import { useSessions } from '../../hooks/use-sessions';

const mockUseSessions = vi.mocked(useSessions);

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
      data: [
        { id: 's1', agentCode: 'MECH', taskType: 'validate_stress', status: 'completed', startedAt: new Date().toISOString(), events: [] },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessions>);
    render(<SessionsPage />);
    expect(screen.getByText('validate stress')).toBeInTheDocument();
    expect(screen.getByText('MECH')).toBeInTheDocument();
  });
});
