import type {
  RadarAlertView,
  RadarOfferView,
  RunSummaryView,
  SkillTrendView,
} from "./components/viewTypes";
import type { RadarLatestOut, RadarRunOut, RadarRunSummary } from "./types";

export type RunStatus = RadarRunOut["status"];

/** A sweep as the page reads it: the count, the ranking, the alerts and the offers. */
export interface RunView {
  id: string;
  status: RunStatus;
  trigger: "schedule" | "manual";
  createdAt: string;
  finishedAt: string | null;
  /** The code of a failed sweep (`failed`), never a message. */
  errorCode: string | null;
  summary: RunSummaryView;
  ranking: SkillTrendView[];
  alerts: RadarAlertView[];
  offers: RadarOfferView[];
}

/** A history row. */
export interface HistoryItemView {
  id: string;
  role: string;
  zone: string;
  status: RunStatus;
  trigger: "schedule" | "manual";
  createdAt: string;
  errorCode: string | null;
  readCount: number;
  /** Pages read that were not offers: « offres lues » = `readCount - notPostings`. */
  notPostings: number;
  blockedCount: number;
  analyzed: number;
  lowSample: boolean;
}

/** What `GET /radar/latest` tells the page: the suggested values and the sweeps spotted. */
export interface LatestView {
  defaults: { role: string; zone: string };
  runningId: string | null;
  /** The latest finished sweep (succeeded or failed), already complete: the radar home shows it. */
  latest: RunView | null;
}

export function toRunView(run: RadarRunOut): RunView {
  return {
    id: run.id,
    status: run.status,
    trigger: run.trigger,
    createdAt: run.created_at,
    finishedAt: run.finished_at,
    errorCode: run.error_code,
    summary: {
      role: run.role,
      zone: run.zone,
      readCount: run.read_count,
      blockedCount: run.blocked_count,
      analyzed: run.analyzed,
      notPostings: run.not_postings,
      notAnalyzed: run.not_analyzed,
      blockedDomains: run.blocked_domains.map((entry) => ({
        domain: entry.domain,
        count: entry.count,
      })),
      lowSample: run.low_sample,
    },
    ranking: run.ranking.map((item) => ({
      rank: item.rank,
      skill: item.skill,
      share: item.share,
      deltaShare: item.delta_share,
      isNew: item.new,
    })),
    alerts: run.alerts.map((alert) => ({
      skill: alert.skill,
      share: alert.share,
      message: alert.message,
    })),
    offers: run.offers.map((offer) => ({
      title: offer.title,
      company: offer.company,
      url: offer.url,
      score: offer.score,
      level: offer.level,
      remote: offer.remote,
      salary: offer.salary,
    })),
  };
}

export function toHistoryItem(run: RadarRunSummary): HistoryItemView {
  return {
    id: run.id,
    role: run.role,
    zone: run.zone,
    status: run.status,
    trigger: run.trigger,
    createdAt: run.created_at,
    errorCode: run.error_code,
    readCount: run.read_count,
    notPostings: run.not_postings,
    blockedCount: run.blocked_count,
    analyzed: run.analyzed,
    lowSample: run.low_sample,
  };
}

export function toLatestView(latest: RadarLatestOut): LatestView {
  return {
    defaults: { role: latest.defaults.role, zone: latest.defaults.zone },
    runningId: latest.running?.id ?? null,
    latest: latest.latest ? toRunView(latest.latest) : null,
  };
}
