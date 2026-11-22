import { t } from "@/shared/i18n/t";

export interface EditValues {
  headline: string;
  about: string;
  skills: string;
}

export function DraftFields({ values, onChange }: {
  values: EditValues;
  onChange: (field: keyof EditValues, value: string) => void;
}) {
  const style = "w-full rounded-md border bg-background p-2";
  return (
    <>
      <label className="grid gap-1">
        <span>{t("linkedInDrafts.headline")}</span>
        <input value={values.headline} required className={style} maxLength={220}
          onChange={(event) => onChange("headline", event.target.value)} />
      </label>
      <label className="grid gap-1">
        <span>{t("linkedInDrafts.about")}</span>
        <textarea value={values.about} required className={style} maxLength={2600} rows={8}
          onChange={(event) => onChange("about", event.target.value)} />
      </label>
      <label className="grid gap-1">
        <span>{t("linkedInDrafts.skills")}</span>
        <textarea value={values.skills} className={style} rows={5}
          onChange={(event) => onChange("skills", event.target.value)} />
      </label>
    </>
  );
}
