import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { DecideOptions, DecideResult, DecisionView, ModificationView } from "../viewTypes";
import { FilterBar, matches, type Filter } from "./FilterBar";
import { groupBySection } from "./groupBySection";
import { SectionGroupView } from "./SectionGroupView";

interface ReviewDiffProps {
  mods: ModificationView[];
  onDecide: (id: string, status: DecisionView, opts?: DecideOptions) => DecideResult;
  /** Le refus de la dernière décision, affiché sur la carte de la modification concernée. */
  error?: { id: string; message: string } | null;
  /** « Tout accepter » : les modifications « à confirmer » restent à décider une par une. */
  onBulk: (status: DecisionView) => void;
  busy: boolean;
}

function noteText(count: number): string {
  if (count === 0) return "";
  return count === 1 ? t("cv.review.note.one") : t("cv.review.note.many", { count });
}

/** Le message sous « Tout accepter » : ce qui reste à confirmer, puis, après le clic, le résultat. */
function statusText(toConfirm: number, announced: boolean): string {
  const note = noteText(toConfirm);
  if (!announced) return note;
  const done = toConfirm === 0 ? t("cv.review.doneAll") : t("cv.review.done");
  return note ? `${done} ${note}.` : done;
}

/**
 * Les modifications d'une revue, regroupées par section, avec des filtres (toutes, à décider, à
 * confirmer) et « Tout accepter », qui laisse les modifications « à confirmer » à décider une par une.
 */
export function ReviewDiff({ mods, onDecide, error = null, onBulk, busy }: ReviewDiffProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const [announced, setAnnounced] = useState(false);
  if (mods.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("cv.review.empty")}</p>;
  }
  const toConfirm = mods.filter((mod) => mod.status === "to_confirm").length;
  const acceptable = mods.filter((mod) => mod.status === "proposed").length;
  const groups = groupBySection(mods.filter((mod) => matches(mod, filter)));
  return (
    <section aria-label={t("cv.review.label")} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <FilterBar mods={mods} filter={filter} onChange={setFilter} />
        <Button
          onClick={() => {
            setAnnounced(true);
            onBulk("accepted");
          }}
          disabled={busy || acceptable === 0}
        >
          {t("cv.review.acceptAll")}
        </Button>
      </div>
      <p role="status" className="text-sm text-muted-foreground">
        {statusText(toConfirm, announced)}
      </p>
      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("cv.review.emptyFilter")}</p>
      ) : null}
      {groups.map((group) => (
        <SectionGroupView
          key={group.section}
          group={group}
          busy={busy}
          onDecide={onDecide}
          error={error}
        />
      ))}
    </section>
  );
}
