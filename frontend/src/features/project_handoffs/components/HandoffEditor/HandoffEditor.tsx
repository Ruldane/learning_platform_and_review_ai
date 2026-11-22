import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

const fields = [
  { key: "commands", maxLength: 1500 },
  { key: "limitations", maxLength: 4000 },
  { key: "steps", maxLength: 4000 },
] as const;

type Field = (typeof fields)[number]["key"];

export function HandoffEditor({ draft, busy, onEdit, onPreview }: {
  draft: Record<Field, string>;
  busy: boolean;
  onEdit: (field: Field, value: string) => void;
  onPreview: () => void;
}) {
  const filled = fields.every(({ key }) => draft[key].trim());
  return (
    <form className="grid gap-3" onSubmit={(event) => {
      event.preventDefault();
      if (filled && !busy) onPreview();
    }}>
      {fields.map(({ key, maxLength }) => (
        <label className="grid gap-1" key={key}>
          {t(`projectHandoffs.${key}`)}
          <textarea className="rounded border bg-background p-2" value={draft[key]}
            rows={3} required maxLength={maxLength} disabled={busy}
            onChange={(event) => onEdit(key, event.target.value)} />
        </label>
      ))}
      <Button type="submit" className="w-fit" disabled={busy || !filled}>
        {t("projectHandoffs.preview")}
      </Button>
    </form>
  );
}
