import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface MixBarProps {
  /** Nombre de cartes cochées. */
  picked: number;
  /** Nombre de cartes à cocher pour mélanger. */
  size: number;
  canChoose: boolean;
  canAnotherRound: boolean;
  actionable: boolean;
  onMix: () => void;
  onAnotherRound: () => void;
}

/** Sous les cartes : « Mélanger ces deux parcours » (deux cartes cochées) et « Demander un autre tour ». */
export function MixBar({
  picked,
  size,
  canChoose,
  canAnotherRound,
  actionable,
  onMix,
  onAnotherRound,
}: MixBarProps) {
  return (
    <div
      role="group"
      aria-label={t("learning.proposals.mixGroup")}
      className="flex flex-wrap items-center gap-2"
    >
      <Button disabled={!actionable || picked !== size} onClick={onMix}>
        {t("learning.proposals.mix")}
      </Button>
      {canAnotherRound ? (
        <Button variant="outline" disabled={!actionable} onClick={onAnotherRound}>
          {t("learning.proposals.anotherRound")}
        </Button>
      ) : null}
      <p role="status" className="text-sm text-muted-foreground">
        {canChoose
          ? t("learning.proposals.mixHint", { count: picked })
          : t("learning.proposals.locked")}
      </p>
    </div>
  );
}
