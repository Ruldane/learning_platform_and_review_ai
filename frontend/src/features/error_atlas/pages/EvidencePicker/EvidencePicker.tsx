import { t } from "@/shared/i18n/t";
import type { Evidence } from "../../api";
import { sourceLabels } from "../../labels";

type Props = { evidence: Evidence[]; selected: string; onChange: (key: string) => void };

export function EvidencePicker({ evidence, selected, onChange }: Props) {
  return (
    <label className="flex flex-col gap-1">
      {t("errorAtlas.selectEvidence")}
      <select
        className="rounded border border-border bg-background p-2"
        value={selected}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{t("errorAtlas.selectEvidencePlaceholder")}</option>
        {evidence.map(({ reference, title, finding }) => {
          const key = JSON.stringify(reference);
          const source = t("errorAtlas.evidenceLabel", {
            kind: t(sourceLabels[reference.kind]),
            title,
          });
          return (
            <option key={key} value={key}>
              {source} · {finding.slice(0, 90)}
            </option>
          );
        })}
      </select>
    </label>
  );
}
