import { useEffect, useState } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { TopbarChatToggle } from './TopbarChatToggle';
import { ThemeToggle } from './ThemeToggle';
import { RunAgentDialog } from '../shared/RunAgentDialog';

// ---------------------------------------------------------------------------
// Route → page name mapping
// ---------------------------------------------------------------------------

const SEGMENT_LABELS: Record<string, string> = {
  projects:  'Projects',
  sessions:  'Sessions',
  approvals: 'Approvals',
  bom:       'BOM',
  twin:      'Digital Twin',
  assistant: 'Design Assistant',
};

// ---------------------------------------------------------------------------
// Breadcrumb helpers
// ---------------------------------------------------------------------------

interface BreadcrumbSegment {
  label: string;
  /** True for the last (current) segment — rendered without a separator after it. */
  isCurrent: boolean;
}

function useBreadcrumbs(): { segments: BreadcrumbSegment[]; pageTitle: string } {
  const { pathname } = useLocation();
  const params = useParams();

  // Strip leading slash, split, filter empties
  const parts = pathname.replace(/^\//, '').split('/').filter(Boolean);

  const segments: BreadcrumbSegment[] = parts.map((part, idx) => {
    const isLast = idx === parts.length - 1;

    // If it looks like a dynamic ID (UUID or similar), use a shortened form
    const isId = /^[0-9a-f-]{8,}$/i.test(part) || Object.values(params).includes(part);

    let label: string;
    if (isId) {
      label = part.length > 8 ? `${part.slice(0, 8)}…` : part;
    } else {
      label = SEGMENT_LABELS[part] ?? part.charAt(0).toUpperCase() + part.slice(1);
    }

    return { label, isCurrent: isLast };
  });

  // Derive the current page name for <title>
  const topLevelSegment = parts[0] ?? '';
  const pageTitle = SEGMENT_LABELS[topLevelSegment] ?? (topLevelSegment.charAt(0).toUpperCase() + topLevelSegment.slice(1) || 'Dashboard');

  return { segments, pageTitle };
}

// ---------------------------------------------------------------------------
// Topbar
// ---------------------------------------------------------------------------

export function Topbar() {
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const { segments, pageTitle } = useBreadcrumbs();

  // Sync browser tab title
  useEffect(() => {
    document.title = pageTitle ? `${pageTitle} — MetaForge` : 'MetaForge';
  }, [pageTitle]);

  return (
    <>
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-zinc-200 bg-white/80 px-6 backdrop-blur dark:border-zinc-700 dark:bg-zinc-900/80">
        {/* Breadcrumbs */}
        <nav aria-label="Breadcrumb" className="flex items-center">
          {segments.length === 0 ? (
            <h1 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              MetaForge
            </h1>
          ) : (
            <ol className="flex items-center gap-1.5 text-sm">
              {segments.map((seg, idx) => (
                <li key={idx} className="flex items-center gap-1.5">
                  {idx > 0 && (
                    <span className="text-zinc-400 dark:text-zinc-600" aria-hidden="true">
                      /
                    </span>
                  )}
                  <span
                    className={
                      seg.isCurrent
                        ? 'font-semibold text-zinc-900 dark:text-zinc-100'
                        : 'text-zinc-500 dark:text-zinc-400'
                    }
                    aria-current={seg.isCurrent ? 'page' : undefined}
                  >
                    {seg.label}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </nav>

        {/* Right-side actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setRunDialogOpen(true)}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
          >
            Run Agent
          </button>
          <ThemeToggle />
          <TopbarChatToggle />
        </div>
      </header>

      {runDialogOpen && (
        <RunAgentDialog onClose={() => setRunDialogOpen(false)} />
      )}
    </>
  );
}
