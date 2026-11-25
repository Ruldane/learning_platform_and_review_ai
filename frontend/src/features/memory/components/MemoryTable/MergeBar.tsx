import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { MemoryItemRow } from "../viewTypes";
import { canMerge } from "./mergeRule";
import { MergeConfirm } from "./MergeConfirm";

interface MergeBarProps {
  items: MemoryItemRow[];
  selected: string[];
  merging: boolean;
  onMerge: (targetId: string, otherIds: string[]) => void;
}

/** « Fusionner » button: inline confirmation, then locked during the call. */
export function MergeBar({ items, selected, merging, onMerge }: MergeBarProps) {
  const [confirming, setConfirming] = useState(false);
  const picked = selected.map((id) => items.find((item) => item.id === id));
  // An item ticked on another page has no known type here: no blind merge.
  const mergeable =
    picked.every((item) => item !== undefined) && canMerge(picked as MemoryItemRow[]);
  const [target, ...others] = selected;
  const confirm = () => {
    setConfirming(false);
    if (target !== undefined) onMerge(target, others);
  };

  return (
    <div className="flex flex-col gap-3">
      {confirming && mergeable && !merging ? (
        <MergeConfirm
          count={selected.length}
          targetTitle={picked[0]?.title ?? ""}
          onConfirm={confirm}
          onCancel={() => setConfirming(false)}
        />
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          disabled={!mergeable || merging}
          onClick={() => setConfirming(true)}
        >
          {t("memory.button.merge")}
        </Button>
        <p className="text-xs text-muted-foreground">{t("memory.table.mergeHint")}</p>
      </div>
    </div>
  );
}
