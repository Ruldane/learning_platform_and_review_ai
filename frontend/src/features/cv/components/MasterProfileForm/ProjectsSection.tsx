import { t } from "@/shared/i18n/t";
import type { ProjectView } from "../viewTypes";
import { blank } from "./profileDraft";
import { ProjectFields } from "./ProjectFields";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface ProjectsSectionProps {
  items: ProjectView[];
  onChange: (items: ProjectView[]) => void;
}

/** Les projets : une ligne par projet. */
export function ProjectsSection({ items, onChange }: ProjectsSectionProps) {
  return (
    <Section title={t("cv.profile.section.projects")} count={items.length} path="projects">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.project}
        rowName={(n) => t("cv.profile.project.row", { n })}
        addLabel={t("cv.profile.project.add")}
        removeLabel={(n) => t("cv.profile.project.remove", { n })}
      >
        {(item, index, patch) => <ProjectFields item={item} index={index} patch={patch} />}
      </RowList>
    </Section>
  );
}
