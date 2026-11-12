import { useState } from "react";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ProgressOverview } from "../../components/ProgressOverview";
import { TaskList } from "../../components/TaskList";
import type { TaskEdits } from "../../hooks/useTaskMutations";
import type { ModuleLessonView, ProgressView, WeekView } from "../../types";
import { ModuleLessons } from "./ModuleLessons";
import { ViewTabs, panelId, tabId, type ProgramViewId } from "./ViewTabs";
import { WeekPane } from "./WeekPane";

interface ProgramViewsProps {
  weeks: WeekView[];
  progress: ProgressView;
  lessons: ModuleLessonView[];
  edits: TaskEdits;
  /** Aujourd'hui, `AAAA-MM-JJ`. */
  today: string;
}

/** Les trois vues du programme : Semaine (calendrier), Liste (tâches et leçons), Avancement. */
export function ProgramViews({ weeks, progress, lessons, edits, today }: ProgramViewsProps) {
  const [view, setView] = useState<ProgramViewId>("week");
  return (
    <div className="flex flex-col gap-4">
      <ViewTabs active={view} onChange={setView} />
      {edits.error ? <InlineError message={edits.error} /> : null}
      <div role="tabpanel" id={panelId(view)} aria-labelledby={tabId(view)} tabIndex={0}>
        {view === "week" && <WeekPane weeks={weeks} edits={edits} today={today} />}
        {view === "list" && (
          <div className="flex flex-col gap-8">
            <TaskList
              weeks={weeks}
              editable
              onToggleDone={edits.toggleDone}
              onDelete={edits.remove}
              onAdd={edits.add}
              addError={edits.addError}
            />
            <ModuleLessons lessons={lessons} />
          </div>
        )}
        {view === "progress" && <ProgressOverview progress={progress} weeks={weeks} />}
      </div>
    </div>
  );
}
