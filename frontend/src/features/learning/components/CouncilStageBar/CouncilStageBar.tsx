import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { CouncilStage } from "../viewTypes";

interface CouncilStageBarProps {
  stage: CouncilStage;
  /** Tour en cours du débat (0 : pas encore commencé). */
  round: number;
  /** Nombre total de tours prévus, tour 1 compris (`1 + debate_rounds`). */
  rounds: number;
}

const STAGES: CouncilStage[] = ["framing", "research", "debate", "proposals", "program"];

/**
 * Les cinq étapes du Conseil, de gauche à droite : cadrage, recherche, débat, propositions,
 * programme. L'étape courante porte `aria-current="step"` ; les étapes passées sont dites
 * « terminée » aux lecteurs d'écran ; pendant le débat, « Tour 2 / 4 » s'affiche à côté.
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
