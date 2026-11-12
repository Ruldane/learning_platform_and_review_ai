import { useState } from "react";
import { WeekCalendar } from "../../components/WeekCalendar";
import { WeekHeader } from "../../components/WeekHeader";
import type { TaskEdits } from "../../hooks/useTaskMutations";
import type { WeekView } from "../../types";
import { WeekPicker } from "./WeekPicker";

interface WeekPaneProps {
  weeks: WeekView[];
  edits: TaskEdits;
  /** Aujourd'hui, `AAAA-MM-JJ` : la semaine en cours s'ouvre la première. */
  today: string;
}

/** Rang de la semaine qui porte `today`, sinon de la première. */
function initialRank(weeks: WeekView[], today: string): number {
  const current = weeks.find((week) => week.days.some((day) => day.date === today));
  return (current ?? weeks[0])?.rank ?? 1;
}

/** Vue « Semaine » : choix de la semaine, entête (charge face à 85 %) et calendrier déplaçable. */
export function WeekPane({ weeks, edits, today }: WeekPaneProps) {
  const [chosen, setChosen] = useState<number | null>(null);
  const rank = chosen ?? initialRank(weeks, today);
  const week = weeks.find((item) => item.rank === rank) ?? weeks[0];
  if (!week) return null;
  return (
    <div className="flex flex-col gap-4">
      <WeekPicker weeks={weeks} rank={week.rank} onChange={setChosen} />
      <WeekHeader week={week} />
      <WeekCalendar week={week} editable onMoveTask={edits.move} />
    </div>
  );
}
