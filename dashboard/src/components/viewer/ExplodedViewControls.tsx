import { useCallback, useEffect } from 'react';
import { clsx } from 'clsx';
import { useViewerStore } from '../../store/viewer-store';
import { Button } from '../ui/Button';

/**
 * Bottom toolbar for controlling the exploded view of a 3D assembly.
 *
 * Features:
 * - Slider to adjust explode factor (0% assembled to 100% fully exploded)
 * - Direction toggle between radial and axial explosion
 * - Reset button to return to assembled state
 * - Keyboard shortcut (E) to toggle explode on/off
 */
export function ExplodedViewControls({ className }: { className?: string }) {
  const explodeFactor = useViewerStore((s) => s.explodeFactor);
  const explodeDirection = useViewerStore((s) => s.explodeDirection);
  const setExplodeFactor = useViewerStore((s) => s.setExplodeFactor);
  const toggleExplodeDirection = useViewerStore((s) => s.toggleExplodeDirection);
  const toggleExplode = useViewerStore((s) => s.toggleExplode);
  const resetExplode = useViewerStore((s) => s.resetExplode);

  // -----------------------------------------------------------------------
  // Keyboard shortcut: E toggles explode
  // -----------------------------------------------------------------------
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore when typing in an input or textarea
      const tag = (event.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (event.key === 'e' || event.key === 'E') {
        event.preventDefault();
        toggleExplode();
      }
    },
    [toggleExplode]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div
      className={clsx(
        'flex items-center gap-4 rounded-lg border border-zinc-200 bg-white px-4 py-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-800',
        className
      )}
      role="toolbar"
      aria-label="Exploded view controls"
    >
      {/* Slider label */}
      <label
        htmlFor="explode-slider"
        className="flex-shrink-0 text-sm font-medium text-zinc-700 dark:text-zinc-300"
      >
        Explode
      </label>

      {/* Explode factor slider */}
      <input
        id="explode-slider"
        type="range"
        min={0}
        max={100}
        step={1}
        value={explodeFactor}
        onChange={(e) => setExplodeFactor(Number(e.target.value))}
        className="h-2 w-40 cursor-pointer appearance-none rounded-full bg-zinc-200 accent-blue-600 dark:bg-zinc-600"
        aria-valuenow={explodeFactor}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Explode factor"
      />

      {/* Percentage display */}
      <span className="w-10 flex-shrink-0 text-right text-sm tabular-nums text-zinc-600 dark:text-zinc-400">
        {Math.round(explodeFactor)}%
      </span>

      {/* Separator */}
      <div className="h-6 w-px bg-zinc-200 dark:bg-zinc-600" />

      {/* Direction toggle */}
      <button
        type="button"
        onClick={toggleExplodeDirection}
        className={clsx(
          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
          'border border-zinc-200 dark:border-zinc-600',
          'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-700'
        )}
        title={`Direction: ${explodeDirection} (click to toggle)`}
        aria-label={`Explode direction: ${explodeDirection}`}
      >
        {explodeDirection === 'radial' ? (
          <>
            <RadialIcon />
            Radial
          </>
        ) : (
          <>
            <AxialIcon />
            Axial
          </>
        )}
      </button>

      {/* Separator */}
      <div className="h-6 w-px bg-zinc-200 dark:bg-zinc-600" />

      {/* Reset button */}
      <Button
        variant="secondary"
        size="sm"
        onClick={resetExplode}
        disabled={explodeFactor === 0}
        aria-label="Reset to assembled state"
      >
        Reset
      </Button>

      {/* Keyboard hint */}
      <kbd className="hidden flex-shrink-0 rounded border border-zinc-300 bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500 sm:inline-block dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-400">
        E
      </kbd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small inline SVG icons for direction toggle
// ---------------------------------------------------------------------------

function RadialIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 1v2M7 11v2M1 7h2M11 7h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function AxialIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path d="M7 1v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M4 3l3-2 3 2M4 11l3 2 3-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
