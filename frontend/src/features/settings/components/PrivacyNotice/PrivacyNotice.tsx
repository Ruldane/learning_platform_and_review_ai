import { t } from "@/shared/i18n/t";

const ROWS = ["prompts", "searches", "rest"] as const;

/**
 * « Ce qui sort de ta machine » (SPEC 17.3) : le tableau des données et de leur destination, puis
 * ce que Tremplin retire ou limite. Elle vient avant la clé d'API : la clé envoie les prompts au
 * fournisseur.
 */
export function PrivacyNotice() {
  return (
    <div className="flex flex-col gap-5">
      <p className="text-muted-foreground">{t("onboarding.privacy.intro")}</p>
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">{t("onboarding.privacy.table")}</caption>
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-medium">
              {t("onboarding.privacy.data")}
            </th>
            <th scope="col" className="py-2 font-medium">
              {t("onboarding.privacy.destination")}
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row} className="border-b border-border align-top">
              <td className="py-2 pr-4">{t(`onboarding.privacy.rows.${row}.data`)}</td>
              <td className="py-2">{t(`onboarding.privacy.rows.${row}.destination`)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <section className="flex flex-col gap-2">
        <h2 className="font-medium">{t("onboarding.privacy.safeguards")}</h2>
        <ul className="list-disc pl-5 text-sm">
          <li>{t("onboarding.privacy.search")}</li>
          <li>{t("onboarding.privacy.contacts")}</li>
          <li>{t("onboarding.privacy.control")}</li>
        </ul>
      </section>
    </div>
  );
}
