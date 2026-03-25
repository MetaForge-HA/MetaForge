import { Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { ChatSidebar } from '../chat/ChatSidebar';
import { useLayoutStore } from '@/store/layout-store';

export function AppLayout() {
  const { sidebarCollapsed } = useLayoutStore();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <Sidebar />

      {/* Main content — offset by sidebar width with smooth transition */}
      <div
        className={clsx(
          'transition-all duration-200',
          // On mobile there is no persistent sidebar, so no left margin
          'md:ml-14',
          // On desktop, match sidebar width
          !sidebarCollapsed && 'md:ml-56'
        )}
      >
        <Topbar />
        <main className="p-6">
          <Outlet />
        </main>
      </div>

      <ChatSidebar />
    </div>
  );
}
