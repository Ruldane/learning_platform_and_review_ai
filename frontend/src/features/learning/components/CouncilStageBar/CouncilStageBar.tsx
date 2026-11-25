import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { CouncilStage } from "../viewTypes";

interface CouncilStageBarProps {
  stage: CouncilStage;
  /** Current debate round (0: not started yet). */
  round: number;
  /** Total number of planned rounds, round 1 included (`1 + debate_rounds`). */
  rounds: number;
}

const STAGES: CouncilStage[] = ["framing", "research", "debate", "proposals", "program"];

/**
 * The five Council stages, left to right: framing, research, debate, proposals,
 * program. The current stage has `aria-current="step"`; past stages are announced
 * « terminée » to screen readers; during the debate, « Tour 2 / 4 » shows beside it.
 */
export function CouncilStageBar({ stage, round, rounds }: CouncilStageBarProps) {
  const current = STAGES.indexOf(stage);
  return (
    <ol
      aria-label={t("learning.stage.label")}
      className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm"
    >
      {STAGES.map((item, index) => (
        <li key={item} className="flex items-center gap-1.5">
          <span
            aria-current={index === current ? "step" : undefined}
            className={cn(
              "rounded-full px-2.5 py-0.5",
              index === current && "bg-primary font-medium text-primary-foreground",
              index < current && "text-foreground",
              index > current && "text-muted-foreground",
            )}
          >
            {t(`learning.stage.${item}`)}
          </span>
          {index < current ? <span className="sr-only">{t("learning.stage.done")}</span> : null}
          {item === "debate" && stage === "debate" && round > 0 ? (
            <span className="text-xs text-muted-foreground">
              {t("learning.stage.round", { round, rounds })}
            </span>
          ) : null}
          {index < STAGES.length - 1 ? (
            <span aria-hidden="true" className="text-muted-foreground">
              ›
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
