import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { ModificationCard } from "../ModificationCard";
import type { DecideOptions, DecideResult, DecisionView } from "../viewTypes";
import type { SectionGroup } from "./groupBySection";

interface SectionGroupViewProps {
  group: SectionGroup;
  busy: boolean;
  onDecide: (id: string, status: DecisionView, opts?: DecideOptions) => DecideResult;
  error: { id: string; message: string } | null;
}

/** Les modifications d'une section du CV, sous son titre et leur nombre. */
export function SectionGroupView({ group, busy, onDecide, error }: SectionGroupViewProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId}>
      <h3 id={headingId} className="mb-2 text-base font-semibold">
        {t(`cv.review.section.${group.section}`)} ({group.mods.length})
      </h3>
      <div className="flex flex-col gap-3">
        {group.mods.map((mod) => (
          <ModificationCard
            key={mod.id}
            mod={mod}
            busy={busy}
            error={error?.id === mod.id ? error.message : null}
            onDecide={(status, opts) =>
              opts ? onDecide(mod.id, status, opts) : onDecide(mod.id, status)
            }
          />
        ))}
      </div>
    </section>
  );
}
