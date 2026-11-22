import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

const scenarios = ["latency", "queue", "quota", "fidelity"] as const;

interface OncallStartProps {
  busy: boolean;
  onStart: (scenario: (typeof scenarios)[number] | null) => void;
}

export function OncallStart({ busy, onStart }: OncallStartProps) {
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (busy) return;
        const selected = new FormData(event.currentTarget).get("scenario");
        onStart(scenarios.find((scenario) => scenario === selected) ?? null);
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        {t("oncall.scenario")}
        <select name="scenario" className="rounded-md border border-[var(--border)] bg-card p-2">
          <option value="">{t("oncall.random")}</option>
          {scenarios.map((kind) => (
            <option key={kind} value={kind}>
              {t(`oncall.kind.${kind}`)}
            </option>
          ))}
        </select>
      </label>
      <Button type="submit" aria-disabled={busy}>
        {t("oncall.start")}
      </Button>
    </form>
  );
}
