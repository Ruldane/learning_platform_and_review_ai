import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  title: string;
  critique: string;
  onTitle: (value: string) => void;
  onCritique: (value: string) => void;
  onSave: () => void;
  busy: boolean;
}

export function SaveScenarioForm({ title, critique, onTitle, onCritique, onSave, busy }: Props) {
  return (
    <form className="flex flex-col gap-3" onSubmit={(event) => { event.preventDefault(); onSave(); }}>
      <h2 className="text-lg font-semibold">{t("decisionLab.saveArea")}</h2>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("decisionLab.name")}</span>
        <input
          className="min-w-0 rounded-md border border-input bg-background p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          required
          maxLength={120}
          value={title}
          onChange={(event) => onTitle(event.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("decisionLab.critique")}</span>
        <textarea
          className="min-h-24 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-ring"
          value={critique}
          maxLength={2000}
          onChange={(event) => onCritique(event.target.value)}
        />
      </label>
      <Button type="submit" disabled={busy || !title.trim()} className="self-start">
        {t("decisionLab.save")}
      </Button>
    </form>
  );
}
