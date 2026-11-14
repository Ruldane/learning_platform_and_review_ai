import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useActivateTemplate } from "../../hooks/useCreateTemplate";
import type { TemplateSummaryOut } from "../../types";
import { TemplateRow } from "./TemplateRow";

/** Les modèles de CV, le plus récent d'abord ; « Utiliser ce modèle » les active un à un. */
export function TemplateList({ templates }: { templates: TemplateSummaryOut[] }) {
  const { activate, pending, error } = useActivateTemplate();
  return (
    <div className="flex flex-col gap-2">
      <ul aria-label={t("cv.templatesPage.list")} className="flex flex-col gap-2">
        {templates.map((template) => (
          <TemplateRow key={template.id} template={template} busy={pending} onActivate={activate} />
        ))}
      </ul>
      {error ? <InlineError message={error} /> : null}
    </div>
  );
}
