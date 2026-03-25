import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface LayoutStore {
  /** Whether the sidebar is collapsed to icon-only rail mode. */
  sidebarCollapsed: boolean;
  /** Whether the mobile sidebar overlay is open. */
  mobileSidebarOpen: boolean;
  /** Toggle the sidebar between collapsed and expanded. */
  toggleSidebar: () => void;
  /** Explicitly set the sidebar collapsed state. */
  setSidebarCollapsed: (v: boolean) => void;
  /** Open the mobile sidebar overlay. */
  openMobileSidebar: () => void;
  /** Close the mobile sidebar overlay. */
  closeMobileSidebar: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useLayoutStore = create<LayoutStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      mobileSidebarOpen: false,

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      openMobileSidebar: () => set({ mobileSidebarOpen: true }),

      closeMobileSidebar: () => set({ mobileSidebarOpen: false }),
    }),
    {
      name: 'metaforge-sidebar',
      // Only persist the collapsed state — mobile overlay is ephemeral
      partialize: (state) => ({ sidebarCollapsed: state.sidebarCollapsed }),
    }
  )
);
