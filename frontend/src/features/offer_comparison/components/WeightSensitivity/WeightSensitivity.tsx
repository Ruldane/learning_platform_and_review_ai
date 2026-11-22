import { t } from "@/shared/i18n/t";
import type { WeightSensitivityView } from "../viewTypes";

export function WeightSensitivity({ data }: { data: WeightSensitivityView[] }) {
  return (
    <section className="grid gap-2">
      <h3 className="font-medium">{t("offerComparison.sensitivity")}</h3>
      <p className="text-sm">{t("offerComparison.sensitivityInfo")} {t("offerComparison.margin")}.</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr>
              <th scope="col" className="border p-2">{t("offerComparison.weights")}</th>
              <th scope="col" className="border p-2">{t("offerComparison.weightDown")}</th>
              <th scope="col" className="border p-2">{t("offerComparison.weightUp")}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => <tr key={row.criterion}>
              <th scope="row" className="border p-2">{row.criterion}</th>
              <td className="border p-2">{row.lower}</td>
              <td className="border p-2">{row.higher}</td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
