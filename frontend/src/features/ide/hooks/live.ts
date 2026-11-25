/** Re-read interval for an open session (notes, files, Claude's runs). */
export const LIVE_MS = 3000;

/**
 * Re-reads every 3 s **while the tab is visible**: TanStack pauses the interval when the
 * page is hidden or loses visibility (`refetchIntervalInBackground` is false) and re-reads on
 * return. A failed re-read keeps the data already there.
 */
export const liveOptions = {
  refetchInterval: LIVE_MS,
  refetchIntervalInBackground: false,
} as const;
