/**
 * View types for the market radar: a reduced copy of `RadarRunOut` (`GET /radar/runs/{id}`,
 * `GET /radar/latest`) with only the fields the components read. The pages (8.14)
 * convert the responses to these shapes.
 */

/** `TrendOut`: a skill in the ranking and its change since the previous sweep. */
export interface SkillTrendView {
  rank: number;
  skill: string;
  /** The share of analysed offers asking for it, between 0 and 1. */
  share: number;
  /** Percentage points gained or lost; `null` without a previous sweep. */
  deltaShare: number | null;
  /** Absent from the previous sweep (never true on the first sweep). */
  isNew: boolean;
}

export interface BlockedDomainView {
  domain: string;
  count: number;
}

/** A sweep's count: what was actually read, blocked and analysed. */
export interface RunSummaryView {
  role: string;
  zone: string;
  readCount: number;
  blockedCount: number;
  analyzed: number;
  /** Pages read that were not offers. */
  notPostings: number;
  /** Offers read but not analysed (extraction failed, or beyond a sweep's 50). */
  notAnalyzed: number;
  blockedDomains: BlockedDomainView[];
  /** Fewer than 30 readable offers: the ranking is indicative. */
  lowSample: boolean;
}

/** `RadarAlertOut`: a skill in high demand and absent from the program. */
export interface RadarAlertView {
  skill: string;
  share: number;
  /** The message written by the server, already in French. */
  message: string;
}

/** `OfferOut`: a read offer, with its match score computed by the code. */
export interface RadarOfferView {
  title: string | null;
  company: string | null;
  url: string;
  score: number;
  level: string;
  remote: string | null;
  salary: string | null;
}

/** The launch form: role and area typed, the empty area leaving the server default. */
export interface RadarRunRequestView {
  role: string;
  zone: string | null;
}
