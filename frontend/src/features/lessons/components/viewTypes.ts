/** Types de vue des composants des leçons : indépendants du contrat d'API (D34). */

/** Type de vue du lecteur de leçon. */
export interface LessonView {
  title: string;
  markdown: string;
  wordCount: number;
  /** Adresse du PDF, ou `null` tant qu'il n'est pas prêt. */
  pdfUrl: string | null;
}

export type ResourceType = "documentation" | "cours" | "video" | "article" | "depot" | "papier";
export type ResourceLevel = "debutant" | "intermediaire" | "avance";
export type ResourceStatus = "to_read" | "read";

export interface ResourceView {
  id: string;
  title: string;
  /** Adresse web (http ou https seulement) ; `null` si l'adresse du serveur n'en est pas une. */
  url: string | null;
  type: ResourceType;
  /** Code de langue (`fr`, `en`…). */
  lang: string | null;
  durationMinutes: number | null;
  level: ResourceLevel | null;
  author: string | null;
  /** Date de publication, telle que la source la donne. */
  date: string | null;
  /** La raison du choix, en une phrase. */
  reason: string;
  /** Fiche de lecture (ressource sans copie locale). */
  note: string | null;
  /** Adresse de la copie locale (PDF), si elle existe. */
  localCopyUrl: string | null;
  status: ResourceStatus;
}

/** Les filtres de la bibliothèque : `null` veut dire « tous ». */
export interface LibraryFilterValue {
  programId: string | null;
  type: ResourceType | null;
  lang: string | null;
  status: ResourceStatus | null;
}

export interface ProgramOption {
  id: string;
  title: string;
}
