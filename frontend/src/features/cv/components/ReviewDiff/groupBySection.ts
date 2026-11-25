import type { CvSectionView, ModificationView } from "../viewTypes";

const ORDER: CvSectionView[] = [
  "summary",
  "experience",
  "education",
  "skills",
  "projects",
  "languages",
  "links",
];

export interface SectionGroup {
  section: CvSectionView;
  mods: ModificationView[];
}

/** Changes grouped by CV section, in CV order; empty sections are dropped. */
export function groupBySection(mods: ModificationView[]): SectionGroup[] {
  return ORDER.map((section) => ({
    section,
    mods: mods.filter((mod) => mod.section === section),
  })).filter((group) => group.mods.length > 0);
}
