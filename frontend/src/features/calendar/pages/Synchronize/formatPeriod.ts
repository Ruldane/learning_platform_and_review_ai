import { t } from "@/shared/i18n/t";
import type { Proposal } from "../../api";

export function formatPeriod(proposal: Proposal): string {
  const options = { timeZone: proposal.timezone } as const;
  const start = new Intl.DateTimeFormat("fr-FR", {
    ...options,
    dateStyle: "long",
    timeStyle: "short",
  });
  const end = new Intl.DateTimeFormat("fr-FR", { ...options, timeStyle: "short" });
  return t("calendar.period", {
    start: start.format(new Date(proposal.start)),
    end: end.format(new Date(proposal.end)),
    timezone: proposal.timezone,
  });
}
