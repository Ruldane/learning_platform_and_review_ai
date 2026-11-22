import { t } from "@/shared/i18n/t";
import type { Commitment } from "../../api";
import { formatDue, formatMeasure, statuses } from "../../format";

export function CommitmentContext({ item }: { item: Commitment }) {
  const quantity = (value: string | number) =>
    t("datedCommitments.quantity", { value: formatMeasure(value), unit: item.unit });
  return (
    <section className="flex flex-col gap-3 rounded border border-border p-4">
      <p>
        {t(statuses[item.status])} · {t("datedCommitments.date", { date: formatDue(item.due_on) })}
      </p>
      <dl className="grid gap-2 sm:grid-cols-[auto_1fr]">
        <dt className="font-semibold">{t("datedCommitments.version")}</dt>
        <dd>{item.version}</dd>
        <dt className="font-semibold">{t("datedCommitments.intention")}</dt>
        <dd className="whitespace-pre-wrap">{item.intention}</dd>
        <dt className="font-semibold">{t("datedCommitments.indicator")}</dt>
        <dd>{item.indicator}</dd>
        <dt className="font-semibold">{t("datedCommitments.target")}</dt>
        <dd>{quantity(item.target)}</dd>
        {item.observed !== null && item.delta !== null && (
          <>
            <dt className="font-semibold">{t("datedCommitments.measure")}</dt>
            <dd>{quantity(item.observed)}</dd>
            <dt className="font-semibold">{t("datedCommitments.delta")}</dt>
            <dd>{quantity(item.delta)}</dd>
          </>
        )}
        {item.note && (
          <>
            <dt className="font-semibold">{t("datedCommitments.note")}</dt>
            <dd className="whitespace-pre-wrap">{item.note}</dd>
          </>
        )}
      </dl>
    </section>
  );
}
