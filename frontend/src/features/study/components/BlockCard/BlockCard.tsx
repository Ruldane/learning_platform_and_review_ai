import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { BlockView } from "../viewTypes";
import { BlockTasks } from "./BlockTasks";

interface BlockCardProps {
  /** The day's block; `null` when no study task is to do. */
  block: BlockView | null;
  /** A session already open: resume it instead of starting another. */
  openSessionId: string | null;
  onStart: () => void;
  onResume: () => void;
  /** A start or a resume is under way: the button cannot fire twice. */
  disabled?: boolean;
}

/**
 * The day's block: the lesson, its module and the tasks the session ticks. « Commencer mon
 * bloc », or « Reprendre ma session » when a session is open (never both).
 */
export function BlockCard({
  block,
  openSessionId,
  onStart,
  onResume,
  disabled = false,
}: BlockCardProps) {
  if (block === null && openSessionId === null) {
    return (
      <EmptyState
        title={t("study.block.emptyTitle")}
        description={t("study.block.emptyDescription")}
      />
    );
  }
  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {t("study.block.title")}
      </p>
      {block ? (
        <>
          <div>
            <h2 className="text-lg font-semibold">{block.lessonTitle}</h2>
            <p className="text-sm text-muted-foreground">
              {t("study.block.module", { module: block.moduleTitle })}
            </p>
          </div>
          <BlockTasks tasks={block.tasks} />
        </>
      ) : null}
      {openSessionId !== null ? (
        <>
          <p className="text-sm text-muted-foreground">{t("study.block.open")}</p>
          <Button className="self-start" disabled={disabled} onClick={onResume}>
            {t("study.block.resume")}
          </Button>
        </>
      ) : (
        <Button className="self-start" disabled={disabled} onClick={onStart}>
          {t("study.block.start")}
        </Button>
      )}
    </section>
  );
}
