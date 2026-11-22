export type ProjectionChoices = {
  role?: string;
  zone?: string;
  hours?: number;
  target: number;
};

export type ScenarioView = {
  id: string;
  title: string;
  weeklyMinutes: number | null;
  targetDate: string | null;
  projectedPercent: number | null;
};

export type ChapterView = {
  id: string;
  link: string;
  title: string;
  minutes: number;
  unlocked: number;
  improved: number;
};

export type ProjectionView = {
  currentPercent: number | null;
  offerCount: number;
  sampleId: string | null;
  programId: string | null;
  targetPercent: number;
  notes: string[];
  scenarios: ScenarioView[];
  chapters: ChapterView[];
};
