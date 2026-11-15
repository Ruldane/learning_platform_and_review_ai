import { t } from "@/shared/i18n/t";

/** Le bandeau permanent du comité : ce qu'il dit n'est pas une prédiction. */
export function SimulationBanner() {
  return (
    <p role="note" className="w-fit rounded-lg border bg-muted px-3 py-2 text-sm font-medium">
      {t("applications.committeePage.banner")}
    </p>
  );
}
