import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

const label = "flex flex-col gap-1 text-sm font-medium";

export function PublicationFields({ title }: { title: string }) {
  return (
    <>
      <label className={label}>
        {t("contributions.publication.author")}
        <input name="author" required maxLength={39} className={fieldClass} />
      </label>
      <label className={label}>
        {t("contributions.publication.head")}
        <input name="head" required maxLength={100} className={fieldClass} />
      </label>
      <label className={label}>
        {t("contributions.publication.title")}
        <input
          name="title"
          required
          maxLength={120}
          defaultValue={title.slice(0, 120)}
          className={fieldClass}
        />
      </label>
      <label className={label}>
        {t("contributions.publication.body")}
        <textarea name="body" required maxLength={1400} rows={5} className={fieldClass} />
      </label>
    </>
  );
}
