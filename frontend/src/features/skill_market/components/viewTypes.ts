export interface QuoteView {
  key: string;
  name: string;
  demand_percent: number;
  change_points: number | null;
  opportunity: boolean;
}

export interface HourView {
  skill: string;
  chapter: string | null;
  lesson_id: string | null;
  remaining_minutes: number | null;
  progress_percent: number | null;
  covered_before: number;
  covered_after: number | null;
}
