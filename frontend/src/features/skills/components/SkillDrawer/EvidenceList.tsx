import { t } from "@/shared/i18n/t";
import type { EvidenceView } from "../viewTypes";
import { SmartLink } from "./SmartLink";

const DAY = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });

/** Les preuves d'un niveau : une ligne par preuve, avec un lien quand elle a sa page. */
export function EvidenceList({ evidence }: { evidence: EvidenceView[] }) {
  if (evidence.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("skills.drawer.evidenceEmpty")}</p>;
  }
  return (
    <ul aria-label={t("skills.drawer.evidence")} className="flex flex-col gap-1 text-sm">
      {evidence.map((item) => {
        const text = t("skills.drawer.evidenceAt", {
          label: item.label,
          date: DAY.format(new Date(item.at)),
        });
        return (
          <li key={`${item.kind}:${item.label}:${item.at}`}>
            {item.url ? <SmartLink url={item.url}>{text}</SmartLink> : text}
          </li>
        );
      })}
    </ul>
  );
}
