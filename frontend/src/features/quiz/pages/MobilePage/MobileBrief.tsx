import { t } from "@/shared/i18n/t";
import type { MobileSnapshot } from "../../mobile/data";

export function MobileBrief({ snapshot }: { snapshot: MobileSnapshot }) {
  return (
    <section className="grid gap-2 rounded-lg border p-4">
      <h2 className="font-semibold">{t("mobile.brief")}</h2>
      <p>{t("mobile.date", { day: snapshot.day })}</p>
      {snapshot.lesson ? (
        <p>{snapshot.lesson}{snapshot.minutes === null ? null : " · " + t("mobile.minutes", {
          count: snapshot.minutes,
        })}</p>
      ) : null}
      {snapshot.offers.length ? (
        <ul aria-label={t("mobile.offerList")} className="list-inside list-disc">
          {snapshot.offers.map((offer, index) => <li key={index}>{offer}</li>)}
        </ul>
      ) : null}
    </section>
  );
}
