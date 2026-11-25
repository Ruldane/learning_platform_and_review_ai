import { t } from "@/shared/i18n/t";
import type { EducationView } from "../viewTypes";
import { Field } from "./Field";
import { LineList } from "./LineList";

interface EducationFieldsProps {
  item: EducationView;
  index: number;
  patch: (changes: Partial<EducationView>) => void;
}

/** The fields of an education entry: degree, school, dates and details. */
export function EducationFields({ item, index, patch }: EducationFieldsProps) {
  const base = `education.${index}`;
  const row = t("cv.profile.education.row", { n: index + 1 });
  const required = (field: "degree" | "school") => (
    <Field
      path={`${base}.${field}`}
      label={t(`cv.profile.education.${field}`)}
      context={row}
      value={item[field]}
      required
      onChange={(value) => patch({ [field]: value })}
    />
  );
  const date = (field: "start" | "end") => (
    <Field
      path={`${base}.${field}`}
      label={t(`cv.profile.education.${field}`)}
      context={row}
      value={item[field] ?? ""}
      onChange={(value) => patch({ [field]: value || null })}
    />
  );
  return (
    <>
      {required("degree")}
      {required("school")}
      {date("start")}
      {date("end")}
      <LineList
        path={`${base}.details`}
        context={row}
        lines={item.details}
        onChange={(details) => patch({ details })}
        lineLabel={(n) => t("cv.profile.education.detail", { n })}
        addLabel={t("cv.profile.education.addDetail")}
        addAriaLabel={t("cv.profile.education.addDetailTo", { n: index + 1 })}
        removeAriaLabel={(n) => t("cv.profile.education.removeDetail", { n, row: index + 1 })}
      />
    </>
  );
}
