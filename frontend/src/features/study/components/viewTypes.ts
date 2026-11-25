/** View types of the study session's components: independent of the API contract (D34). */

export type StudyModeView = "socratic" | "feynman" | "direct";

export type TimerPhase = "work" | "break";

export interface TimerState {
  phase: TimerPhase;
  secondsLeft: number;
  /** Cumulative work time, in seconds: the break never counts. */
  workedSeconds: number;
  running: boolean;
}

export type BlockTaskType = "read" | "watch" | "practice" | "quiz" | "project";

export interface BlockTaskView {
  id: string;
  title: string;
  type: BlockTaskType;
  minutes: number;
}

/** The day's block: the tasks of a module whose lesson is ready. */
export interface BlockView {
  lessonTitle: string;
  moduleTitle: string;
  tasks: BlockTaskView[];
}

export type SkillLevelView = "declared" | "in_progress" | "validated" | "proven";

export interface SkillGainView {
  name: string;
  level: SkillLevelView;
}

/** Summary of a finished session. */
export interface StudySummaryView {
  moduleTitle: string;
  lessonTitle: string;
  /** Recorded worked time, in minutes. */
  minutes: number;
  summary: string;
  /** Titles of the ticked tasks. */
  tasksDone: string[];
  flashcardsCreated: number;
  skills: SkillGainView[];
}

/** An option of a Tutor interruption (`stuck`, `skip`): the label comes from the back end. */
export interface TutorOptionView {
  value: string;
  label: string;
}
