import type {
  EducationView,
  ExperienceView,
  LanguageView,
  LineView,
  LinkView,
  MasterProfileView,
  ProjectView,
  SkillFactView,
} from "../viewTypes";

/** Remplace des champs d'une ligne de liste, sans toucher aux autres. */
export function replaceAt<T>(items: T[], index: number, patch: Partial<T>): T[] {
  return items.map((item, position) => (position === index ? { ...item, ...patch } : item));
}

export function removeAt<T>(items: T[], index: number): T[] {
  return items.filter((_, position) => position !== index);
}

/** Une ligne ajoutée à la main : sans identifiant (le code l'attribue à l'enregistrement), source « Toi ». */
export const blank = {
  line: (): LineView => ({ id: "", text: "" }),
  experience: (): ExperienceView => ({
    id: "",
    role: "",
    company: "",
    location: null,
    start: null,
    end: null,
    achievements: [],
    sources: ["january"],
  }),
  education: (): EducationView => ({
    id: "",
    degree: "",
    school: "",
    start: null,
    end: null,
    details: [],
    sources: ["january"],
  }),
  skill: (): SkillFactView => ({ id: "", name: "", category: null, sources: ["january"] }),
  project: (): ProjectView => ({
    id: "",
    name: "",
    description: "",
    link: null,
    achievements: [],
    sources: ["january"],
  }),
  language: (): LanguageView => ({ id: "", name: "", level: null, sources: ["january"] }),
  link: (): LinkView => ({ id: "", label: "", url: "", sources: ["january"] }),
};

const orNull = (value: string | null): string | null => (value?.trim() ? value : null);
const keepFilled = (lines: LineView[]): LineView[] =>
  lines.filter((line) => line.text.trim() !== "");
const orNullLine = (line: LineView | null): LineView | null =>
  line && line.text.trim() !== "" ? line : null;

/**
 * Le profil tel qu'il part à l'enregistrement : une valeur facultative laissée blanche devient
 * `null`, une ligne de texte vide disparaît. Le reste est envoyé tel quel : l'API refuse (422) ce
 * qui est invalide et le formulaire place le message sous le champ.
 */
export function cleanProfile(profile: MasterProfileView): MasterProfileView {
  const { identity } = profile;
  return {
    identity: {
      ...identity,
      email: orNull(identity.email),
      phone: orNull(identity.phone),
      location: orNull(identity.location),
      headline: orNull(identity.headline),
    },
    title: orNullLine(profile.title),
    summary: orNullLine(profile.summary),
    experiences: profile.experiences.map((item) => ({
      ...item,
      location: orNull(item.location),
      start: orNull(item.start),
      end: orNull(item.end),
      achievements: keepFilled(item.achievements),
    })),
    education: profile.education.map((item) => ({
      ...item,
      start: orNull(item.start),
      end: orNull(item.end),
      details: keepFilled(item.details),
    })),
    skills: profile.skills.map((item) => ({ ...item, category: orNull(item.category) })),
    projects: profile.projects.map((item) => ({
      ...item,
      link: orNull(item.link),
      achievements: keepFilled(item.achievements),
    })),
    languages: profile.languages.map((item) => ({ ...item, level: orNull(item.level) })),
    links: profile.links,
  };
}
