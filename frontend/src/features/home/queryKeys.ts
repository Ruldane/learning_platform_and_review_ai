/** TanStack Query keys for home: never any brief or feed data. */
export const homeKeys = {
  brief: ["home", "brief"] as const,
  /** The first page of the feed (the only one re-read; older pages are read on demand). */
  activity: ["home", "activity"] as const,
  /** The background re-read of notifications. */
  notices: ["home", "notices"] as const,
} as const;
