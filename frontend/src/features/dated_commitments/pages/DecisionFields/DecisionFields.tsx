import { t } from "@/shared/i18n/t";
import type { Draft } from "../../api";

type Decision = Pick<Draft, "title" | "version" | "intention">;
type Props = { draft: Decision; onChange: (field: keyof Decision, value: string) => void };

export function DecisionFields({ draft, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1">
        {t("datedCommitments.decision")}
        <input
          required
          maxLength={200}
          value={draft.title}
          onChange={(event) => onChange("title", event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      <label className="flex flex-col gap-1">
        {t("datedCommitments.version")}
        <input
          required
          maxLength={80}
          value={draft.version}
          onChange={(event) => onChange("version", event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      <label className="flex flex-col gap-1">
        {t("datedCommitments.intention")}
        <textarea
          required
          maxLength={1500}
          rows={3}
          value={draft.intention}
          onChange={(event) => onChange("intention", event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
    </div>
  );
}
