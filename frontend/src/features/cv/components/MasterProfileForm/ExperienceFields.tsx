import { t } from "@/shared/i18n/t";
import type { ExperienceView } from "../viewTypes";
import { Field } from "./Field";
import { LineList } from "./LineList";

interface ExperienceFieldsProps {
  item: ExperienceView;
  index: number;
  patch: (changes: Partial<ExperienceView>) => void;
}

/** Les champs d'une expérience : poste, entreprise, lieu, dates et réalisations. */
export function ExperienceFields({ item, index, patch }: ExperienceFieldsProps) {
  const base = `experiences.${index}`;
  const row = t("cv.profile.experience.row", { n: index + 1 });
  const required = (field: "role" | "company") => (
    <Field
      path={`${base}.${field}`}
      label={t(`cv.profile.experience.${field}`)}
      context={row}
      value={item[field]}
      required
      onChange={(value) => patch({ [field]: value })}
    />
  );
  const optional = (field: "location" | "start" | "end") => (
    <Field
      path={`${base}.${field}`}
      label={t(`cv.profile.experience.${field}`)}
      context={row}
      value={item[field] ?? ""}
      onChange={(value) => patch({ [field]: value || null })}
    />
  );
  return (
    <>
      {required("role")}
      {required("company")}
      {optional("location")}
      {optional("start")}
      {optional("end")}
      <LineList
        path={`${base}.achievements`}
        context={row}
        lines={item.achievements}
        onChange={(achievements) => patch({ achievements })}
        lineLabel={(n) => t("cv.profile.experience.achievement", { n })}
        addLabel={t("cv.profile.experience.addAchievement")}
        addAriaLabel={t("cv.profile.experience.addAchievementTo", { n: index + 1 })}
        removeAriaLabel={(n) => t("cv.profile.experience.removeAchievement", { n, row: index + 1 })}
      />
    </>
  );
}
