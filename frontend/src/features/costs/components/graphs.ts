import { costs } from "@/shared/i18n/messages/costs";
import { t } from "@/shared/i18n/t";

type GraphKey = keyof typeof costs.graphs;

/** Les parcours connus, dans l'ordre du registre `GRAPHS` du back. */
export const GRAPH_KEYS = Object.keys(costs.graphs) as GraphKey[];

const isGraph = (key: string): key is GraphKey => Object.hasOwn(costs.graphs, key);

/**
 * L'écran où l'on retrouve le travail d'un parcours. Aucune page n'ouvre une session par son
 * identifiant : on mène à l'écran de la feature (adresses de navigation seulement).
 */
export const GRAPH_SCREENS: Partial<Record<GraphKey, string>> = {
  demo_debate: "/demo",
  learned_document: "/memory/documents",
  web_research: "/settings/search/probe",
  learning_council: "/learn/council",
  program_builder: "/learn/programs",
  lesson_factory: "/learn/lessons",
  quiz: "/study/quiz",
  study_session: "/study/session",
  capture: "/study/journal",
  gap_analysis: "/career/gaps",
  cv_capture: "/career/profile",
  cv_review: "/career/cv",
  application_intake: "/applications",
  application_kit: "/applications",
  interview: "/applications/interview",
  hiring_committee: "/applications",
  market_radar: "/career/radar",
  daily_brief: "/",
  project_brief: "/skills/portfolio",
  project_review: "/skills/portfolio",
  skill_transfer: "/skills/transfer",
  blind_assessment: "/career/blind-assessment",
  recruitment_process: "/career/recruitment-process",
  grade_appeals: "/skills/appeals",
};

/** Le libellé d'un parcours ; un parcours inconnu garde son nom brut, « hors session » si vide. */
export function graphLabel(key: string | null): string {
  if (key === null || key === "") return t("costs.noSession");
  return isGraph(key) ? t(`costs.graphs.${key}`) : key;
}

/** L'écran d'un parcours, ou `null` s'il n'en a pas (ou s'il est inconnu). */
export function graphScreen(key: string | null): string | null {
  return key !== null && isGraph(key) ? (GRAPH_SCREENS[key] ?? null) : null;
}
