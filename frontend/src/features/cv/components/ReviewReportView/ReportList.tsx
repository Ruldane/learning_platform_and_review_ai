import { t } from "@/shared/i18n/t";

interface ReportListProps {
  title: string;
  items: string[];
}

/** Une liste du rapport ; sans rien dedans, elle le dit au lieu de disparaître. */
export function ReportList({ title, items }: ReportListProps) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="text-sm font-medium">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("cv.report.none")}</p>
      ) : (
        <ul className="list-disc pl-5 text-sm">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
