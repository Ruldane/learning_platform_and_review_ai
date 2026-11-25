import { t } from "@/shared/i18n/t";
import type { ProjectView } from "../viewTypes";
import { Field } from "./Field";
import { LineList } from "./LineList";

interface ProjectFieldsProps {
  item: ProjectView;
  index: number;
  patch: (changes: Partial<ProjectView>) => void;
}

/** The fields of a project: name, description, link and achievements. */
export function ProjectFields({ item, index, patch }: ProjectFieldsProps) {
  const base = `projects.${index}`;
  const row = t("cv.profile.project.row", { n: index + 1 });
  return (
    <>
      <Field
        path={`${base}.name`}
        label={t("cv.profile.project.name")}
        context={row}
        value={item.name}
        required
        onChange={(name) => patch({ name })}
      />
      <Field
        path={`${base}.description`}
        label={t("cv.profile.project.description")}
        context={row}
        value={item.description}
        multiline
        onChange={(description) => patch({ description })}
      />
      <Field
        path={`${base}.link`}
        label={t("cv.profile.project.link")}
        context={row}
        value={item.link ?? ""}
        onChange={(link) => patch({ link: link || null })}
      />
      <LineList
        path={`${base}.achievements`}
        context={row}
        lines={item.achievements}
        onChange={(achievements) => patch({ achievements })}
        lineLabel={(n) => t("cv.profile.project.achievement", { n })}
        addLabel={t("cv.profile.project.addAchievement")}
        addAriaLabel={t("cv.profile.project.addAchievementTo", { n: index + 1 })}
        removeAriaLabel={(n) => t("cv.profile.project.removeAchievement", { n, row: index + 1 })}
      />
    </>
  );
}
