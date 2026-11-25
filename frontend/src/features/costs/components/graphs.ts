import { costs } from "@/shared/i18n/messages/costs";
import { t } from "@/shared/i18n/t";

type GraphKey = keyof typeof costs.graphs;

/** The known graphs, in the order of the backend `GRAPHS` registry. */
export const GRAPH_KEYS = Object.keys(costs.graphs) as GraphKey[];

const isGraph = (key: string): key is GraphKey => Object.hasOwn(costs.graphs, key);

/**
 * The screen where a graph's work can be found. No page opens a session by its
 * id: it leads to the feature's screen (navigation addresses only).
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

/** A graph's label; an unknown graph keeps its raw name, « hors session » if empty. */
export function graphLabel(key: string | null): string {
  if (key === null || key === "") return t("costs.noSession");
  return isGraph(key) ? t(`costs.graphs.${key}`) : key;
}

/** A graph's screen, or `null` if it has none (or if it is unknown). */
export function graphScreen(key: string | null): string | null {
  return key !== null && isGraph(key) ? (GRAPH_SCREENS[key] ?? null) : null;
}
