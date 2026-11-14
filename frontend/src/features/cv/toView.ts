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
 * Les modifications du contrat → les cartes ; un fait dont on ne retrouve plus le texte n'est pas
 * cité. `placed` est la dernière version prête : une modification acceptée que sa composition n'a
 * pas pu placer (`decisions[ref] === "ignored"`) le dit sur sa carte.
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

const ZONES: ZoneView["zone"][] = ["haut", "milieu", "bas", "gauche", "droite"];

/** Les écarts de mise en page d'un modèle (parts d'encre de 0 à 1) ; une zone inconnue est ignorée. */
export function toZoneViews(zones: TemplateOut["zones"]): ZoneView[] {
  return zones.flatMap(({ zone, original, render }): ZoneView[] => {
    const known = ZONES.find((name) => name === zone);
    return known ? [{ zone: known, original, render }] : [];
  });
}

/** La dernière version prête d'une revue : la seule dont les décisions disent ce qui est dans le PDF. */
export function latestReadyVersion(review: CvReviewOut): VersionOut | null {
  return latestVersion({
    ...review,
    versions: review.versions.filter((v) => v.status === "ready"),
  });
}

/** Le nombre de modifications acceptées que la composition n'a pas pu placer dans cette version. */
export const ignoredCount = (version: VersionOut): number =>
  Object.values(version.decisions).filter((decision) => decision === "ignored").length;

/** La version la plus récente d'une revue (numéros croissants), ou `null`. */
export function latestVersion(review: CvReviewOut): VersionOut | null {
  return review.versions.reduce<VersionOut | null>(
    (latest, version) => (latest === null || version.number > latest.number ? version : latest),
    null,
  );
}
