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
  learned_document: "/memoire/documents",
  web_research: "/reglages/recherche/essai",
  learning_council: "/apprendre/conseil",
  program_builder: "/apprendre/programme",
  lesson_factory: "/apprendre/lecons",
  quiz: "/etudier/quiz",
  study_session: "/etudier/session",
  capture: "/etudier/journal",
  gap_analysis: "/carriere/ecarts",
  cv_capture: "/carriere/profil",
  cv_review: "/carriere/cv",
  application_intake: "/candidatures",
  application_kit: "/candidatures",
  interview: "/candidatures/entretien",
  hiring_committee: "/candidatures",
  market_radar: "/carriere/radar",
  daily_brief: "/",
  project_brief: "/competences/portfolio",
  project_review: "/competences/portfolio",
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
