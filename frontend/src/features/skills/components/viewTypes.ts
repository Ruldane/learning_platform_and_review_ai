/** Types de vue des composants de la carte de compétences : indépendants du contrat d'API (D34). */

/** Niveau de maîtrise d'une compétence ; `null` : aucune ligne `user_skills` (absente). */
export type LevelView = "declare" | "en_cours" | "valide" | "prouve" | null;

export interface SkillNodeView {
  id: string;
  name: string;
  domain: string;
  level: LevelView;
  /**
   * Demande du marché, de 0 à 1 ; `null` tant que l'analyse du marché n'a pas eu lieu (phase 8) :
   * le nœud garde alors une taille moyenne.
   */
  demand: number | null;
  evidenceCount: number;
}

/** Un lien de prérequis : `beforeId` s'apprend avant `afterId`. */
export interface SkillEdgeView {
  beforeId: string;
  afterId: string;
}

/** Score d'un domaine, de 0 à 100. */
export interface DomainScoreView {
  domain: string;
  score: number;
}

/** Nombre de compétences à chaque niveau (clés du niveau, sans « absent »). */
export type LevelCounts = Record<Exclude<LevelView, null>, number>;

/** Un relevé hebdomadaire. */
export interface HistoryPointView {
  /** Lundi de la semaine, `AAAA-MM-JJ`. */
  weekStart: string;
  counts: LevelCounts;
  /** 0 à 100. */
  score: number;
}

export interface EvidenceView {
  /** Nature de la preuve : `lesson`, `quiz`, `study`, `program`, `capture`… */
  kind: string;
  label: string;
  /** Date ISO de la preuve. */
  at: string;
  /** Chemin dans l'application ; `null` quand la preuve n'a pas de page. */
  url: string | null;
}

/** Offre qui exige la compétence (phase 6) ; la liste est vide d'ici là. */
export interface PostingRefView {
  id: string;
  title: string;
  url: string | null;
}

export interface NextActionView {
  kind: "study" | "quiz" | "review" | "project";
  label: string;
  /** `null` quand l'action n'est pas encore disponible (projet preuve, phase 8). */
  url: string | null;
}

export interface SkillDetailView {
  id: string;
  name: string;
  domain: string;
  synonyms: string[];
  level: LevelView;
  evidence: EvidenceView[];
  postings: PostingRefView[];
  nextAction: NextActionView | null;
}

export interface CompareRowView {
  skillId: string;
  name: string;
  domain: string;
  /** Mon niveau ; `null` : absente. */
  mine: LevelView;
  /** Niveau attendu par la cible. */
  target: Exclude<LevelView, null>;
  /** Écart de rang entre la cible et moi (absente = −1) ; 0 ou moins : atteint. */
  gap: number;
}

export type SkillViewId = "graph" | "radar" | "progress" | "compare";
