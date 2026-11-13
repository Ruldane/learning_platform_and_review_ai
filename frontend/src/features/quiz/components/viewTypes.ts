/** Types de vue des composants des quiz et des révisions : indépendants du contrat d'API (D34). */

export type QuestionTypeView = "qcm" | "short" | "code" | "explain";

export interface QuestionView {
  id: string;
  rank: number;
  type: QuestionTypeView;
  prompt: string;
  /** Code à lire, rendu tel quel (jamais interprété) ; `null` quand la question n'en a pas. */
  code: string | null;
  /** Choix d'un QCM ; vide pour les autres types. */
  choices: string[];
}

/** Réponse à une question : `choice` pour un QCM, `text` pour les autres types. */
export interface AnswerDraft {
  question_id: string;
  choice: number | null;
  text: string;
}

/** Le résultat d'une question, joint à son énoncé par la page. */
export interface QuestionResultView {
  questionId: string;
  rank: number;
  prompt: string;
  /** 0, 0,5 ou 1 : la grille n'admet rien d'autre. */
  points: number;
  correctAnswer: string;
  explanation: string;
  /** Retour sur la réponse de January ; vide pour un QCM. */
  feedback: string;
}

/** Ce qui suit un échec : révisions ajoutées, nouvel essai, tâches sans place dans le budget. */
export interface FollowupView {
  revisionTasks: string[];
  /** Jour `AAAA-MM-JJ` du nouvel essai, s'il est à venir ; `null` sinon. */
  retryOn: string | null;
  /** Révisions qu'aucune semaine du budget n'a pu accueillir. */
  unplaced: number;
}

export interface AttemptResultView {
  /** Pourcentage entier, 0 à 100. */
  score: number;
  /** Vrai à 80 % : l'acquis passe à `valide`. La décision reste celle du back. */
  passed: boolean;
  results: QuestionResultView[];
  /** `null` quand le quiz est réussi. */
  followup: FollowupView | null;
}

export interface CardView {
  id: string;
  front: string;
  back: string;
  skill: string | null;
}

export type QuizStatusView = "generating" | "ready" | "failed";

/** Une ligne de la liste : un module, son quiz s'il existe, le meilleur score. */
export interface QuizSummaryView {
  moduleId: string;
  moduleTitle: string;
  weekRank: number;
  quizId: string | null;
  status: QuizStatusView | null;
  /** Meilleur score en pourcentage ; `null` tant qu'aucune tentative n'est notée. */
  bestScore: number | null;
  /** Jour `AAAA-MM-JJ` du prochain essai après un échec, s'il est à venir (sinon `null`). */
  retryOn: string | null;
}
