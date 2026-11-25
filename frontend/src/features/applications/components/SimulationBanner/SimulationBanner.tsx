import { t } from "@/shared/i18n/t";

/** The committee's permanent banner: what it says is not a prediction. */
export function SimulationBanner() {
  return (
    <p role="note" className="w-fit rounded-lg border bg-muted px-3 py-2 text-sm font-medium">
      {t("applications.committeePage.banner")}
    </p>
  );
}
