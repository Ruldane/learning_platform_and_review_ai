import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { shortDate } from "../formatDate";
import type { DuplicateView } from "../viewTypes";

interface DuplicateItemProps {
  duplicate: DuplicateView;
  onOpen: (postingId: string) => void;
  onDistinct: (postingId: string) => void;
}

function nameOf(duplicate: DuplicateView): string {
  const title = duplicate.title ?? t("gap.duplicate.untitled");
  return duplicate.company ? `${title} (${duplicate.company})` : title;
}

function sentence(duplicate: DuplicateView): string {
  if (duplicate.level === "certain") {
    return t("gap.duplicate.certain", { date: shortDate(duplicate.createdAt) });
  }
  return t(duplicate.level === "probable" ? "gap.duplicate.probable" : "gap.duplicate.possible");
}

/** A duplicate: the sentence for its level, its posting, and for « probable » the two actions. */
export function DuplicateItem({ duplicate, onOpen, onDistinct }: DuplicateItemProps) {
  const nameId = useId();
  return (
    <li
      data-level={duplicate.level}
      className="flex flex-col gap-2 rounded-xl border bg-card p-3 text-sm"
    >
      <p className="font-medium">{sentence(duplicate)}</p>
      <p id={nameId} className="text-muted-foreground">
        {t("gap.duplicate.posting", { title: nameOf(duplicate) })}
      </p>
      {duplicate.level === "probable" ? (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => onOpen(duplicate.postingId)} aria-describedby={nameId}>
            {t("gap.duplicate.open")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDistinct(duplicate.postingId)}
            aria-describedby={nameId}
          >
            {t("gap.duplicate.distinct")}
          </Button>
        </div>
      ) : null}
    </li>
  );
}
