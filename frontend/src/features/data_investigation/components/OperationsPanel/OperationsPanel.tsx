import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

const options = [
  "latest_revision",
  "delivered_only",
  "declared_identifier",
  "positive_units",
] as const;
type Operation = (typeof options)[number];

interface Step {
  operation: Operation;
  removed_rows: readonly number[];
  remaining_rows: number;
}

interface Props {
  trace: readonly Step[];
  editable: boolean;
  busy: boolean;
  onChange: (operations: Operation[]) => void;
}

export function OperationsPanel({ trace, editable, busy, onChange }: Props) {
  const used = trace.map((entry) => entry.operation);
  return (
    <section className="grid gap-3">
      <h2 className="font-semibold">{t("dataInvestigation.pipeline")}</h2>
      <ol className="list-decimal space-y-2 pl-6">
        {trace.map((entry) => (
          <li key={entry.operation}>
            <p>{t(`dataInvestigation.operations.${entry.operation}`)}</p>
            <p className="text-sm">
              {t("dataInvestigation.removal", {
                count: entry.remaining_rows,
                removed: entry.removed_rows.join(", ") || t("dataInvestigation.noRemoval"),
              })}
            </p>
          </li>
        ))}
      </ol>
      {editable && (
        <div className="flex flex-wrap gap-2">
          {options.map((operation) => (
            <Button
              key={operation}
              type="button"
              variant="outline"
              aria-disabled={busy || used.includes(operation)}
              onClick={() => !busy && !used.includes(operation) && onChange([...used, operation])}
            >
              {t(`dataInvestigation.operations.${operation}`)}
            </Button>
          ))}
          <Button
            type="button"
            variant="outline"
            aria-disabled={busy || used.length === 0}
            onClick={() => !busy && used.length > 0 && onChange(used.slice(0, -1))}
          >
            {t("dataInvestigation.undo")}
          </Button>
        </div>
      )}
    </section>
  );
}
