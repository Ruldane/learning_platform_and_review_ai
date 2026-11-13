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

/** Les modifications regroupées par section du CV, dans l'ordre d'un CV ; les sections vides disparaissent. */
export function groupBySection(mods: ModificationView[]): SectionGroup[] {
  return ORDER.map((section) => ({
    section,
    mods: mods.filter((mod) => mod.section === section),
  })).filter((group) => group.mods.length > 0);
}
