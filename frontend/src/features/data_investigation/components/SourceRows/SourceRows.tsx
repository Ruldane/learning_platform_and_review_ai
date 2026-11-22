import { t } from "@/shared/i18n/t";

const columns = ["line", "reference", "revision", "state", "unitsColumn"] as const;

interface Row {
  source_row: number;
  reference: string;
  revision: number;
  status: "delivered" | "pending" | "cancelled";
  units: number;
}

interface Props {
  source: readonly Row[];
  retained: readonly number[];
  digest: string;
}

export function SourceRows({ source, retained, digest }: Props) {
  return (
    <section className="grid gap-2">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="mb-2 text-left font-semibold">{t("dataInvestigation.rows")}</caption>
          <thead>
            <tr className="border-b">
              {columns.map((column) => (
                <th scope="col" className="p-2" key={column}>
                  {t(`dataInvestigation.${column}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {source.map((row) => (
              <tr className="border-b" key={row.source_row}>
                <th scope="row" className="p-2">
                  {row.source_row} ·{" "}
                  {t(
                    retained.includes(row.source_row)
                      ? "dataInvestigation.kept"
                      : "dataInvestigation.removed",
                  )}
                </th>
                <td className="p-2">{row.reference}</td>
                <td className="p-2">{row.revision}</td>
                <td className="p-2">{t(`dataInvestigation.states.${row.status}`)}</td>
                <td className="p-2">{row.units}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="break-all text-sm">
        {t("dataInvestigation.hash")} <code>{digest}</code>
      </p>
    </section>
  );
}
