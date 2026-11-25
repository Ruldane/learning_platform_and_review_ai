import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Evidence } from "../../api";
import { sourceLabels } from "../../labels";

export function EvidenceCard({ value }: { value: Evidence }) {
  const { kind, resource_id } = value.reference;
  const path = kind === "quiz" ? "/study/quiz/" : "/skills/portfolio/";
  const recorded = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(
    new Date(value.recorded_at),
  );
  return (
    <div className="flex flex-col gap-1 border-l border-border pl-3 break-words">
      <p className="font-medium">
        {t("errorAtlas.evidenceLabel", { kind: t(sourceLabels[kind]), title: value.title })}
      </p>
      <p className="text-sm">{recorded}</p>
      <p>{value.finding}</p>
      {value.expected && (
        <p>
          <strong>{t("errorAtlas.expected")}</strong> · {value.expected}
        </p>
      )}
      <Link className="self-start underline" to={path + encodeURIComponent(resource_id)}>
        {t("errorAtlas.correction")}
      </Link>
    </div>
  );
}
