import { useId, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Week } from "../../api";
import { formatDay } from "../../dates";
import { WeekCapacity } from "../WeekCapacity";
import { WeekDetails } from "../WeekDetails";
import { useApplyWeek } from "./useApplyWeek";

const statuses = {
  pending: "interprogramPlanning.pendingProposal",
  blocked: "interprogramPlanning.blockedProposal",
  accepted: "interprogramPlanning.acceptedProposal",
} as const;

export function ProposalCard({ week }: { week: Week }) {
  const headingId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const apply = useApplyWeek(week.id, () => heading.current?.focus());
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded border border-border p-4"
    >
      <h3 ref={heading} id={headingId} tabIndex={-1} className="font-semibold">
        {t("interprogramPlanning.week", { date: formatDay(week.week_start) })}
      </h3>
      <p>
        {t(statuses[week.status])} ·{" "}
        {t("interprogramPlanning.usage", { planned: week.planned_minutes, cap: week.cap_minutes })}
      </p>
      <WeekCapacity days={week.days} />
      <WeekDetails week={week} />
      {apply.isError && <p role="alert">{errorMessage(apply.error)}</p>}
      {week.status === "pending" && (
        <Button
          type="button"
          className="self-start"
          aria-disabled={apply.isPending}
          onClick={() => {
            if (!apply.isPending) apply.mutate();
          }}
        >
          {t("interprogramPlanning.apply")}
        </Button>
      )}
    </section>
  );
}
