import { formatMinutes } from "@/shared/lib/format";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { BlockView } from "../viewTypes";

interface BlockCardProps {
  /** Today's study block; `null` when nothing is planned. */
  block: BlockView | null;
  onStart: () => void;
  /** The block source was down this morning: no « rien de prévu » shown. */
  unavailable?: boolean;
}

/** Today's block: module, lesson, total duration, tasks, and the study session button. */
export function BlockCard({ block, onStart, unavailable = false }: BlockCardProps) {
  return (
    <section
      aria-labelledby="home-block"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-block" className="text-lg font-medium">
        {t("home.block.title")}
      </h2>
      {unavailable ? (
        <p className="text-muted-foreground">{t("home.unavailable")}</p>
      ) : block === null ? (
        <p className="text-muted-foreground">{t("home.block.empty")}</p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {t("home.block.module", { title: block.moduleTitle })}
          </p>
          <p className="font-medium">{t("home.block.lesson", { title: block.lessonTitle })}</p>
          <p className="text-sm tabular-nums">
            {t("home.block.total", { time: formatMinutes(block.minutes) })}
          </p>
          <ul
            aria-label={t("home.block.tasks")}
            className="flex list-disc flex-col gap-1 pl-5 text-sm"
          >
            {block.tasks.map((task, index) => (
              <li key={`${index}-${task.title}`}>
                {t("home.block.task", { title: task.title, time: formatMinutes(task.minutes) })}
              </li>
            ))}
          </ul>
          <Button className="self-start" onClick={onStart}>
            {t("home.block.start")}
          </Button>
        </>
      )}
    </section>
  );
}
