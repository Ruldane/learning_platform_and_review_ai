import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { BlockView } from "../viewTypes";
import { BlockTasks } from "./BlockTasks";

interface BlockCardProps {
  /** Le bloc du jour ; `null` quand aucune tâche d'étude n'est à faire. */
  block: BlockView | null;
  /** Une session déjà ouverte : on la reprend au lieu d'en commencer une autre. */
  openSessionId: string | null;
  onStart: () => void;
  onResume: () => void;
  /** Un départ ou une reprise est en route : le bouton ne se déclenche pas deux fois. */
  disabled?: boolean;
}

/**
 * Le bloc du jour : la leçon, son module et les tâches que la session coche. « Commencer mon
 * bloc », ou « Reprendre ma session » quand une session est ouverte (jamais les deux).
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
