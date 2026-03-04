import { formatDistanceToNowStrict } from 'date-fns';

/**
 * Format an ISO-8601 date string as a human-readable relative time.
 *
 * Uses date-fns `formatDistanceToNowStrict` for concise output like
 * "2 minutes ago", "1 hour ago", "3 days ago".
 *
 * Falls back to the raw date string when parsing fails.
 */
export function formatRelativeTime(iso: string): string {
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
      return iso;
    }
    return formatDistanceToNowStrict(date, { addSuffix: true });
  } catch {
    return iso;
  }
}
