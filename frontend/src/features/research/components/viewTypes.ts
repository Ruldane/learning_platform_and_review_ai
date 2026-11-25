/** Display types for the feature's components (see `settings/components/viewTypes.ts`). */

/** What the user submits for a Scout test. */
export interface ResearchBenchInput {
  query: string;
  /** http(s) addresses to read in addition to the search (5 at most). */
  urls: string[];
}
