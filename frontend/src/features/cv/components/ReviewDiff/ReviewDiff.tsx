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
  /** The refusal of the last decision, shown on the card of the related change. */
  error?: { id: string; message: string } | null;
  /** « Tout accepter »: « à confirmer » changes are still decided one by one. */
  onBulk: (status: DecisionView) => void;
  busy: boolean;
}

function noteText(count: number): string {
  if (count === 0) return "";
  return count === 1 ? t("cv.review.note.one") : t("cv.review.note.many", { count });
}

/** The message under « Tout accepter »: what is still to confirm, then the result after a click. */
function statusText(toConfirm: number, announced: boolean): string {
  const note = noteText(toConfirm);
  if (!announced) return note;
  const done = toConfirm === 0 ? t("cv.review.doneAll") : t("cv.review.done");
  return note ? `${done} ${note}.` : done;
}

/**
 * The changes of a review, grouped by section, with filters (all, to decide, to
 * confirm) and « Tout accepter », which leaves « à confirmer » changes to decide one by one.
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
