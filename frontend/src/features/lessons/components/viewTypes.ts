/** Type de vue du lecteur de leçon : indépendant du contrat d'API (D34). */
export interface LessonView {
  title: string;
  markdown: string;
  wordCount: number;
  /** Adresse du PDF, ou `null` tant qu'il n'est pas prêt. */
  pdfUrl: string | null;
}
