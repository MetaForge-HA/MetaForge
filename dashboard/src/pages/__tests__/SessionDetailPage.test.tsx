import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '../../test/test-utils';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ id: 'sess-001' }) };
});

vi.mock('../../hooks/use-sessions', () => ({
  useSession: vi.fn(),
}));

vi.mock('../../hooks/use-scoped-chat', () => ({
  useScopedChat: () => ({
    thread: null,
    messages: [],
    isTyping: false,
    sendMessage: vi.fn(),
    createThread: vi.fn(),
    isLoading: false,
    isCreating: false,
    isSending: false,
  }),
}));

import { SessionDetailPage } from '../SessionDetailPage';
import { useSession } from '../../hooks/use-sessions';

const mockUseSession = vi.mocked(useSession);

const SESSION_WITH_EVENTS = {
  id: 'sess-001',
  agentCode: 'MECH',
  taskType: 'validate_stress',
  status: 'completed',
  startedAt: new Date(Date.now() - 5000).toISOString(),
  completedAt: new Date().toISOString(),
  runId: 'run-001',
  events: [
    {
      id: 'e1',
      timestamp: new Date(Date.now() - 5000).toISOString(),
      type: 'task_started',
      agentCode: 'MECH',
      message: 'Started stress validation',
    },
    {
      id: 'e2',
      timestamp: new Date().toISOString(),
      type: 'task_completed',
      agentCode: 'MECH',
      message: 'Completed stress validation\nerror: constraint violated\nwarning: tolerance exceeded',
    },
  ],
};

describe('SessionDetailPage', () => {
  it('shows loading state', () => {
    mockUseSession.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
  });

  it('shows not found', () => {
    mockUseSession.mockReturnValue({ data: undefined, isLoading: false, isError: false, refetch: vi.fn() } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    expect(screen.getByText('Session not found')).toBeInTheDocument();
  });

  it('renders session detail with events', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    expect(screen.getByText('validate stress')).toBeInTheDocument();
    // Event message appears at least once (in stage header button)
    expect(screen.getAllByText('Started stress validation').length).toBeGreaterThanOrEqual(1);
  });

  it('shows total duration badge', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    expect(screen.getByTestId('total-duration')).toBeInTheDocument();
  });

  it('shows log search input when events exist', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    expect(screen.getByTestId('log-search')).toBeInTheDocument();
  });

  it('first stage is expanded by default', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    // First stage header should have aria-expanded="true"
    const firstHeader = screen.getByTestId('stage-header-e1');
    expect(firstHeader).toHaveAttribute('aria-expanded', 'true');
  });

  it('second stage is collapsed by default', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    const secondHeader = screen.getByTestId('stage-header-e2');
    expect(secondHeader).toHaveAttribute('aria-expanded', 'false');
  });

  it('clicking a collapsed stage expands it', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);
    const secondHeader = screen.getByTestId('stage-header-e2');
    fireEvent.click(secondHeader);
    expect(secondHeader).toHaveAttribute('aria-expanded', 'true');
  });

  it('log search filters lines in expanded stage', () => {
    mockUseSession.mockReturnValue({
      data: SESSION_WITH_EVENTS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
    render(<SessionDetailPage />);

    // Expand second stage first
    const secondHeader = screen.getByTestId('stage-header-e2');
    fireEvent.click(secondHeader);

    // Now search for 'error' — should only show the error line
    const searchInput = screen.getByTestId('log-search');
    fireEvent.change(searchInput, { target: { value: 'error' } });

    // The error line should be visible
    expect(screen.getByText('error: constraint violated')).toBeInTheDocument();
    // The warning line should be filtered out
    expect(screen.queryByText('warning: tolerance exceeded')).not.toBeInTheDocument();
  });
});
