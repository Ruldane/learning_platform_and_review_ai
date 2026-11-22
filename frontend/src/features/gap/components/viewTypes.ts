/** Types de vue des composants des offres et de l'écart : indépendants du contrat d'API (D34). */
import type { DuplicateAlertView } from "@/shared/ui/DuplicateAlert";

/** Niveau de maîtrise d'une compétence ; `null` : aucune ligne (absente). */
export type SkillLevelView = "declare" | "en_cours" | "valide" | "prouve";

export type DuplicateLevel = "certain" | "probable" | "possible";

export interface DuplicateView {
  level: DuplicateLevel;
  postingId: string;
  title: string | null;
  company: string | null;
  /** Instant ISO de l'ajout de l'offre déjà connue. */
  createdAt: string;
}

export type GapActionView = "in_program" | "to_add" | "out_of_scope";

/** D'où vient la ligne : l'offre elle-même, ou un mot clé que la revue du CV a renvoyé vers l'écart. */
export type GapSourceView = "posting" | "cv_review";

export interface GapRowView {
  skill: string;
  required: boolean;
  level: SkillLevelView | null;
  action: GapActionView;
  /** Semaine de la première tâche du module, pour `in_program`. */
  week: number | null;
  source: GapSourceView;
}

/**
 * La ligne peut être ajoutée au planning : elle est « À ajouter » et manque vraiment (une
 * compétence déjà validée ou prouvée n'est pas à apprendre).
 */
export function isAddable(row: GapRowView): boolean {
  return row.action === "to_add" && row.level !== "valide" && row.level !== "prouve";
}

export function canPlan(row: GapRowView): boolean {
  return isAddable(row) || row.action === "out_of_scope";
}

export interface MissingSkillView {
  skill: string;
  /** Nombre d'offres où la compétence manque. */
  postings: number;
  /** Parmi elles, nombre d'offres qui l'exigent. */
  requiredIn: number;
}

export interface PostingAnalysisView {
  title: string;
  company: string | null;
  /** `junior`, `confirme`, `senior`, `lead` ou `inconnu` ; toute autre valeur est rendue telle quelle. */
  level: string;
  location: string | null;
  remote: string | null;
  requirements: { text: string; required: boolean }[];
  keywords: string[];
  eliminatory: string[];
  tools: string[];
}

/** Ce que January fournit pour ajouter une offre : un lien ou le texte collé, jamais les deux. */
export type PostingSourceView = { url: string } | { text: string };

/** Une erreur d'envoi : `code` d'API (`posting_unreadable`…) et message déjà en français. */
export interface FormErrorView {
  code: string;
  message: string;
}

/** Nombre maximal de compétences ajoutées au planning en un seul envoi. */
export const MAX_PLAN_SKILLS = 10;

export type PostingStatusView = "analyzing" | "ready" | "rejected" | "failed";

/** Une ligne de la liste des offres. */
export interface PostingListItemView {
  id: string;
  /** `null` tant que l'analyse n'a pas trouvé le titre. */
  title: string | null;
  company: string | null;
  /** Score de match de 0 à 100 ; `null` tant que l'écart n'est pas calculé. */
  score: number | null;
  status: PostingStatusView;
}

/** La candidature qui existe déjà pour une offre. */
export interface ExistingApplicationView {
  id: string;
  company: string;
  title: string;
  status: DuplicateAlertView["status"];
}
