import type {
  AtsCheckView,
  FactRefView,
  IndicatorsView,
  ModificationView,
  ProfileVersionView,
  ReportView,
  VersionView,
  ZoneView,
} from "./components/viewTypes";
import type {
  CvReviewOut,
  IndicatorsOut,
  ModificationOut,
  ProfileVersionOut,
  ReviewReport,
  TemplateOut,
  VersionOut,
} from "./types";

export function toProfileVersionViews(versions: ProfileVersionOut[]): ProfileVersionView[] {
  return versions.map((version) => ({
    version: version.version,
    status: version.status,
    source: version.source,
    createdAt: version.created_at,
  }));
}

/**
 * Contract changes → the cards; a fact whose text is no longer found is not
 * cited. `placed` is the latest ready version: an accepted change its composition could not
 * place (`decisions[ref] === "ignored"`) says so on its card.
 */
export function toModificationViews(
  mods: ModificationOut[],
  labels: Map<string, string>,
  placed: VersionOut | null = null,
): ModificationView[] {
  return mods.map((mod) => ({
    ignoredIn:
      placed !== null && mod.status === "accepted" && placed.decisions[mod.ref] === "ignored"
        ? placed.number
        : null,
    id: mod.id,
    ref: mod.ref,
    section: mod.section,
    action: mod.action,
    type: mod.type,
    before: mod.before,
    after: mod.after,
    reason: mod.reason,
    status: mod.status,
    blocks: mod.blocks,
    author: mod.author,
    facts: mod.fact_ids.flatMap((id): FactRefView[] => {
      const label = labels.get(id);
      return label === undefined ? [] : [{ id, label }];
    }),
  }));
}

export function toIndicatorsView(indicators: IndicatorsOut): IndicatorsView {
  return {
    coveragePercent: indicators.coverage_percent,
    covered: indicators.covered,
    total: indicators.total,
    missing: indicators.missing,
    checks: indicators.checks.map(({ id, passed, detail }): AtsCheckView => ({
      id,
      passed,
      detail,
    })),
  };
}

export function toVersionView(version: VersionOut): VersionView {
  return {
    id: version.id,
    number: version.number,
    status: version.status,
    pageCount: version.page_count,
    originalPageCount: version.original_page_count,
    filename: version.filename,
    createdAt: version.created_at,
    failureReason: version.failure_reason,
  };
}

export function toReportView(report: ReviewReport): ReportView {
  return {
    ats: report.ats ?? null,
    atsNotes: report.ats_notes ?? [],
    companySummary: report.company_summary ?? null,
    strengths: report.strengths ?? [],
    risks: report.risks ?? [],
    eliminatory: report.eliminatory ?? [],
  };
}

const ZONES: ZoneView["zone"][] = ["top", "middle", "bottom", "left", "right"];

/** Read known CV region codes and their ink coverage. */
export function toZoneViews(zones: TemplateOut["zones"]): ZoneView[] {
  return zones.flatMap(({ zone, original, render }): ZoneView[] => {
    const known = ZONES.find((name) => name === zone);
    return known ? [{ zone: known, original, render }] : [];
  });
}

/** The latest ready version of a review: the only one whose decisions say what is in the PDF. */
export function latestReadyVersion(review: CvReviewOut): VersionOut | null {
  return latestVersion({
    ...review,
    versions: review.versions.filter((v) => v.status === "ready"),
  });
}

/** The number of accepted changes the composition could not place in this version. */
export const ignoredCount = (version: VersionOut): number =>
  Object.values(version.decisions).filter((decision) => decision === "ignored").length;

/** The newest version of a review (increasing numbers), or `null`. */
export function latestVersion(review: CvReviewOut): VersionOut | null {
  return review.versions.reduce<VersionOut | null>(
    (latest, version) => (latest === null || version.number > latest.number ? version : latest),
    null,
  );
}
