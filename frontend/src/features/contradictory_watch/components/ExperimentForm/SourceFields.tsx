import { t } from "@/shared/i18n/t";

export function SourceFields({ source }: { source: "first" | "second" }) {
  return (
    <fieldset className="grid gap-2 rounded border p-3">
      <legend className="font-semibold">{t(`contradictoryWatch.${source}`)}</legend>
      <label className="grid gap-1">
        {t("contradictoryWatch.url")}
        <input
          name={`${source}-url`}
          className="rounded border bg-background p-2"
          type="url"
          required
        />
      </label>
      <label className="grid gap-1">
        {t("contradictoryWatch.version")}
        <input
          name={`${source}-version`}
          className="rounded border bg-background p-2"
          maxLength={140}
          required
        />
      </label>
      <label className="grid gap-1">
        {t("contradictoryWatch.claim")}
        <textarea
          name={`${source}-claim`}
          className="rounded border bg-background p-2"
          maxLength={3000}
          required
        />
      </label>
    </fieldset>
  );
}
