/** Types de vue des composants de la session d'étude : indépendants du contrat d'API (D34). */

export type StudyModeView = "socratic" | "feynman" | "direct";

export type TimerPhase = "work" | "break";

export interface TimerState {
  phase: TimerPhase;
  secondsLeft: number;
  /** Temps de travail cumulé, en secondes : la pause ne compte jamais. */
  workedSeconds: number;
  running: boolean;
}

export type BlockTaskType = "lire" | "regarder" | "pratiquer" | "quiz" | "projet";

export interface BlockTaskView {
  id: string;
  title: string;
  type: BlockTaskType;
  minutes: number;
}

/** Le bloc du jour : les tâches d'un module dont la leçon est prête. */
export interface BlockView {
  lessonTitle: string;
  moduleTitle: string;
  tasks: BlockTaskView[];
}

export type SkillLevelView = "declare" | "en_cours" | "valide" | "prouve";

export interface SkillGainView {
  name: string;
  level: SkillLevelView;
}

/** Bilan d'une session terminée. */
export interface StudySummaryView {
  moduleTitle: string;
  lessonTitle: string;
  /** Temps travaillé enregistré, en minutes. */
  minutes: number;
  summary: string;
  /** Titres des tâches cochées. */
  tasksDone: string[];
  flashcardsCreated: number;
  skills: SkillGainView[];
}

/** Une option d'une interruption du Tuteur (`stuck`, `skip`) : le libellé vient du back. */
export interface TutorOptionView {
  value: string;
  label: string;
}
