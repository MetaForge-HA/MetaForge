import { clsx } from 'clsx';

// Base skeleton block
interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded-md bg-zinc-200 dark:bg-zinc-700',
        className
      )}
    />
  );
}

// Card skeleton: title + 2 lines + badge
export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-800">
      <div className="mb-3 flex items-start justify-between">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="mb-2 h-3 w-full" />
      <Skeleton className="mb-4 h-3 w-3/4" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

// Table skeleton
interface SkeletonTableProps {
  rows?: number;
  cols?: number;
}

export function SkeletonTable({ rows = 5, cols = 4 }: SkeletonTableProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
      {/* Header row */}
      <div className="flex gap-3 border-b border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800/50">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {/* Data rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="flex gap-3 border-b border-zinc-100 px-3 py-2.5 last:border-0 dark:border-zinc-800"
        >
          {Array.from({ length: cols }).map((_, colIdx) => (
            <Skeleton
              key={colIdx}
              className={clsx('h-3 flex-1', colIdx === 0 && 'w-24 flex-none')}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// List skeleton (for sessions, timeline items)
interface SkeletonListProps {
  rows?: number;
}

export function SkeletonList({ rows = 5 }: SkeletonListProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-800"
        >
          <Skeleton className="h-9 w-9 flex-shrink-0 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}
