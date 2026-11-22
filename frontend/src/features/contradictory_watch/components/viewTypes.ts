export interface SourceDraft {
  url: string;
  version: string;
  claim: string;
}

export interface ExperimentDraft {
  title: string;
  first: SourceDraft;
  second: SourceDraft;
  protocol: string;
  criterion: string;
}

export const outcomes = ["first", "second", "inconclusive"] as const;
export type Outcome = (typeof outcomes)[number];

export interface FrozenWatchView {
  sources: readonly { link: string; version: string; claim: string }[];
  protocol: string;
  criterion: string;
  result: { text: string; verdict: Outcome } | null;
}
