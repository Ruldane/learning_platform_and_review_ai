import type {
  EducationView,
  ExperienceView,
  FactSourceView,
  IdentityView,
  LanguageView,
  LineView,
  LinkView,
  MasterProfileView,
  ProjectView,
  SkillFactView,
} from "./components/viewTypes";
import type { MasterProfileData } from "./types";

type ApiLine = { id: string; text: string };
type ApiSourced = ApiLine & { sources?: FactSourceView[] };
type ListKey = "experiences" | "education" | "skills" | "projects" | "languages" | "links";
type Data<K extends ListKey> = NonNullable<MasterProfileData[K]>[number];

const lines = (items: ApiLine[] | undefined): LineView[] =>
  (items ?? []).map(({ id, text }) => ({ id, text }));
const apiLines = (items: LineView[]): ApiLine[] => items.map(({ id, text }) => ({ id, text }));
const sourcedLine = (line: ApiSourced | null | undefined): LineView | null =>
  line ? { id: line.id, text: line.text, sources: line.sources ?? [] } : null;
const apiSourced = (line: LineView | null): ApiSourced | null =>
  line ? { id: line.id, text: line.text, sources: line.sources ?? [] } : null;

const identityView = ({ identity }: MasterProfileData): IdentityView => ({
  name: identity.name,
  email: identity.email ?? null,
  phone: identity.phone ?? null,
  location: identity.location ?? null,
  headline: identity.headline ?? null,
});

const experienceView = (item: Data<"experiences">): ExperienceView => ({
  id: item.id,
  role: item.role,
  company: item.company,
  location: item.location ?? null,
  start: item.start ?? null,
  end: item.end ?? null,
  achievements: lines(item.achievements),
  sources: item.sources ?? [],
});

const educationView = (item: Data<"education">): EducationView => ({
  id: item.id,
  degree: item.degree,
  school: item.school,
  start: item.start ?? null,
  end: item.end ?? null,
  details: lines(item.details),
  sources: item.sources ?? [],
});

const skillView = (item: Data<"skills">): SkillFactView => ({
  id: item.id,
  name: item.name,
  category: item.category ?? null,
  sources: item.sources ?? [],
});

const projectView = (item: Data<"projects">): ProjectView => ({
  id: item.id,
  name: item.name,
  description: item.description,
  link: item.link ?? null,
  achievements: lines(item.achievements),
  sources: item.sources ?? [],
});

const languageView = (item: Data<"languages">): LanguageView => ({
  id: item.id,
  name: item.name,
  level: item.level ?? null,
  sources: item.sources ?? [],
});

const linkView = (item: Data<"links">): LinkView => ({
  id: item.id,
  label: item.label,
  url: item.url,
  sources: item.sources ?? [],
});

/** Le profil du contrat → la vue du formulaire (listes et valeurs facultatives toujours présentes). */
export function toProfileView(data: MasterProfileData): MasterProfileView {
  return {
    identity: identityView(data),
    title: sourcedLine(data.title),
    summary: sourcedLine(data.summary),
    experiences: (data.experiences ?? []).map(experienceView),
    education: (data.education ?? []).map(educationView),
    skills: (data.skills ?? []).map(skillView),
    projects: (data.projects ?? []).map(projectView),
    languages: (data.languages ?? []).map(languageView),
    links: (data.links ?? []).map(linkView),
  };
}

/** La vue du formulaire → le profil envoyé à `PUT /profile` (ids gardés, `""` pour une ligne neuve). */
export function fromProfileView(view: MasterProfileView): MasterProfileData {
  return {
    identity: view.identity,
    title: apiSourced(view.title),
    summary: apiSourced(view.summary),
    experiences: view.experiences.map((item) => ({
      ...item,
      achievements: apiLines(item.achievements),
    })),
    education: view.education.map((item) => ({ ...item, details: apiLines(item.details) })),
    skills: view.skills,
    projects: view.projects.map((item) => ({
      ...item,
      achievements: apiLines(item.achievements),
    })),
    languages: view.languages,
    links: view.links,
  };
}

const MAX_LABEL = 100;
const clip = (text: string): string =>
  text.length > MAX_LABEL ? `${text.slice(0, MAX_LABEL - 1)}…` : text;

/** Ce que January lit pour reconnaître un fait du profil : identifiant du fait → texte court. */
export function factLabels(data: MasterProfileData): Map<string, string> {
  const labels = new Map<string, string>();
  const put = (id: string, text: string) => {
    if (id !== "" && text.trim() !== "") labels.set(id, clip(text));
  };
  const putLines = (items: ApiLine[] | undefined) => items?.forEach((l) => put(l.id, l.text));
  if (data.title) put(data.title.id, data.title.text);
  if (data.summary) put(data.summary.id, data.summary.text);
  for (const item of data.experiences ?? []) {
    put(item.id, `${item.role} · ${item.company}`);
    putLines(item.achievements);
  }
  for (const item of data.education ?? []) {
    put(item.id, `${item.degree} · ${item.school}`);
    putLines(item.details);
  }
  for (const item of data.skills ?? []) put(item.id, item.name);
  for (const item of data.projects ?? []) {
    put(item.id, item.name);
    putLines(item.achievements);
  }
  for (const item of data.languages ?? []) put(item.id, item.name);
  for (const item of data.links ?? []) put(item.id, item.label);
  return labels;
}
